"""Report chunk to vector store point mappings (the qdrant_mappings table), in the caller's session."""
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import schema_name


def insert_mapping(session: Session, qdrant_id: str, report_id: str, chunk_index: int) -> None:
    session.execute(
        text(f"""
        INSERT INTO {schema_name}.qdrant_mappings (qdrant_id, report_id, chunk_index)
        VALUES (:qdrant_id, :report_id, :chunk_index)
        """),
        {"qdrant_id": qdrant_id, "report_id": report_id, "chunk_index": chunk_index}
    )


def insert_mappings(session: Session, rows: List[Dict]) -> None:
    """Insert mappings ({qdrant_id, report_id, chunk_index}); a point already mapped is left as it is."""
    session.execute(
        text(f"INSERT INTO {schema_name}.qdrant_mappings (qdrant_id, report_id, chunk_index) VALUES (:qdrant_id, :report_id, :chunk_index) ON CONFLICT (qdrant_id) DO NOTHING"),
        rows
    )


def point_ids_for_reports(session: Session, report_ids: Iterable) -> List[str]:
    """The vector store point IDs mapped to any of these reports."""
    rows = session.execute(
        text(f"SELECT qdrant_id FROM {schema_name}.qdrant_mappings WHERE CAST(report_id AS text) = ANY(:report_ids)"),
        {"report_ids": [str(report_id) for report_id in report_ids]},
    ).fetchall()
    return [str(row[0]) for row in rows]


def delete_mappings(session: Session, point_ids: List[str]) -> None:
    session.execute(
        text(f"DELETE FROM {schema_name}.qdrant_mappings WHERE CAST(qdrant_id AS text) = ANY(:ids)"),
        {"ids": point_ids},
    )


def report_chunk_points(session: Session, report_id: str) -> List[Tuple]:
    """(point id, chunk index) of a report's chunks, in chunk order."""
    return session.execute(
        text(f"""
        SELECT qdrant_id, chunk_index
        FROM {schema_name}.qdrant_mappings
        WHERE report_id = :report_id
        ORDER BY chunk_index
        """),
        {"report_id": report_id}
    ).fetchall()
