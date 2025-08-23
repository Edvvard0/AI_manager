from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    user_id: int


class ProjectUpdate(BaseModel):
    title: str


class ProjectOut(BaseModel):
    id: int
    title: str
    vector_store_id: Optional[int] = None
    created_at: datetime
    user_id: int

    model_config = {"from_attributes": True}