from sqlalchemy import Column, Integer, String
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.models.database_postgres import Base


class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    wing = Column(String, nullable=False, index=True)
    position = Column(String, nullable=False, index=True)


    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.name}', wing_section='{self.wing}', role_position='{self.position}')>"


