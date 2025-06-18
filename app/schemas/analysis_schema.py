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

class CredibilityAssessment(BaseModel):
    """Schema for credibility assessment in analysis."""
    rating: str = Field(description="Overall credibility rating (high/medium/low)")
    explanation: str = Field(description="Assessment of the report's credibility, focusing on potential exaggeration")
    exaggeration_flags: List[str] = Field(description="Specific claims that appear to be exaggerated")
    consistency_score: str = Field(description="How well the various sections of the report align with each other")

class PerformanceAssessment(BaseModel):
    """Schema for performance assessment in analysis."""
    rating: str = Field(description="Overall performance rating (high/medium/low)")
    summary: str = Field(description="Brief overall performance assessment summarizing key findings")
    key_strengths: List[str] = Field(description="Notable strengths identified from the report")
    improvement_areas: List[str] = Field(description="Specific areas where performance could be enhanced")

class AnalysisResponse(BaseModel):
    """Schema for analysis response. This is the model that is returned by the API."""
    report_id: str
    employee_name: str 
    sentiment: float  
    sentiment_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_explanation: Optional[str] = None
    full_analysis_json: Optional[Dict[str, Any]] = None
    achievements_json: Optional[List[Any]] = None
    challenges_json: Optional[List[Any]] = None
    topics: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    credibility_assessment: Optional[CredibilityAssessment] = None
    performance_assessment: Optional[PerformanceAssessment] = None

    class Config:
        from_attributes = True
