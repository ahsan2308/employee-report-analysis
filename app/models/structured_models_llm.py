"""
Pydantic models for structured data responses.

This module contains all the Pydantic models used for structured data
generation with LLM services. Import these models when you need to
define a structured output format for LLM responses.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# More detailed models commented out for future use
class Achievement(BaseModel):
    # Model representing an employee achievement
    description: str = Field(
        description="Detailed description of the achievement in complete sentences without referencing the impact rating"
    )
    impact: str = Field(
        description="Format must be: 'N (reason)' where N is an integer rating 1-10, followed by a concise reason for the rating in parentheses"
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


class CredibilityAssessment(BaseModel):
    # Model representing a credibility assessment for an employee report
    rating: Literal["high", "medium", "low"] = Field(
        description="Overall credibility rating of the report"
    )
    explanation: str = Field(
        description="Assessment of the report's credibility, focusing on potential exaggeration"
    )
    exaggeration_flags: List[str] = Field(
        description="Specific claims that appear to be exaggerated"
    )
    consistency_score: Literal["high", "medium", "low"] = Field(
        description="How well the various sections of the report align with each other"
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
    credibility_assessment: CredibilityAssessment = Field(
        description="Assessment of the report's credibility and potential exaggeration"
    )

    class Config:
        from_attributes = True  # Updated from orm_mode=True for Pydantic v2



