"""Vision system activity data queries."""
from typing import Dict, Any, List, Set, Tuple
from datetime import date, timedelta
from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from app.db.database import get_database
from app.models.vision_data_models import EmployeeVisionData
from app.core.logger import logger
from app.domain.periods import get_month_date_range, get_quarter_date_range, month_name, months_in_quarter


def get_employee_vision_data(employee_id: int, report_date: date, num_previous_weeks: int = 4) -> Dict[str, Any]:
    """
    Fetch vision data for an employee for the given report date and previous periods.
    
    Args:
        employee_id: The ID of the employee
        report_date: The date of the report (to match with to_date in vision data)
        num_previous_weeks: Number of previous weeks worth of data to include
        
    Returns:
        Dictionary containing current data (matching report date) and previous data
    """
    db_instance = get_database()
    
    # Calculate cutoff date for previous data (4 weeks before report date by default)
    previous_data_cutoff = report_date - timedelta(weeks=num_previous_weeks)
    
    result = {
        "date_context": {
            "report_date": report_date.isoformat(),
        },
        "current_data": [],  # Data where to_date matches report_date
        "previous_data": []  # Data where to_date is before report_date but after cutoff
    }
    
    try:
        with db_instance.create_session() as session:
            # Get current data - records where to_date exactly matches the report_date
            current_data = session.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.to_date == report_date
            ).all()
            
            # Format current data
            for record in current_data:
                result["current_data"].append({
                    "main_entity": record.main_entity,
                    "sub_entities": record.sub_entities,
                    "sub_entities_content": record.sub_entities_content,
                    "from_date": record.from_date.isoformat() if record.from_date else None,
                    "to_date": record.to_date.isoformat() if record.to_date else None
                })
            
            # Get previous data - records with to_date before report_date but after cutoff
            previous_data = session.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.to_date < report_date,
                EmployeeVisionData.to_date >= previous_data_cutoff
            ).order_by(EmployeeVisionData.to_date.desc()).all()
            
            # Format previous data
            for record in previous_data:
                result["previous_data"].append({
                    "main_entity": record.main_entity,
                    "sub_entities": record.sub_entities,
                    "sub_entities_content": record.sub_entities_content,
                    "from_date": record.from_date.isoformat() if record.from_date else None,
                    "to_date": record.to_date.isoformat() if record.to_date else None
                })
                
            logger.info(f"Retrieved vision data for employee {employee_id}: {len(result['current_data'])} current records, {len(result['previous_data'])} previous records")
            return result
            
    except Exception as e:
        logger.error(f"Error fetching vision data for employee {employee_id}: {e}")
        return result


def get_employee_vision_data_for_month(employee_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Fetch vision data for an employee for all weeks in a given month.
    
    Args:
        employee_id: The ID of the employee
        year: Year (e.g., 2025)
        month: Month as integer (1-12)
        
    Returns:
        Dictionary containing a list of week-wise data for the month
    """

    db_instance = get_database()
    start_date, end_date = get_month_date_range(year, month)
    result = {
        "date_context": {
            "month": month,
            "year": year,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        },
        "weeks_data": []
    }

    try:
        with db_instance.create_session() as session:
            # Query all vision data for the month
            records = session.query(EmployeeVisionData).filter(
                EmployeeVisionData.employee_id == employee_id,
                EmployeeVisionData.to_date >= start_date,
                EmployeeVisionData.to_date <= end_date
            ).order_by(EmployeeVisionData.to_date.asc()).all()

            # Group records by week (ISO week number)
            week_map = {}
            for record in records:
                week_num = record.to_date.isocalendar()[1]
                if week_num not in week_map:
                    week_map[week_num] = []
                week_map[week_num].append({
                    "main_entity": record.main_entity,
                    "sub_entities": record.sub_entities,
                    "sub_entities_content": record.sub_entities_content,
                    "from_date": record.from_date.isoformat() if record.from_date else None,
                    "to_date": record.to_date.isoformat() if record.to_date else None
                })

            # Build week-wise data list
            for idx, (week_num, items) in enumerate(sorted(week_map.items())):
                result["weeks_data"].append({
                    "week_number": idx + 1,
                    "iso_week": week_num,
                    "activities": items
                })

            logger.info(f"Retrieved vision data for employee {employee_id} for {year}-{month}: {len(result['weeks_data'])} weeks")
            return result

    except Exception as e:
        logger.error(f"Error fetching monthly vision data for employee {employee_id}: {e}")
        return result


def get_employee_vision_data_for_quarter(employee_id: int, year: int, quarter: int) -> Dict[str, Any]:
    """
    Fetch vision data for an employee for all months in a given quarter.
    
    Args:
        employee_id: The ID of the employee
        year: Year (e.g., 2025)
        quarter: Quarter as integer (1-4)
        
    Returns:
        Dictionary containing quarter-wise vision data
    """
    start_date, end_date = get_quarter_date_range(year, quarter)
    
    result = {
        "date_context": {
            "quarter": quarter,
            "year": year,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
        },
        "months_data": []
    }

    try:
        # Get the three months in this quarter
        # Get vision data for each month in the quarter
        for month in months_in_quarter(quarter):
            month_vision_data = get_employee_vision_data_for_month(employee_id, year, month)
            
            if month_vision_data and month_vision_data.get("weeks_data"):
                # Add month name to the month data
                month_vision_data["month_name"] = month_name(month)
                result["months_data"].append(month_vision_data)

        logger.info(f"Retrieved vision data for employee {employee_id} for {year}-Q{quarter}: {len(result['months_data'])} months")
        return result

    except Exception as e:
        logger.error(f"Error fetching quarterly vision data for employee {employee_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return result


def upsert_vision_record(session: Session, employee_id: int, from_date, to_date, main_entity: str,
                         sub_entities, sub_entities_content) -> bool:
    """Set the sub-entities of an employee's main entity for a period, creating the record if needed.

    Returns True when created (not flushed).
    """
    existing = session.query(EmployeeVisionData).filter(
        EmployeeVisionData.employee_id == employee_id,
        EmployeeVisionData.from_date == from_date,
        EmployeeVisionData.to_date == to_date,
        EmployeeVisionData.main_entity == main_entity
    ).first()
    if existing:
        existing.sub_entities = sub_entities
        existing.sub_entities_content = sub_entities_content
        return False
    session.add(EmployeeVisionData(
        employee_id=employee_id,
        from_date=from_date,
        to_date=to_date,
        main_entity=main_entity,
        sub_entities=sub_entities,
        sub_entities_content=sub_entities_content
    ))
    return True


def existing_vision_keys(session: Session, keys: List[Tuple]) -> Set[Tuple]:
    """The (employee_id, from_date, to_date, main_entity) keys among keys that already have a record."""
    columns = (
        EmployeeVisionData.employee_id,
        EmployeeVisionData.from_date,
        EmployeeVisionData.to_date,
        EmployeeVisionData.main_entity
    )
    rows = session.query(*columns).filter(tuple_(*columns).in_(keys)).all()
    return {tuple(row) for row in rows}


def bulk_upsert_vision_records(session: Session, vision_data: List[Dict[str, Any]]) -> None:
    """Insert vision records, replacing the sub-entities of those that exist; flushed."""
    stmt = pg_insert(EmployeeVisionData.__table__).values(vision_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['employee_id', 'from_date', 'to_date', 'main_entity'],
        set_={
            'sub_entities': stmt.excluded.sub_entities,
            'sub_entities_content': stmt.excluded.sub_entities_content
        }
    )
    session.execute(stmt)
    session.flush()
