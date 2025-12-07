from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index, Float, DateTime, Text, ARRAY, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.base import schema_name
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    wing = Column(String, nullable=False, index=True)
    position = Column(String, nullable=False, index=True)
    
    # Add relationship to vision data
    vision_data = relationship("EmployeeVisionData", back_populates="employee")
    monthly_analyses = relationship("MonthlyAnalysis", back_populates="employee", cascade="all, delete-orphan")
    quarterly_analyses = relationship("QuarterlyAnalysis", back_populates="employee", cascade="all, delete-orphan")
    job_descriptions = relationship("EmployeeJobDescription", back_populates="employee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.name}', wing='{self.wing}', position='{self.position}')>"

class Report(Base):
    __tablename__ = "reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(Integer, ForeignKey(f"{schema_name}.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    report_text = Column(String, nullable=False)

    def __repr__(self):
        return f"<Report(id={self.report_id}, employee_id={self.employee_id}, report_date={self.report_date})>"

# Add a unique index to prevent duplicate reports for the same employee on the same date
Index("idx_unique_report", Report.__table__.c.employee_id, Report.__table__.c.report_date, unique=True)


# Add a new table to store mappings between reports and Qdrant document IDs
class QdrantMapping(Base):
    __tablename__ = "qdrant_mappings"

    qdrant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Qdrant document ID
    report_id = Column(UUID(as_uuid=True), ForeignKey(f"{schema_name}.reports.report_id", ondelete="CASCADE"), nullable=False)  # Foreign key to the reports table
    chunk_index = Column(Integer, nullable=False)  # Index of the chunk
    # meta_data = Column(JSONB, nullable=True)  # Optional metadata in JSON format

    def __repr__(self):
        return f"<QdrantMapping(qdrant_id={self.qdrant_id}, report_id={self.report_id}, chunk_index={self.chunk_index})>"

class EmployeeAnalysis(Base):
    """
    Simplified database model for storing employee report analyses.
    This version focuses on essential fields for initial testing.
    """
    __tablename__ = "employee_analyses"
    
    # Primary key
    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys - these are not redundant as they enable proper relationships
    # Having separate report_id and analysis_id allows multiple analyses per report if needed
    report_id = Column(UUID(as_uuid=True), ForeignKey(f"{schema_name}.reports.report_id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey(f"{schema_name}.employees.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_date = Column(DateTime, default=func.now(), nullable=False)
    
    # Core analysis fields
    sentiment_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)  # "low", "medium", "high"
    risk_explanation = Column(Text, nullable=True)  
    
    # Existing fields for credibility assessment
    credibility_rating = Column(String, nullable=True)
    credibility_explanation = Column(Text, nullable=True)
    exaggeration_flags = Column(JSONB, nullable=True)
    consistency_score = Column(String, nullable=True)
    
    # Fields for performance assessment
    performance_rating = Column(String, nullable=True)
    performance_summary = Column(Text, nullable=True)
    performance_strengths = Column(JSONB, nullable=True)
    performance_improvement_areas = Column(JSONB, nullable=True)
    
    # Complete analysis output
    full_analysis_json = Column(JSONB, nullable=False)
    
    # Additional structured fields for common queries
    achievements_json = Column(JSONB, nullable=True)  # JSON array of achievements with description and impact
    challenges_json = Column(JSONB, nullable=True)   # JSON array of challenges with description and severity
    topics = Column(JSONB, nullable=True)  # JSON array of key topics 
    action_items = Column(JSONB, nullable=True)  # JSON array of recommended actions
    
    # Auditing fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    report = relationship("Report", back_populates="analyses")
    employee = relationship("Employee", back_populates="analyses")
    
    def __repr__(self):
        return f"<EmployeeAnalysis(analysis_id={self.analysis_id}, report_id={self.report_id}, date={self.analysis_date})>"

# Add relationship backref to existing models
Report.analyses = relationship("EmployeeAnalysis", back_populates="report", cascade="all, delete-orphan")
Employee.analyses = relationship("EmployeeAnalysis", back_populates="employee")

class MonthlyAnalysis(Base):
    """
    Monthly aggregated analysis of employee reports.
    Contains insights derived from multiple weekly reports over a month.
    """
    __tablename__ = "monthly_analyses"
    
    # Primary key and relationships
    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Time fields - using separate year and month fields for optimization
    year = Column(Integer, nullable=False, comment="Year of this analysis")
    month = Column(Integer, nullable=False, comment="Month as integer (1-12)")
    period_start = Column(Date, nullable=False, comment="Start date of the analysis period")
    period_end = Column(Date, nullable=False, comment="End date of the analysis period")
    
    # Weekly report references
    weekly_report_ids = Column(ARRAY(UUID), nullable=True, comment="List of weekly report IDs included in this analysis")
    
    # Analysis metrics
    avg_sentiment_score = Column(Float, nullable=True, comment="Average sentiment score across all weekly reports")
    
    # Progress Trends fields (aligned with prompt structure)
    sentiment_trend = Column(String, nullable=True, comment="Trend direction of sentiment (improving, declining, stable)")
    performance_trend = Column(String, nullable=True, comment="Performance trend (improving, declining, stable)")
    risk_level_pattern = Column(String, nullable=True, comment="Risk level pattern (increasing, decreasing, stable)")
    challenge_resolution_progress = Column(String, nullable=True, comment="Progress in resolving challenges (improved, declined, unchanged)")
    
    # Risk Assessment fields (aligned with prompt structure)
    risk_level = Column(String, nullable=True, comment="Overall risk assessment (low, medium, high)")
    risk_explanation = Column(Text, nullable=True, comment="Explanation of risk assessment")
    significant_risks = Column(JSONB, nullable=True, comment="List of significant risks identified")
    escalating_risks = Column(JSONB, nullable=True, comment="List of escalating risks requiring attention")
    risk_mitigation_recommendations = Column(JSONB, nullable=True, comment="Recommendations for mitigating identified risks")
    
    # Monthly Achievements & Challenges
    monthly_achievements = Column(JSONB, nullable=True, comment="Most significant achievements with impact ratings")
    recurring_challenges = Column(JSONB, nullable=True, comment="Challenges that appeared multiple times with severity and status")
    achievement_impact_avg = Column(Float, nullable=True, comment="Average impact score of achievements")
    
    # Consistency Assessment fields (aligned with prompt structure)
    task_completion_reliability = Column(String, nullable=True, comment="Reliability in completing planned tasks (high, medium, low)")
    work_quality_consistency = Column(String, nullable=True, comment="Consistency of work quality (high, medium, low)")
    performance_stability = Column(String, nullable=True, comment="Stability of performance across weeks (high, medium, low)")
    consistency_notable_strengths = Column(JSONB, nullable=True, comment="Notable strengths in consistency")
    consistency_notable_weaknesses = Column(JSONB, nullable=True, comment="Notable weaknesses in consistency")
    
    # Growth Indicators (detailed as per prompt)
    complexity_of_tasks = Column(String, nullable=True, comment="Changes in task complexity (increased, decreased, unchanged)")
    skill_development_evidence = Column(String, nullable=True, comment="Evidence of skill development (high, medium, low)")
    confidence_level_change = Column(String, nullable=True, comment="Change in confidence level (increased, decreased, unchanged)")
    approach_to_challenges = Column(String, nullable=True, comment="Approach to challenges (more proactive, more reactive, unchanged)")
    
    # Focus Areas
    focus_areas = Column(JSONB, nullable=True, comment="Key projects with time investment and priority levels")
    
    # Recommendations
    strategic_recommendations = Column(JSONB, nullable=True, comment="Strategic actions with priority levels")
    
    # Summary and complete data
    monthly_summary = Column(Text, nullable=True, comment="Overall summary of the month's performance")
    full_analysis_json = Column(JSONB, nullable=True, comment="Complete analysis results in JSON format")
    
    # Metadata
    analysis_date = Column(DateTime, default=func.now(), nullable=False)
    
    # Define relationships
    employee = relationship("Employee", back_populates="monthly_analyses")
    
    def __repr__(self):
        """String representation for debugging and logging."""
        month_name = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }.get(self.month, "Unknown")
        
        return f"<MonthlyAnalysis id={self.analysis_id} employee={self.employee_id} period={self.year}-{month_name}>"

Employee.monthly_analyses = relationship("MonthlyAnalysis", back_populates="employee")

class QuarterlyAnalysis(Base):
    """
    Quarterly aggregated analysis of employee performance.
    Contains strategic insights derived from three months of performance data.
    """
    __tablename__ = "quarterly_analyses"
    
    # Primary key and relationships
    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Time fields
    year = Column(Integer, nullable=False, comment="Year of this analysis")
    quarter = Column(Integer, nullable=False, comment="Quarter as integer (1-4)")
    period_start = Column(Date, nullable=False, comment="Start date of the analysis period")
    period_end = Column(Date, nullable=False, comment="End date of the analysis period")
    
    # References to monthly analyses
    monthly_analysis_ids = Column(ARRAY(Integer), nullable=True, comment="List of monthly analysis IDs included in this quarterly analysis")
    
    # Strategic alignment (high value fields extracted)
    organizational_impact = Column(String, nullable=True, comment="Scope of impact: individual/team/department/organization")
    
    # Performance trajectory fields
    performance_trend = Column(String, nullable=True, comment="Overall trend: improving/stable/declining/mixed")
    task_completion_reliability = Column(String, nullable=True, comment="Reliability in completing tasks: high/medium/low")
    work_quality_consistency = Column(String, nullable=True, comment="Consistency of work quality: high/medium/low")
    performance_stability = Column(String, nullable=True, comment="Performance stability: high/medium/low")
    
    # Cross-functional impact
    collaboration_effectiveness = Column(String, nullable=True, comment="Effectiveness of collaboration: high/medium/low")
    stakeholder_count = Column(Integer, nullable=True, comment="Number of stakeholders impacted")
    
    # Risk assessment
    risk_level = Column(String, nullable=True, comment="Overall risk assessment: low/medium/high")
    risk_trend = Column(String, nullable=True, comment="Risk trend: increasing/stable/decreasing")
    
    # Skills and development
    learning_agility = Column(String, nullable=True, comment="Learning agility: high/medium/low")
    autonomy_level = Column(String, nullable=True, comment="Level of independence: high/medium/low")
    development_focus = Column(Text, nullable=True, comment="Recommended skill to develop next")
    
    # Credibility metrics
    credibility_rating = Column(String, nullable=True, comment="Overall credibility: high/medium/low") 
    vision_data_alignment = Column(String, nullable=True, comment="Alignment with vision data: high/medium/low")
    
    # Challenge patterns
    adaptation_effectiveness = Column(String, nullable=True, comment="Effectiveness in adapting to challenges: high/medium/low")
    
    # Complex structures stored as JSONB
    strategic_alignment_json = Column(JSONB, nullable=True, comment="Complete strategic alignment assessment with key initiatives")
    achievement_themes_json = Column(JSONB, nullable=True, comment="Achievement themes with related achievements and impact")
    performance_trajectory_json = Column(JSONB, nullable=True, comment="Significant shifts in performance during the quarter")
    challenge_patterns_json = Column(JSONB, nullable=True, comment="Recurring challenges and their patterns")
    cross_functional_impact_json = Column(JSONB, nullable=True, comment="Impact across teams and departments")
    skill_development_json = Column(JSONB, nullable=True, comment="Skills demonstrated and developed during the quarter")
    behavioral_assessment_json = Column(JSONB, nullable=True, comment="Assessment of key workplace behaviors")
    risk_assessment_json = Column(JSONB, nullable=True, comment="Complete risk assessment with factors and strategies")
    credibility_assessment_json = Column(JSONB, nullable=True, comment="Complete credibility assessment")
    forward_planning_json = Column(JSONB, nullable=True, comment="Recommendations for activities to continue, improve, start, and stop")
    
    # Summary and complete data
    quarterly_summary = Column(Text, nullable=True, comment="Executive summary of quarterly performance")
    full_analysis_json = Column(JSONB, nullable=True, comment="Complete analysis results in JSON format")
    
    # Metadata
    analysis_date = Column(DateTime, default=func.now(), nullable=False)
    
    # Define relationships
    employee = relationship("Employee", back_populates="quarterly_analyses")
    
    def __repr__(self):
        """String representation for debugging and logging."""
        return f"<QuarterlyAnalysis id={self.analysis_id} employee={self.employee_id} period=Q{self.quarter}/{self.year}>"

class EmployeeJobDescription(Base):
    """
    Model for tracking employee job description assignments.
    
    Supports multiple JDs per employee and tracks role changes over time.
    Designed for incremental sync from SQL Server.
    """
    __tablename__ = "employee_job_descriptions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to employee
    employee_id = Column(
        Integer, 
        ForeignKey(f"{schema_name}.employees.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Original JD_ID from SQL Server (for traceability)
    jd_id = Column(String, nullable=False)
    
    # Full job description text
    job_description = Column(Text, nullable=False)
    
    # Role assignment tracking
    assigned_date = Column(Date, nullable=False) 
    end_date = Column(Date, nullable=True)  # NULL if current role
    is_current = Column(Boolean, default=True, nullable=False)
    
    # Audit timestamps (internal PostgreSQL tracking only)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship back to Employee
    employee = relationship("Employee", back_populates="job_descriptions")
    
    # Table constraints and indexes
    __table_args__ = (
        # Prevent duplicate (employee_id, jd_id) assignments
        UniqueConstraint('employee_id', 'jd_id', name='uq_employee_jd_assignment'),
        
        # Index for fast "current JD" lookups (partial index for performance)
        Index(
            'ix_employee_jd_current', 
            'employee_id',
            postgresql_where=(is_current == True)
        ),
        
        # Index for querying by source JD_ID (if needed to trace back to SQL Server)
        Index('ix_employee_jd_jd_id', 'jd_id'),
        
        # Schema
        {'schema': schema_name}
    )
    
    def __repr__(self):
        return f"<EmployeeJobDescription(id={self.id}, employee_id={self.employee_id}, jd_id={self.jd_id}, is_current={self.is_current})>"