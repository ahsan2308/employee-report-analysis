from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
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

# New schemas for monthly analysis
class ProgressTrends(BaseModel):
    """Schema for employee progress trends over a month."""
    sentiment_trend: str = Field(description="Trend direction of sentiment (improving, declining, stable)")
    performance_trend: str = Field(description="Performance trend (improving, declining, stable)")
    risk_level_pattern: str = Field(description="Risk level pattern (increasing, decreasing, stable)")
    challenge_resolution_progress: str = Field(description="Progress in resolving challenges (improved, declined, unchanged)")

class ConsistencyAssessment(BaseModel):
    """Schema for monthly consistency assessment."""
    task_completion_reliability: str = Field(description="Reliability in completing planned tasks (high, medium, low)")
    work_quality_consistency: str = Field(description="Consistency of work quality (high, medium, low)")
    performance_stability: str = Field(description="Stability of performance across weeks (high, medium, low)")
    notable_strengths: List[str] = Field(description="Notable strengths in consistency")
    notable_weaknesses: List[str] = Field(description="Notable weaknesses in consistency")

class GrowthIndicators(BaseModel):
    """Schema for employee growth indicators."""
    complexity_of_tasks: str = Field(description="Changes in task complexity (increased, decreased, unchanged)")
    skill_development_evidence: str = Field(description="Evidence of skill development (high, medium, low)")
    confidence_level_change: str = Field(description="Change in confidence level (increased, decreased, unchanged)")
    approach_to_challenges: str = Field(description="Approach to challenges (more proactive, more reactive, unchanged)")

class MonthlyRiskAssessment(BaseModel):
    """Schema for monthly risk assessment."""
    overall_risk_level: str = Field(description="Overall risk assessment (low, medium, high)")
    risk_explanation: str = Field(description="Explanation of risk assessment")
    significant_risks: List[Dict[str, Any]] = Field(description="List of significant risks identified")
    escalating_risks: List[Dict[str, Any]] = Field(description="List of escalating risks requiring attention")
    risk_mitigation_recommendations: List[Dict[str, Any]] = Field(description="Recommendations for mitigating identified risks")

class MonthlyAnalysisResponse(BaseModel):
    """Schema for monthly analysis response."""
    analysis_id: int
    employee_id: int
    employee_name: str
    year: int
    month: int
    period_start: date
    period_end: date
    
    # Core metrics
    avg_sentiment_score: Optional[float] = None
    
    # Structured analysis components
    progress_trends: ProgressTrends
    monthly_achievements: List[Dict[str, Any]]
    recurring_challenges: List[Dict[str, Any]]
    consistency_assessment: ConsistencyAssessment
    growth_indicators: GrowthIndicators
    focus_areas: List[Dict[str, Any]]
    monthly_risk_assessment: MonthlyRiskAssessment
    strategic_recommendations: List[Dict[str, Any]]
    
    # Summary
    monthly_summary: str
    
    class Config:
        from_attributes = True

class MonthlyAnalysisSummary(BaseModel):
    """Schema for summarized monthly analysis in list responses."""
    analysis_id: int
    employee_id: int
    year: int
    month: int
    period_start: date
    period_end: date
    performance_trend: str
    sentiment_trend: str
    risk_level: str
    achievement_count: int
    challenge_count: int
    monthly_summary: str
    
    class Config:
        from_attributes = True

# Schemas for quarterly analysis
class StrategicAlignment(BaseModel):
    """Schema for strategic alignment assessment."""
    organizational_impact: str = Field(description="Scope of impact: individual/team/department/organization")
    key_initiatives: List[Dict[str, Any]] = Field(description="Key strategic initiatives the employee contributed to")
    alignment_rating: str = Field(description="How well the employee's work aligns with organizational goals")

class PerformanceTrajectory(BaseModel):
    """Schema for quarterly performance trajectory."""
    trend: str = Field(description="Overall trend: improving/stable/declining/mixed")
    consistency: Dict[str, Any] = Field(description="Metrics for work consistency and reliability")
    notable_shifts: List[Dict[str, Any]] = Field(description="Significant shifts in performance during the quarter")

class CrossFunctionalImpact(BaseModel):
    """Schema for cross-functional impact assessment."""
    collaboration_effectiveness: str = Field(description="Effectiveness of collaboration: high/medium/low")
    stakeholder_impacts: List[Dict[str, Any]] = Field(description="Impact on various stakeholders")
    knowledge_sharing: List[Dict[str, Any]] = Field(description="Knowledge sharing contributions")

class RiskAssessment(BaseModel):
    """Schema for quarterly risk assessment."""
    overall_risk_level: str = Field(description="Overall risk assessment: low/medium/high")
    risk_trend: str = Field(description="Risk trend: increasing/stable/decreasing")
    key_risk_factors: List[Dict[str, Any]] = Field(description="Key factors contributing to risk assessment")
    mitigation_strategies: List[Dict[str, Any]] = Field(description="Recommended strategies for risk mitigation")

class SkillDevelopment(BaseModel):
    """Schema for quarterly skill development assessment."""
    key_capabilities: List[Dict[str, Any]] = Field(description="Key capabilities demonstrated during the quarter")
    learning_agility: str = Field(description="Learning agility: high/medium/low")
    autonomy_level: str = Field(description="Level of independence: high/medium/low")
    development_focus: str = Field(description="Recommended skill to develop next")

class QuarterlyAnalysisResponse(BaseModel):
    """Schema for quarterly analysis response."""
    analysis_id: int
    employee_id: int
    employee_name: str
    year: int
    quarter: int
    period_start: date
    period_end: date
    monthly_analysis_ids: Optional[List[int]] = None
    
    # Strategic alignment
    organizational_impact: str
    strategic_alignment: Dict[str, Any]
    
    # Performance metrics
    performance_trend: str
    task_completion_reliability: str
    work_quality_consistency: str
    performance_stability: str
    achievement_themes: List[Dict[str, Any]]
    performance_trajectory: Dict[str, Any]
    
    # Cross-functional impact
    collaboration_effectiveness: str
    stakeholder_count: int
    challenge_patterns: Dict[str, Any]
    cross_functional_impact: Dict[str, Any]
    adaptation_effectiveness: str
    
    # Risk assessment
    risk_level: str
    risk_trend: str
    risk_assessment: Dict[str, Any]
    
    # Skills and development
    learning_agility: str
    autonomy_level: str
    development_focus: str
    skill_development: Dict[str, Any]
    behavioral_assessment: Dict[str, Any]
    
    # Credibility assessment
    credibility_rating: str
    vision_data_alignment: str
    credibility_assessment: Dict[str, Any]
    
    # Forward planning
    forward_planning: Dict[str, Any]
    
    # Summary
    quarterly_summary: str
    
    class Config:
        from_attributes = True
