from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.models.base import Base
from app.models.base import schema_name

class EmployeeVisionData(Base):
    """
    Database model for storing employee data imported from the Vision system.
    This captures activities, interactions, and other tracked elements.
    """
    __tablename__ = "employee_vision_data"
    
    # Primary key
    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to employees table
    employee_id = Column(Integer, ForeignKey(f"{schema_name}.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Date range for the record
    from_date = Column(Date, nullable=False, index=True)
    to_date = Column(Date, nullable=False, index=True)
    
    # Entity data
    main_entity = Column(String, nullable=False, index=True)
    sub_entities = Column(JSONB, nullable=False)  # Stores all quantitative sub-entity data
    sub_entities_content = Column(JSONB, nullable=True)  # Stores all qualitative sub-entity content
    
    # Audit fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship
    employee = relationship("Employee", back_populates="vision_data")
    
    # Add composite unique constraint for the fields used in bulk upsert
    __table_args__ = (
        UniqueConstraint('employee_id', 'from_date', 'to_date', 'main_entity', 
                        name='uix_vision_data_composite'),
        # Keep any existing indexes
        Index('ix_vision_data_employee_id', 'employee_id'),
        Index('ix_vision_data_date_range', 'from_date', 'to_date'),
        {'schema': schema_name}
    )
    
    def __repr__(self):
        return f"<EmployeeVisionData(record_id={self.record_id}, employee_id={self.employee_id}, main_entity='{self.main_entity}')>"
