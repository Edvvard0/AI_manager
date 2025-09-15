from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    """
    Создание проекта по tg_id пользователя.
    """
    title: str
    tg_id: int


class ProjectUpdate(BaseModel):
    title: str


class ProjectOut(BaseModel):
    id: int
    title: str
    vector_store_id: Optional[int] = None
    created_at: datetime
    user_id: int

    # Pydantic v2: разрешаем брать данные из ORM-объектов
    model_config = {"from_attributes": True}