from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.dao.base import BaseDAO
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate


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

    @classmethod
    async def create_task(cls, session: AsyncSession, task_data: TaskCreate) -> Task:
        # создаём объект
        new_task = Task(**task_data.model_dump())
        session.add(new_task)
        await session.commit()
        await session.refresh(new_task)  # обновляем объект из БД, теперь есть id
        return new_task

    @classmethod
    async def find_all(cls, session: AsyncSession):
        result = await session.execute(
            select(Task)
            .options(
                joinedload(Task.executor),  # подгрузим исполнителя
                joinedload(Task.chats)      # подгрузим чат
            )
        )
        return result.scalars().all()

    @classmethod
    async def find_one_or_none_by_id(cls, session: AsyncSession, task_id: int):
        result = await session.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                joinedload(Task.executor),  # подгрузим исполнителя
                joinedload(Task.chats)      # подгрузим чат
            )
        )
        return result.scalar_one_or_none()