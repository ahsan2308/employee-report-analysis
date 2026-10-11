from pydantic import BaseModel, ConfigDict

class EmployeeCreate(BaseModel):
    name: str
    wing: str
    position: str
    
    model_config = ConfigDict(from_attributes=True)
