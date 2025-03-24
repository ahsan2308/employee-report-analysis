from pydantic import BaseModel

class EmployeeCreate(BaseModel):
    name: str
    wing: str
    position: str