from pydantic import BaseModel 
from typing import Optional, List

class CreateProfileRequest(BaseModel):
    name: str

class ProfileResponse(BaseModel):
    id: str
    name: str
    gender: str 
    gender_probability: float
    sample_size: int
    age: int 
    age_group: str 
    country_id: str 
    country_probability: float
    created_at: str

class SingleProfileResponse(BaseModel):
    status: str
    data: ProfileResponse

class AllProfileResponse(BaseModel):
    status: str
    count: int 
    data: List[ProfileResponse]


class ErrorResponse(BaseModel):
    status: str