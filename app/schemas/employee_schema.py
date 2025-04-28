from pydantic import BaseModel

class EmployeeCreate(BaseModel):
    name: str
    wing: str
    position: str
    
    class Config:
        from_attributes = True 