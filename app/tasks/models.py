from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import TSVectorType

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str]
    description: Mapped[str]
    deadline_date: Mapped[date]

    executor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # связь только с проектом
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str]
    comment: Mapped[Optional[str]] = mapped_column(nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(nullable=True)

    executor: Mapped["User"] = relationship(back_populates="tasks")
    project: Mapped["Project"] = relationship(back_populates="tasks")

    search_vector: Mapped[str] = mapped_column(
        TSVectorType("title", "description"), nullable=True
    )

    __table_args__ = (
        Index("ix_tasks_search", "search_vector", postgresql_using="gin"),
    )
