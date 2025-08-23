from sqlalchemy import select, or_
from sqlalchemy.orm import aliased

from app.chat_gpt.models import Chat
from app.dao.base import BaseDAO
from app.project.models import Project
from app.users.models import User


class ProjectDAO(BaseDAO):
    model = Project

    @classmethod
    async def find_by_tg_id(cls, session, tg_id: int):
        """
        Получение всех проектов, где владелец — пользователь с указанным tg_id
        """
        stmt = (
            select(Project)
            .join(Project.user)
            .filter(User.tg_id == tg_id)
            .order_by(Project.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_chats(cls, session, project_id: int):
        """
        Список чатов, привязанных к проекту.
        """
        stmt = (
            select(Chat)
            .where(Chat.project_id == project_id)
            .order_by(Chat.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()