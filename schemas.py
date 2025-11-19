from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class ScheduleRequest(BaseModel):
    client_name: str 
    client_email: EmailStr 
    problem_description: str 
    suggested_datetime: datetime 

class ScheduleResponse(BaseModel):
    status: str
    appointment_id: str
    message: str
    scheduled_time: Optional[datetime] = None
