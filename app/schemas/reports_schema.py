from pydantic import BaseModel
from datetime import date
from pydantic import Field, validator
from typing import Optional

class ReportCreate(BaseModel):
    employee_id: int
    report_date: date
    report_text: str


class ReportForm(BaseModel):
    employee_id: int
    key_tasks_completed: Optional[str] = None
    impact_outcome: Optional[str] = None
    challenges_faced: Optional[str] = None
    support_required: Optional[str] = None
    tasks_planned_next_week: Optional[str] = None
    confidence_level: Optional[int] = Field(None, ge=1, le=5)  # Must be between 1 and 5
    nothing_to_report_reason: Optional[str] = None

    @validator("nothing_to_report_reason", always=True)
    def validate_report_fields(cls, value, values):
        # Ensure at least one of the fields is filled
        if not any([
            values.get("key_tasks_completed"),
            values.get("nothing_to_report_reason")
        ]):
            raise ValueError("Either 'key_tasks_completed' or 'nothing_to_report_reason' must be provided.")
        return value