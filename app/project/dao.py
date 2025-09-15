from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.chat_gpt.models import Chat
from app.dao.base import BaseDAO
from app.project.models import Project
from app.users.models import User


class ProjectDAO(BaseDAO):
    model = Project

    @classmethod
    async def create_by_tg_id(
        cls,
        session,
        *,
        title: str,
        tg_id: int,
        vector_store_id: int | None = None,
    ):
        """
        Создать проект, найдя пользователя по tg_id.
        Возвращает ORM-объект Project или None, если пользователь не найден.
        """
        res = await session.execute(select(User.id).where(User.tg_id == tg_id))
        row = res.first()
        if not row:
            return None

        user_id = row[0]
        project = Project(
            title=title,
            user_id=user_id,
            vector_store_id=None,
        )
        session.add(project)
        # получаем id и created_at без коммита
        await session.flush()
        await session.refresh(project)
        return project

    @classmethod
    async def find_by_tg_id(cls, session, tg_id: int):
        """
        Получение всех проектов, где владелец — пользователь с указанным tg_id
        """
        stmt = (
            select(Project)
            .join(Project.user)
            .where(User.tg_id == tg_id)
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