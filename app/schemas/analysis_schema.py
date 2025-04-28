from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class Achievement(BaseModel):
    """Schema for achievement in analysis."""
    description: str = Field(description="Detailed description of the achievement")
    impact: str = Field(description="The measurable impact or result of this achievement between 1 and 10")

class Challenge(BaseModel):
    """Schema for challenge in analysis."""
    description: str = Field(description="Detailed description of the challenge faced")
    severity: str = Field(description="How severe the challenge is (low, medium, high)")

class AnalysisResponse(BaseModel):
    """Schema for analysis response. This is the model that is returned by the API."""
    report_id: str
    employee_name: str  # Required field
    sentiment: float  # Required field (now consistent with sentiment_score)
    sentiment_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_explanation: Optional[str] = None
    full_analysis_json: Optional[Dict[str, Any]] = None
    achievements_json: Optional[List[Any]] = None
    challenges_json: Optional[List[Any]] = None
    topics: Optional[List[str]] = None
    action_items: Optional[List[str]] = None

    class Config:
        from_attributes = True  
