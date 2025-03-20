from pydantic import BaseModel
from datetime import date

class ReportCreate(BaseModel):
    employee_id: int
    report_date: date
    report_text: str
    qdrant_id: str  
