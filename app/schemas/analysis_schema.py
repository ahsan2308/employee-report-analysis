from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import date

class Achievement(BaseModel):
    """Schema for achievement in analysis."""
    description: str = Field(description="Detailed description of the achievement")
    impact_score: int = Field(description="Impact rating from 1 to 10")
    impact_reason: str = Field(description="Brief reason for the impact rating, explaining which organizational level was impacted")
    vision_verification: str = Field(description="Vision data verification status: supported/contradicted/none")

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

    model_config = ConfigDict(from_attributes=True)

# New schemas for monthly analysis
class MonthlyAchievement(BaseModel):
    """Schema for monthly achievement."""
    description: str = Field(description="Detailed description of a significant monthly achievement")
    impact_score: int = Field(description="Impact rating from 1 to 10")
    impact_reason: str = Field(description="Brief reason for the impact rating")
    vision_verification: str = Field(description="Vision data verification status: supported/contradicted/none")

class RecurringChallenge(BaseModel):
    """Schema for recurring challenge."""
    description: str = Field(description="Detailed description of a challenge that appeared multiple times")
    severity: str = Field(description="Overall severity of this recurring challenge: low/medium/high")
    status: str = Field(description="Current status: addressed/ongoing/resolved/worsening")

class FocusArea(BaseModel):
    """Schema for focus area."""
    project: str = Field(description="Project or responsibility name")
    time_investment: str = Field(description="Level of time invested: high/medium/low")
    priority_level: str = Field(description="Priority level of this focus area: high/medium/low")

class StrategicRecommendation(BaseModel):
    """Schema for strategic recommendation."""
    action: str = Field(description="Specific action to enhance performance or address challenges")
    priority: str = Field(description="Priority level: high/medium/low")

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
    significant_risks: List[str] = Field(description="Most significant risks identified across all weeks")
    escalating_risks: List[str] = Field(description="Risks that are escalating and require attention")
    risk_mitigation_recommendations: List[str] = Field(description="Recommendations for mitigating identified risks")

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
    monthly_achievements: List[MonthlyAchievement]
    recurring_challenges: List[RecurringChallenge]
    consistency_assessment: ConsistencyAssessment
    growth_indicators: GrowthIndicators
    focus_areas: List[FocusArea]
    monthly_risk_assessment: MonthlyRiskAssessment
    strategic_recommendations: List[StrategicRecommendation]
    
    # Summary
    monthly_summary: str
    
    model_config = ConfigDict(from_attributes=True)

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
    
    model_config = ConfigDict(from_attributes=True)

# Schemas for quarterly analysis
class Recommendation(BaseModel):
    """Schema for action recommendations."""
    action: str = Field(description="The recommended action in clear, actionable language")
    priority: str = Field(description="Priority level: high/medium/low")
    ownership: str = Field(description="Who is responsible: employee/manager/hr/cross-team")

class KeyInitiative(BaseModel):
    """Schema for strategic initiatives."""
    initiative: str = Field(description="Name of the strategic initiative")
    alignment: str = Field(description="Level of alignment with organizational priorities: high/medium/low")
    outcomes: str = Field(description="Concrete mission outcomes achieved through this initiative")

class StrategicAlignment(BaseModel):
    """Schema for strategic alignment assessment."""
    organizational_impact: str = Field(description="Scope of impact: individual/team/department/organization")
    key_initiatives: List[KeyInitiative] = Field(description="Key strategic initiatives the employee contributed to")
    role_alignment: str = Field(description="How well employee's work aligns with job description: strong/partial/weak")
    role_fit_assessment: str = Field(description="Detailed assessment of Job Description fit")

class AchievementTheme(BaseModel):
    """Schema for achievement theme grouping."""
    theme: str = Field(description="Name of the achievement theme grouping related accomplishments")
    related_achievements: List[str] = Field(description="List of specific achievements within this theme")
    impact_score: int = Field(description="Impact rating from 1 to 10")
    impact_reason: str = Field(description="Brief reason for the impact rating")
    vision_verification: str = Field(description="Vision data verification status: supported/contradicted/none")

class ConsistencyMetrics(BaseModel):
    """Schema for consistency metrics."""
    task_completion_reliability: str = Field(description="Reliability in completing planned tasks: high/medium/low")
    work_quality_consistency: str = Field(description="Consistency of work quality: high/medium/low")
    performance_stability: str = Field(description="Stability of performance: high/medium/low")

class NotableShift(BaseModel):
    """Schema for notable performance shifts."""
    month: str = Field(description="Month when a notable performance shift occurred")
    description: str = Field(description="Description of what changed in performance")
    factors: str = Field(description="Factors that contributed to this change")

