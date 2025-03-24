from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index
from app.models.base import Base
from app.models.base import schema_name


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

    report_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey(f"{schema_name}.employees.id", ondelete="CASCADE"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    report_text = Column(String, nullable=False)

    def __repr__(self):
        return f"<Report(id={self.report_id}, employee_id={self.employee_id}, report_date={self.report_date})>"

# Add a unique index to prevent duplicate reports for the same employee on the same date
Index("idx_unique_report", Report.__table__.c.employee_id, Report.__table__.c.report_date, unique=True)