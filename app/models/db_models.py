from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index, Float, DateTime
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
    meta_data = Column(JSONB, nullable=True)  # Optional metadata in JSON format

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
    risk_explanation = Column(String, nullable=True)  # Add this line
    
    # Complete analysis output
    full_analysis_json = Column(JSONB, nullable=False)
    
    # Auditing fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    report = relationship("Report", back_populates="analyses")
    employee = relationship("Employee", back_populates="analyses")
    
    def __repr__(self):
        return f"<EmployeeAnalysis(analysis_id={self.analysis_id}, report_id={self.report_id}, date={self.analysis_date})>"

    # Commented out advanced fields for simplicity during initial testing
    """
    # Additional structured fields for common queries
    achievements_summary = Column(String, nullable=True)
    challenges_summary = Column(String, nullable=True)
    opportunities_text = Column(String, nullable=True)
    
    # Semi-structured data
    action_items_json = Column(JSONB, nullable=True)  # JSON array of recommended actions
    
    # Notes on full_analysis_json benefits:
    # 1. Schema flexibility: Can store any structure the LLM generates without database migrations
    # 2. Future-proofing: New analysis metrics can be added without schema changes
    # 3. Rich data: Can store nested objects and arrays that would be complex in relational format
    # 4. Queryable: Modern databases allow querying into JSON structures (e.g., full_analysis_json->>'technical_score')
    # 5. Full context: Preserves complete analysis even if we only extract specific fields to structured columns
    # 6. Visualization flexibility: Frontend can access all data dimensions for advanced visualizations
    """

# Add relationship backref to existing models
Report.analyses = relationship("EmployeeAnalysis", back_populates="report", cascade="all, delete-orphan")
Employee.analyses = relationship("EmployeeAnalysis", back_populates="employee")