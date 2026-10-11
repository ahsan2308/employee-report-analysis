from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from datetime import date
from typing import Optional

class ReportCreate(BaseModel):
    employee_id: int
    report_date: date
    report_text: str
    
    model_config = ConfigDict(from_attributes=True)

class ReportForm(BaseModel):
    employee_id: int
    key_tasks_completed: Optional[str] = None
    impact_outcome: Optional[str] = None
    challenges_faced: Optional[str] = None
    support_required: Optional[str] = None
    tasks_planned_next_week: Optional[str] = None
    confidence_level: Optional[int] = Field(None, ge=1, le=5)  # Must be between 1 and 5
    # validate_default so the check below also runs when the reason is omitted
    nothing_to_report_reason: Optional[str] = Field(None, validate_default=True)

    @field_validator("nothing_to_report_reason")
    @classmethod
    def validate_report_fields(cls, value, info: ValidationInfo):
        # Ensure at least one of the fields is filled. The reason itself is
        # `value`: it is not in info.data while it is being validated.
        if not any([
            info.data.get("key_tasks_completed"),
            value
        ]):
            raise ValueError("Either 'key_tasks_completed' or 'nothing_to_report_reason' must be provided.")
        return value
    
    model_config = ConfigDict(from_attributes=True)
