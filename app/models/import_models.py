from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum

from app.models.base import Base
from app.models.base import schema_name

# Define status values
class ImportStatus(str, enum.Enum):
    """Enum for import job statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class CSVImportJob(Base):
    """Model for tracking CSV import jobs."""
    __tablename__ = "csv_import_jobs"
    
    # Primary key
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Job metadata
    filename = Column(String, nullable=False)
    # Use String instead of Enum type for database compatibility
    status = Column(String, default=ImportStatus.PENDING.value, nullable=False)
    
    # Timestamps
    submitted_at = Column(DateTime, default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metrics
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Import results counts
    employees_created = Column(Integer, default=0)
    employees_updated = Column(Integer, default=0)
    reports_created = Column(Integer, default=0)
    reports_updated = Column(Integer, default=0)
    
    # Options/configuration
    options = Column(JSONB, nullable=True)
    
    # Relationships
    errors = relationship("ImportError", back_populates="job", cascade="all, delete-orphan")
    
    # Add check constraint for valid status values
    __table_args__ = (
        CheckConstraint(
            status.in_([s.value for s in ImportStatus]),
            name='check_valid_import_status'
        ),
    )
    
    def __repr__(self):
        return f"<CSVImportJob(id={self.job_id}, status={self.status})>"

class ImportError(Base):
    """Model for tracking individual row errors during CSV imports."""
    __tablename__ = "import_errors"
    
    # Primary key
    error_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to import job
    job_id = Column(UUID(as_uuid=True), ForeignKey(f"{schema_name}.csv_import_jobs.job_id", ondelete="CASCADE"), nullable=False)
    
    # Error details
    row_number = Column(Integer, nullable=False)
    field_name = Column(String, nullable=True)
    error_message = Column(Text, nullable=False)
    row_data = Column(JSONB, nullable=True)  # Store the original row data for reference
    
    # Relationship
    job = relationship("CSVImportJob", back_populates="errors")
    
    def __repr__(self):
        return f"<ImportError(job={self.job_id}, row={self.row_number}, field={self.field_name})>"

# Create index for efficient retrieval of errors for a specific job
Index("idx_import_errors_job_id", ImportError.job_id)
# Create index for job_id and row_number combination for quick lookup
Index("idx_import_errors_job_row", ImportError.job_id, ImportError.row_number)
