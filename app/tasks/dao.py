from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base import BaseDAO
from app.tasks.models import Task


class TaskDAO(BaseDAO):
    model = Task

    @classmethod
    async def find_all_by_user_id(cls, session: AsyncSession, user_id: int):
        """
        Возвращает все задачи конкретного пользователя (executor_id).
        """
        query = select(cls.model).where(cls.model.executor_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()
