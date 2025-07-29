"""
One-off Migration Script: Vision Data (Standalone)

This script migrates vision data from the source table (with raw text fields)
to the target table (employee_vision_data) with proper JSON transformation.

Key changes:
- No dependency on VisionDataCSVRow (schema). All parsing/validation is local.
- Robust parsing for:
  * sub_entities: "Name:Count, Name2:Count2" -> {"Name": int, ...}
  * sub_entities_content: "Key:[{...}], Key2:[]" with commas inside strings/objects
- Defensive date parsing for from_date/to_date.

Usage:
    python migrate_vision_data.py

Place this script in the 'one_of_mg' folder for one-off migrations.
"""

import os
import sys
import json
import re
from datetime import datetime, date

# Add app to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.vision_data_models import EmployeeVisionData
from app.core.logger import logger
from app.database import get_database

SOURCE_TABLE_NAME = "employee_vision_data_raw"
SCHEMA_NAME = "employee_reports"
BATCH_SIZE = 100

# ---------------------------
# Helpers: robust parsing
# ---------------------------

def _top_level_split(s: str, delimiter: str = ','):
    """
    Split on delimiter only when not inside [], {}, or quotes. Handles escapes.
    """
    if s is None:
        return []
    parts, buf = [], []
    depth_square = depth_curly = 0
    in_str = False
    esc = False
    quote_char = ''
    for ch in str(s):
        if esc:
            buf.append(ch); esc = False; continue
        if ch == '\\':
            buf.append(ch); esc = True; continue
        if in_str:
            buf.append(ch)
            if ch == quote_char:
                in_str = False
            continue
        if ch in ('"', "'"):
            in_str = True
            quote_char = ch
            buf.append(ch)
            continue
        if ch == '[': depth_square += 1
        elif ch == ']': depth_square = max(0, depth_square - 1)
        elif ch == '{': depth_curly += 1
        elif ch == '}': depth_curly = max(0, depth_curly - 1)
        if ch == delimiter and depth_square == 0 and depth_curly == 0:
            parts.append(''.join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf).strip())
    return parts

def _json_list_with_fixes(value: str):
    """
    Try to json.loads a list; if it fails, apply light fixes:
    - replace unescaped single quotes with double quotes
    - remove trailing commas before ] or }
    - strip control chars
    Returns: list | None
    """
    if value is None:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        pass

    repaired = str(value).strip()
    repaired = re.sub(r'(?<!\\)\'', '"', repaired)
    repaired = re.sub(r',\s*([\]\}])', r'\1', repaired)
    repaired = ''.join(ch for ch in repaired if ch >= ' ')

    try:
        parsed = json.loads(repaired)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None

def parse_sub_entities(raw: str) -> dict:
    """
    Parse strings like:
      'Cases:0, Case Attachments:0, Activities:0'
    into:
      {'Cases': 0, 'Case Attachments': 0, 'Activities': 0}
    """
    if not raw or not str(raw).strip():
        return {}
    text = str(raw)
    # Accept tokens like "Name:Count" (Count = digits)
    pairs = _top_level_split(text, delimiter=',')
    out = {}
    for tok in pairs:
        if not tok or ':' not in tok:
            continue
        k, v = tok.split(':', 1)
        k = k.strip()
        v = v.strip()
        # Try to coerce to int; if not, log and skip/fallback to 0
        try:
            out[k] = int(v.replace(',', ''))
        except Exception:
            # fallback: try float→int if clean; else 0
            try:
                out[k] = int(float(v))
            except Exception:
                out[k] = 0
    return out

def parse_sub_entities_content(raw: str) -> dict:
    """
    Parse strings like:
      'DFA:[{...},{...}], Correspondence:[]'
    into:
      {'DFA': [ {...}, {...} ], 'Correspondence': []}
    """
    if not raw or not str(raw).strip():
        return {}
    out = {}
    for part in _top_level_split(str(raw), delimiter=','):
        if not part or ':' not in part:
            continue
        key, value = part.split(':', 1)
        key = key.strip()
        value = value.strip()
        if not (value.startswith('[') and value.endswith(']')):
            # not a list → store empty list (and keep going)
            out[key] = []
            continue
        items = _json_list_with_fixes(value)
        if isinstance(items, list):
            # Keep only dict items; non-dict items are discarded
            out[key] = [it for it in items if isinstance(it, dict)]
        else:
            out[key] = []
    return out

