from sqlalchemy import Column, Integer, String
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

metadata = MetaData(schema="employee_reports")
Base = declarative_base(metadata=metadata)

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    wing = Column(String, nullable=False, index=True)
    position = Column(String, nullable=False, index=True)

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.name}', wing_section='{self.wing}', role_position='{self.position}')>"
