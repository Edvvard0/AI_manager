from typing import List

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    username: Mapped[str] = mapped_column(nullable=True)
    tg_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    department: Mapped[str] = mapped_column(index=True, nullable=False)
    is_admin: Mapped[bool]= mapped_column(default=False)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="executor", cascade="all, delete-orphan"
    )
    chats: Mapped["Chat"] = relationship(back_populates="user")