def parse_date_safe(v):
    """
    Accept date, datetime, or string in formats:
      YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, MM-DD-YYYY, DD-MM-YYYY
    Return a date or None (and the caller decides to skip or log).
    """
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    fmts = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    # Last resort: try to detect YYYY-MM-DD pattern even if weird spaces
    m = re.match(r'^\s*(\d{4})-(\d{2})-(\d{2})\s*$', s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            pass
    return None

def migrate():
    db_instance = get_database()
    error_count = 0
    success_count = 0
    total_count = 0
    errors = []

    logger.info("Starting migration from %s.%s to employee_vision_data", SCHEMA_NAME, SOURCE_TABLE_NAME)

    # Get a session using the same pattern as your main codebase
    with db_instance.create_session() as session:
        # Reflect source table dynamically
        from sqlalchemy import Table, select, MetaData
        metadata = MetaData()
        source_table = Table(SOURCE_TABLE_NAME, metadata, autoload_with=session.bind, schema=SCHEMA_NAME)

        # Query all rows
        rows = session.execute(select(source_table)).fetchall()
        logger.info("Found %d rows to migrate", len(rows))

        columns = source_table.columns.keys()

        for idx, row in enumerate(rows):
            total_count += 1
            try:
                row_dict = dict(zip(columns, row))

                # --- Extract & normalize primitives ---
                try:
                    employee_id = int(row_dict.get('employee_id'))
                except Exception:
                    raise ValueError(f"Invalid employee_id: {row_dict.get('employee_id')}")

                from_date_raw = row_dict.get('from_date')
                to_date_raw = row_dict.get('to_date')
                from_date = parse_date_safe(from_date_raw)
                to_date = parse_date_safe(to_date_raw)
                if not from_date or not to_date:
                    raise ValueError(f"Invalid from/to dates: from={from_date_raw}, to={to_date_raw}")
                if from_date > to_date:
                    raise ValueError(f"From date ({from_date}) cannot be after To date ({to_date})")

                main_entity = row_dict.get('main_entity')
                if not main_entity or not str(main_entity).strip():
                    raise ValueError("Main entity cannot be empty")

                # --- Parse JSONish fields standalone ---
                sub_entities_raw = row_dict.get('sub_entities') or ""
                sub_entities = parse_sub_entities(sub_entities_raw)

                sub_entities_content_raw = row_dict.get('sub_entities_content') or ""
                sub_entities_content = parse_sub_entities_content(sub_entities_content_raw)

                # --- Upsert logic ---
                try:
                    existing = session.query(EmployeeVisionData).filter_by(
                        employee_id=employee_id,
                        from_date=from_date,
                        to_date=to_date,
                        main_entity=main_entity
                    ).first()

                    if existing:
                        existing.sub_entities = sub_entities
                        existing.sub_entities_content = sub_entities_content
                        session.flush()
                        success_count += 1
                    else:
                        new_record = EmployeeVisionData(
                            employee_id=employee_id,
                            from_date=from_date,
                            to_date=to_date,
                            main_entity=main_entity,
                            sub_entities=sub_entities,
                            sub_entities_content=sub_entities_content
                        )
                        session.add(new_record)
                        session.flush()
                        success_count += 1

                except Exception as db_exc:
                    session.rollback()
                    error_count += 1
                    errors.append({"row": row_dict, "error": str(db_exc)})
                    logger.error("Error processing row %d (DB error): %s", idx + 1, str(db_exc))
                    continue

                # Commit after every row to avoid batch rollback issues and DB locks
                session.commit()
                if (idx + 1) % BATCH_SIZE == 0:
                    logger.info("Processed %d/%d rows...", idx + 1, len(rows))

            except Exception as e:
                error_count += 1
                errors.append({"row": row_dict, "error": str(e)})
                logger.error("Error processing row %d: %s", idx + 1, str(e))

        # Final commit
        session.commit()
        logger.info("Migration complete: %d succeeded, %d failed, %d total", success_count, error_count, total_count)

        # Optionally, write errors to stdout (excluding common FK employee_id errors if noisy)
        if errors:
            def serialize(obj):
                if isinstance(obj, dict):
                    return {k: serialize(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize(v) for v in obj]
                elif hasattr(obj, "isoformat"):
                    return obj.isoformat()
                else:
                    return obj

            serializable_errors = []
            for err in errors:
                err_copy = err.copy()
                err_copy["row"] = serialize(err_copy["row"])
                serializable_errors.append(err_copy)

            print("\n--- Migration Errors ---")
            for err in serializable_errors:
                error_msg = err.get("error", "")
                if "violates foreign key constraint" not in error_msg and "employee_id" not in error_msg:
                    print(json.dumps(err, indent=2, ensure_ascii=False))
            print("--- End of Migration Errors ---\n")

            logger.info("Displayed %d errors in console (excluding FK employee_id errors)", len(errors))

if __name__ == "__main__":
    migrate()