class PerformanceTrajectory(BaseModel):
    """Schema for quarterly performance trajectory."""
    trend: str = Field(description="Overall trend: improving/stable/declining/mixed")
    consistency: ConsistencyMetrics = Field(description="Metrics for work consistency and reliability")
    notable_shifts: List[NotableShift] = Field(description="Significant shifts in performance during the quarter")

class StakeholderImpact(BaseModel):
    """Schema for stakeholder impact."""
    stakeholder: str = Field(description="Team or department impacted by the employee's work")
    collaboration_type: str = Field(description="Type of collaboration: leading_initiative/contributing_expertise/mentoring/process_improvement")
    impact: str = Field(description="Description of the impact on this stakeholder")
    evidence: str = Field(description="Concrete example demonstrating this impact")

class CrossFunctionalImpact(BaseModel):
    """Schema for cross-functional impact assessment."""
    collaboration_effectiveness: str = Field(description="Effectiveness of collaboration: high/medium/low")
    stakeholder_impacts: List[StakeholderImpact] = Field(description="Impact on various stakeholders")

class RiskAssessment(BaseModel):
    """Schema for quarterly risk assessment."""
    overall_risk_level: str = Field(description="Overall risk assessment: low/medium/high")
    risk_trend: str = Field(description="Risk trend: increasing/stable/decreasing")
    key_risk_factors: List[str] = Field(description="Specific factors contributing to risk")
    mitigation_strategies: List[str] = Field(description="Recommended strategies to mitigate identified risks")

class Capability(BaseModel):
    """Schema for skill/capability."""
    skill: str = Field(description="Name of the skill or capability")
    proficiency: str = Field(description="Current proficiency level: developing/proficient/advanced")
    growth: str = Field(description="How this skill has changed: improved/stable/declined")

class SkillDevelopment(BaseModel):
    """Schema for quarterly skill development assessment."""
    key_capabilities: List[Capability] = Field(description="Key capabilities demonstrated during the quarter")
    learning_agility: str = Field(description="Learning agility: high/medium/low")
    autonomy_level: str = Field(description="Level of independence: high/medium/low")
    development_focus: str = Field(description="Recommended skill to develop next")

class BehaviorAssessment(BaseModel):
    """Schema for individual behavior assessment."""
    rating: str = Field(description="Rating relative to expectations: below/meets/exceeds")
    evidence: str = Field(description="Observable example of this behavior")

class BehavioralAssessment(BaseModel):
    """Schema for behavioral assessment across key areas."""
    ownership: BehaviorAssessment = Field(description="Assessment of ownership and accountability")
    collaboration: BehaviorAssessment = Field(description="Assessment of collaboration and teamwork")
    communication: BehaviorAssessment = Field(description="Assessment of communication effectiveness")
    problem_solving: BehaviorAssessment = Field(description="Assessment of problem-solving approach")
    quality_standards: BehaviorAssessment = Field(description="Assessment of quality standards and craft")

class QuarterlyCredibilityAssessment(BaseModel):
    """Schema for quarterly credibility assessment."""
    rating: str = Field(description="Overall credibility rating: high/medium/low")
    explanation: str = Field(description="Rationale for the credibility assessment")
    vision_data_alignment: Optional[str] = Field(description="Alignment between self-reported activities and vision data: high/medium/low/none")
    impact_on_evaluation: str = Field(description="How credibility concerns affected the overall assessment")

class ForwardPlanning(BaseModel):
    """Schema for forward planning recommendations."""
    keep_doing: List[Recommendation] = Field(description="Activities the employee should continue")
    improve: List[Recommendation] = Field(description="Areas where the employee should focus on enhancement")
    start: List[Recommendation] = Field(description="New initiatives or activities the employee should begin")
    stop: List[Recommendation] = Field(description="Activities the employee should discontinue")
    support_needed: List[Recommendation] = Field(description="Resources or support required for success")

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
    strategic_alignment: StrategicAlignment
    
    # Performance metrics
    performance_trend: str
    task_completion_reliability: str
    work_quality_consistency: str
    performance_stability: str
    achievement_themes: List[AchievementTheme]
    performance_trajectory: PerformanceTrajectory
    
    # Cross-functional impact
    collaboration_effectiveness: str
    stakeholder_count: int
    challenge_patterns: Dict[str, Any]
    cross_functional_impact: CrossFunctionalImpact
    adaptation_effectiveness: str
    
    # Risk assessment
    risk_level: str
    risk_trend: str
    risk_assessment: RiskAssessment
    
    # Skills and development
    learning_agility: str
    autonomy_level: str
    development_focus: str
    skill_development: SkillDevelopment
    behavioral_assessment: BehavioralAssessment
    
    # Credibility assessment
    credibility_rating: str
    vision_data_alignment: str
    credibility_assessment: QuarterlyCredibilityAssessment
    
    # Forward planning
    forward_planning: ForwardPlanning
    
    # Summary
    quarterly_summary: str
    
    model_config = ConfigDict(from_attributes=True)
