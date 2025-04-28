"""
Pydantic models for structured data responses.

This module contains all the Pydantic models used for structured data
generation with LLM services. Import these models when you need to
define a structured output format for LLM responses.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# # Simplified EmployeeAnalysis model
# class EmployeeAnalysis(BaseModel):
#     """Simplified model for employee report analysis."""
#     sentiment: Literal["positive", "negative", "neutral"] = Field(
#         description="Overall sentiment of the report"
#     )
#     risk_level: Literal["low", "medium", "high"] = Field(
#         description="Overall risk assessment level"
#     )
#     risk_explanation: str = Field(
#         description="Explanation for the assigned risk level"
#     )
#     # Additional fields that will be stored in full_analysis_json
#     topics: List[str] = Field(
#         description="Key topics covered in the report"
#     )


# More detailed models commented out for future use
class Achievement(BaseModel):
    # Model representing an employee achievement
    description: str = Field(
        description="Detailed description of the achievement"
    )
    impact: str = Field(
        description="The measurable impact or result of this achievement between 1 and 10"
    )

    class Config:
        from_attributes = True  # Updated from orm_mode=True for Pydantic v2


class Challenge(BaseModel):
    # Model representing a challenge faced by an employee
    description: str = Field(
        description="Detailed description of the challenge faced"
    )
    severity: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="How severe the challenge is (low, medium, high)"
    )

    class Config:
        from_attributes = True  # Updated from orm_mode=True for Pydantic v2


class EmployeeAnalysis(BaseModel):
    # Full model for comprehensive employee report analysis
    achievements: List[Achievement] = Field(
        description="Key achievements mentioned in the report"
    )
    challenges: List[Challenge] = Field(
        description="Challenges mentioned in the report"
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the individual writing the report"
    )
    topics: List[str] = Field(
        description="Key topics covered in the report"
    )
    action_items: List[str] = Field(
        description="Recommended action items based on the report"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Overall risk assessment level"
    )
    risk_explanation: str = Field(
        description="Explanation for the assigned risk level"
    )

    class Config:
        from_attributes = True  # Updated from orm_mode=True for Pydantic v2



