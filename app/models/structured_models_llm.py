"""
Pydantic models for structured data responses.

This module contains all the Pydantic models used for structured data
generation with LLM services. Import these models when you need to
define a structured output format for LLM responses.
"""
from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field
import uuid

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
        from_attributes = True  


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
        from_attributes = True 

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
        from_attributes = True 


class PerformanceAssessment(BaseModel):
    # Model representing a performance assessment for an employee report
    rating: Literal["high", "medium", "low"] = Field(
        description="Overall performance rating of the employee based on the report"
    )
    summary: str = Field(
        description="Brief overall performance assessment summarizing the key findings"
    )
    key_strengths: List[str] = Field(
        description="Notable strengths identified from the report"
    )
    improvement_areas: List[str] = Field(
        description="Specific areas where performance could be enhanced"
    )

    class Config:
        from_attributes = True 


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
    performance_assessment: PerformanceAssessment = Field(
        description="Assessment of the employee's overall performance based on the report"
    )

    class Config:
        from_attributes = True

# Models for Monthly Analysis
class MonthlyAchievement(BaseModel):
    description: str = Field(
        description="Detailed description of a significant monthly achievement"
    )
    impact: str = Field(
        description="Format must be: 'N (reason)' where N is an integer rating 1-10, followed by a concise impact assessment"
    )

class RecurringChallenge(BaseModel):
    description: str = Field(
        description="Detailed description of a challenge that appeared multiple times"
    )
    severity: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Overall severity of this recurring challenge"
    )
    status: Literal["addressed", "ongoing", "resolved", "worsening"] = Field(
        description="Current status of this challenge"
    )

class ProgressTrends(BaseModel):
    performance_trend: Literal["improving", "declining", "stable"] = Field(
        description="Overall trend in employee's performance"
    )
    sentiment_trend: Literal["positive", "negative", "stable"] = Field(
        description="Trend in sentiment across weekly reports"
    )
    risk_level_pattern: Literal["increasing", "decreasing", "stable"] = Field(
        description="Pattern in risk levels over the month"
    )
    challenge_resolution_progress: Literal["improved", "declined", "unchanged"] = Field(
        description="Progress in addressing challenges from earlier weeks"
    )

class ConsistencyAssessment(BaseModel):
    task_completion_reliability: Literal["high", "medium", "low"] = Field(
        description="Reliability in completing planned tasks"
    )
    work_quality_consistency: Literal["high", "medium", "low"] = Field(
        description="Consistency of work quality throughout the month"
    )
    performance_stability: Literal["high", "medium", "low"] = Field(
        description="Variability of performance week-to-week"
    )
    notable_strengths: List[str] = Field(
        description="Areas where the employee consistently performs well"
    )
    notable_weaknesses: List[str] = Field(
        description="Areas where the employee's performance is inconsistent"
    )

class GrowthIndicators(BaseModel):
    complexity_of_tasks: Literal["increased", "decreased", "unchanged"] = Field(
        description="Change in complexity of tasks handled"
    )
    skill_development_evidence: Literal["high", "medium", "low"] = Field(
        description="Evidence of skill development during the month"
    )
    confidence_level_change: Literal["increased", "decreased", "unchanged"] = Field(
        description="Change in employee's confidence level"
    )
    approach_to_challenges: Literal["more proactive", "more reactive", "unchanged"] = Field(
        description="How the employee's approach to challenges has evolved"
    )

class FocusArea(BaseModel):
    project: str = Field(
        description="Project or responsibility name"
    )
    time_investment: Literal["high", "medium", "low"] = Field(
        description="Level of time invested in this area"
    )
    priority_level: Literal["high", "medium", "low"] = Field(
        description="Priority level of this focus area"
    )

class MonthlyRiskAssessment(BaseModel):
    overall_risk_level: Literal["low", "medium", "high"] = Field(
        description="Overall risk assessment for the month"
    )
    risk_explanation: str = Field(
        description="Detailed explanation of the risk assessment and reasoning"
    )
    significant_risks: List[str] = Field(
        description="Most significant risks identified across all weeks"
    )
    escalating_risks: List[str] = Field(
        description="Risks that are escalating and require attention"
    )
    risk_mitigation_recommendations: List[str] = Field(
        description="Recommendations for mitigating identified risks"
    )

class StrategicRecommendation(BaseModel):
    action: str = Field(
        description="Specific action to enhance performance or address challenges"
    )
    priority: Literal["high", "medium", "low"] = Field(
        description="Priority level for this recommendation"
    )

class MonthlyAnalysis(BaseModel):
    progress_trends: ProgressTrends = Field(
        description="Analysis of trends in the employee's progress"
    )
    monthly_achievements: List[MonthlyAchievement] = Field(
        description="Most significant achievements across the month"
    )
    recurring_challenges: List[RecurringChallenge] = Field(
        description="Challenges that appeared multiple times in weekly reports"
    )
    consistency_assessment: ConsistencyAssessment = Field(
        description="Assessment of employee's consistency in performance"
    )
    growth_indicators: GrowthIndicators = Field(
        description="Signs of professional growth observed during the month"
    )
    focus_areas: List[FocusArea] = Field(
        description="Main areas of work the employee focused on"
    )
    monthly_risk_assessment: MonthlyRiskAssessment = Field(
        description="Overall risk assessment for the month"
    )
    strategic_recommendations: List[StrategicRecommendation] = Field(
        description="Strategic recommendations for employee development"
    )
    monthly_summary: str = Field(
        description="Comprehensive summary of the employee's monthly performance"
    )

    class Config:
        from_attributes = True



