from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.models.database_postgres import Base

class Report(Base):
    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)  # Stores only the date
    report_text = Column(String, nullable=False)
    qdrant_id = Column(String, unique=True, nullable=True)  # Stores the reference to Qdrant


    def __repr__(self):
        return f"<Report(id={self.report_id}, employee_id={self.employee_id}, report_date={self.report_date}, report_text={self.report_text})>"

# Add a unique index to prevent duplicate reports for the same employee on the same date
Index("idx_unique_report", Report.employee_id, Report.report_date, unique=True)
