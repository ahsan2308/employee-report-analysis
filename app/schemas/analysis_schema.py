from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class EmployeeAnalysisResponse(BaseModel):
    """Schema for employee analysis response - simplified version"""
    analysis_id: int
    report_id: UUID
    employee_id: int
    analysis_date: datetime
    sentiment_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_explanation: Optional[str] = None
    full_analysis_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
