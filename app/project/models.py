from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str]  # название проекта
    vector_store_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # id векторного хранилища

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # связи
    chats: Mapped[list["Chat"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")