from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    vector_store_id: Optional[int] = None


class ProjectOut(BaseModel):
    id: int
    title: str
    vector_store_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}