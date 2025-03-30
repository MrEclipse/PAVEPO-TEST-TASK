"""
СХЕМЫ PYDANTIC
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_superuser: bool

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None


class AudioFileOut(BaseModel):
    id: int
    file_name: str
    file_path: str
    uploaded_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"