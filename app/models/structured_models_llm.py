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
    impact_score: int = Field(
        ge=1,
        le=10,
        description="Impact rating from 1 to 10, where 1-3 is individual level, 4-6 is section level, 7-8 is wing level, 9-10 is HQ strategic level"
    )
    impact_reason: str = Field(
        max_length=180,
        description="Brief reason for the impact rating (max 120 characters), explaining which organizational level was impacted"
    )
    vision_verification: Literal["supported", "contradicted", "none"] = Field(
        default="none",
        description="If vision data confirms this achievement, set to 'supported'. If vision data contradicts it, set to 'contradicted'. If NO vision data appears in your prompt or it does not exist for the specific achievement, set the key to 'none'"
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
    impact_score: int = Field(
        ge=1,
        le=10,
        description="Impact rating from 1 to 10, where 1-3 is individual level, 4-6 is section level, 7-8 is wing level, 9-10 is HQ strategic level"
    )
    impact_reason: str = Field(
        max_length=180,
        description="Brief reason for the impact rating (max 80 characters), explaining which organizational level was impacted"
    )
    vision_verification: Literal["supported", "contradicted", "none"] = Field(
        default="none",
        description="If vision data confirms this achievement, set to 'supported'. If vision data contradicts it, set to 'contradicted'. If NO vision data appears in your prompt or it does not exist for the specific achievement, set the key to 'none'"
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

# Models for Quarterly Analysis
class KeyInitiative(BaseModel):
    initiative: str = Field(
        description="Name of the strategic initiative"
    )
    alignment: Literal["high", "medium", "low"] = Field(
        description="Level of alignment with organizational priorities"
    )
    outcomes: str = Field(
        description="Concrete mission outcomes achieved through this initiative"
    )

class StrategicAlignment(BaseModel):
    organizational_impact: Literal["individual", "cell", "unit", "section", "wing", "hq"] = Field(
        description="Scope of impact the employee's work has had"
    )
    key_initiatives: List[KeyInitiative] = Field(
        description="Strategic initiatives the employee has contributed to"
    )
    role_alignment: Literal["strong", "partial", "weak"] = Field(
        description="How well employee's work aligns with job description responsibilities across the quarter"
    )
    role_fit_assessment: str = Field(
        description="Detailed assessment of Job Description fit, including stretch contributions beyond role scope and any gaps between role requirements and actual work patterns"
    )

class AchievementTheme(BaseModel):
    theme: str = Field(
        description="Name of the achievement theme grouping related accomplishments"
    )
    related_achievements: List[str] = Field(
        description="List of specific achievements within this theme, including both activities performed and their outcomes. Each achievement should capture what was done and its measurable impact (e.g., 'Developed cross-reference methodology reducing discrepancies by 35%')."
    )
    impact_score: int = Field(
        ge=1,
        le=10,
        description="Impact rating from 1 to 10, where 1-3 is individual level, 4-6 is section level, 7-8 is wing level, 9-10 is HQ strategic level"
    )
    impact_reason: str = Field(
        max_length=180,
        description="Brief reason for the impact rating (max 120 characters), explaining which organizational level was impacted and why"
    )
    vision_verification: Literal["supported", "contradicted", "none"] = Field(
        default="none",
        description="If vision data confirms this achievement theme, set to 'supported'. If vision data contradicts it, set to 'contradicted'. If NO vision data appears in your prompt or it does not exist for the specific achievement, set the key to 'none'"
    )

class ConsistencyMetrics(BaseModel):
    task_completion_reliability: Literal["high", "medium", "low"] = Field(
        description="Reliability in completing planned tasks"
    )
    work_quality_consistency: Literal["high", "medium", "low"] = Field(
        description="Consistency of work quality throughout the quarter"
    )
    performance_stability: Literal["high", "medium", "low"] = Field(
        description="Stability of performance across the quarter"
    )

class NotableShift(BaseModel):
    month: str = Field(
        description="Month when a notable performance shift occurred"
    )
    description: str = Field(
        description="Description of what changed in performance"
    )
    factors: str = Field(
        description="Factors that contributed to this change"
    )

class PerformanceTrajectory(BaseModel):
    trend: Literal["improving", "stable", "declining", "mixed"] = Field(
        description="Overall trend in employee's performance over the quarter"
    )
    consistency: ConsistencyMetrics = Field(
        description="Metrics related to performance consistency"
    )
    notable_shifts: List[NotableShift] = Field(
        description="Significant shifts in performance during the quarter"
    )

class QuarterlyRecurringChallenge(BaseModel):
    description: str = Field(
        description="Description of a recurring challenge"
    )
    type: Literal["internal", "external"] = Field(
        description="Whether the challenge is internal (organizational) or external"
    )
    frequency: Literal["constant", "intermittent", "decreasing", "increasing"] = Field(
        description="Pattern of occurrence for this challenge"
    )
    resolution_status: Literal["resolved", "ongoing"] = Field(
        description="Current status of this challenge"
    )
    systemic: bool = Field(
        description="Whether this is a systemic issue or specific to the employee"
    )

class ChallengePatterns(BaseModel):
    recurring_challenges: List[QuarterlyRecurringChallenge] = Field(
        description="Challenges that recurred throughout the quarter"
    )
    adaptation_effectiveness: Literal["high", "medium", "low"] = Field(
        description="How effectively the employee adapted to challenges"
    )

class StakeholderImpact(BaseModel):
    stakeholder: str = Field(
        description="Team or department impacted by the employee's work"
    )
    collaboration_type: Literal[
        "Leading Initiative",
        "Contributing Expertise",
        "Mentoring",
        "Process Improvement"
    ] = Field(
        description="Type of collaboration: leading_initiative (coordinating across Wings/Sections), contributing_expertise (specialized knowledge to other teams), mentoring (knowledge transfer/capability building), process_improvement (benefiting multiple units)"
    )
    impact: str = Field(
        description="Description of the impact on this stakeholder"
    )
    evidence: str = Field(
        description="Concrete example demonstrating this impact"
    )

class CrossFunctionalImpact(BaseModel):
    collaboration_effectiveness: Literal["high", "medium", "low"] = Field(
        description="Effectiveness of collaboration with other teams/departments across the quarter"
    )
    stakeholder_impacts: List[StakeholderImpact] = Field(
        description="Specific collaboration activities with different stakeholders. Each represents a distinct collaboration pattern with its type, impact, and supporting evidence."
    )

class Capability(BaseModel):
    skill: str = Field(
        description="Name of the skill or capability"
    )
    proficiency: Literal["developing", "proficient", "advanced"] = Field(
        description="Current proficiency level in this skill"
    )
    growth: Literal["improved", "stable", "declined"] = Field(
        description="How this skill has changed over the quarter"
    )

class SkillDevelopment(BaseModel):
    key_capabilities: List[Capability] = Field(
        description="Key skills demonstrated or developed during the quarter"
    )
    learning_agility: Literal["high", "medium", "low"] = Field(
        description="Employee's ability to learn and adapt to new information"
    )
    autonomy_level: Literal["high", "medium", "low"] = Field(
        description="Level of independence in executing responsibilities"
    )
    development_focus: str = Field(
        description="Recommended skill or capability to develop next"
    )

class BehaviorAssessment(BaseModel):
    rating: Literal["below", "meets", "exceeds"] = Field(
        description="Rating relative to expectations"
    )
    evidence: str = Field(
        description="Observable example of this behavior"
    )

class BehavioralAssessment(BaseModel):
    ownership: BehaviorAssessment = Field(
        description="Assessment of ownership and accountability"
    )
    collaboration: BehaviorAssessment = Field(
        description="Assessment of collaboration and teamwork"
    )
    communication: BehaviorAssessment = Field(
        description="Assessment of communication effectiveness"
    )
    problem_solving: BehaviorAssessment = Field(
        description="Assessment of problem-solving approach"
    )
    quality_standards: BehaviorAssessment = Field(
        description="Assessment of quality standards and craft"
    )

class QuarterlyRiskAssessment(BaseModel):
    overall_risk_level: Literal["low", "medium", "high"] = Field(
        description="Overall risk assessment for the quarter"
    )
    risk_trend: Literal["increasing", "stable", "decreasing"] = Field(
        description="Trend in risk level over the quarter"
    )
    key_risk_factors: List[str] = Field(
        description="Specific factors contributing to risk"
    )
    mitigation_strategies: List[str] = Field(
        description="Recommended strategies to mitigate identified risks"
    )

class QuarterlyCredibilityAssessment(BaseModel):
    rating: Literal["high", "medium", "low"] = Field(
        description="Overall credibility rating of the employee's reporting"
    )
    explanation: str = Field(
        description="Rationale for the credibility assessment"
    )
    vision_data_alignment: Optional[Literal["high", "medium", "low", "none"]] = Field(
        description="Alignment between self-reported activities and vision system data. Set to 'high' if vision data strongly validates claims, 'medium' if partially validates, 'low' if contradicts or shows significant discrepancies. If NO vision data exists for this employee, either OMIT this key entirely OR set to 'none' (both are acceptable)."
    )
    impact_on_evaluation: str = Field(
        description="How credibility concerns affected the overall assessment"
    )

class Recommendation(BaseModel):
    action: str = Field(
        description="The recommended action in clear, actionable language"
    )
    priority: Literal["high", "medium", "low"] = Field(
        description="Priority level: high (immediate intervention needed), medium (address within next quarter), low (desirable improvements)"
    )
    ownership: Literal["employee", "manager", "hr", "cross-team"] = Field(
        description="Who is responsible for implementing this recommendation: employee (independent action), manager (intervention/approval required), hr (HR resources/training/policy support), cross-team (coordination with other Wings/Sections)"
    )

class ForwardPlanning(BaseModel):
    keep_doing: List[Recommendation] = Field(
        description="Activities the employee should continue (with rationale for value)"
    )
    improve: List[Recommendation] = Field(
        description="Areas where the employee should focus on enhancement (with specific actions)"
    )
    start: List[Recommendation] = Field(
        description="New initiatives or activities the employee should begin (growth opportunities)"
    )
    stop: List[Recommendation] = Field(
        description="Activities the employee should discontinue (low value or ineffective, provide alternatives)"
    )
    support_needed: List[Recommendation] = Field(
        description="Resources or support required for success (with justification and timeline context)"
    )

class QuarterlyAnalysis(BaseModel):
    strategic_alignment: StrategicAlignment = Field(
        description="Assessment of alignment with organizational goals"
    )
    achievement_themes: List[AchievementTheme] = Field(
        description="Thematic grouping of achievements across the quarter"
    )
    performance_trajectory: PerformanceTrajectory = Field(
        description="Analysis of performance trends over the quarter"
    )
    challenge_patterns: ChallengePatterns = Field(
        description="Analysis of recurring challenges and adaptation"
    )
    cross_functional_impact: CrossFunctionalImpact = Field(
        description="Assessment of impact across teams and departments"
    )
    risk_assessment: QuarterlyRiskAssessment = Field(
        description="Assessment of risks for the next quarter"
    )
    skill_development: SkillDevelopment = Field(
        description="Evaluation of skills demonstrated and developed"
    )
    behavioral_assessment: BehavioralAssessment = Field(
        description="Assessment of key workplace behaviors"
    )
    credibility_assessment: QuarterlyCredibilityAssessment = Field(
        description="Assessment of reporting credibility"
    )
    forward_planning: ForwardPlanning = Field(
        description="Recommendations for future focus"
    )
    quarterly_summary: str = Field(
        description="Executive summary of quarterly performance"
    )

    class Config:
        from_attributes = True



