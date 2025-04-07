from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class EmployeeAnalysisCreate(BaseModel):
    """Schema for creating an employee analysis - simplified version"""
    report_id: str
    employee_id: int
    sentiment_score: Optional[float] = None
    risk_level: Optional[str] = None
    full_analysis: Dict[str, Any]

class EmployeeAnalysisResponse(BaseModel):
    """Schema for employee analysis response - simplified version"""
    analysis_id: int
    report_id: str
    employee_id: int
    analysis_date: datetime
    sentiment_score: Optional[float] = None
    risk_level: Optional[str] = None
    full_analysis: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
