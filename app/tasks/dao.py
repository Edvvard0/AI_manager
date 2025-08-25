from typing import List

from sqlalchemy import select, func, cast, REAL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.dao.base import BaseDAO
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskFilter


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
    async def find_all(cls, session: AsyncSession,  **filter_by):
        result = await session.execute(
            select(Task)
            .filter_by(**filter_by)
            .options(
                joinedload(Task.executor),  # подгрузим исполнителя
                joinedload(Task.project)      # подгрузим чат
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
                joinedload(Task.project)      # подгрузим чат
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def find_by_filters(cls, session: AsyncSession, filters: TaskFilter) -> List[Task]:
        query = select(cls.model)

        if filters.status:
            query = query.where(cls.model.status == filters.status)

        if filters.executor_id:
            query = query.where(cls.model.executor_id == filters.executor_id)

        if filters.project_id:
            query = query.where(cls.model.project_id == filters.project_id)

        if filters.deadline_from:
            query = query.where(cls.model.deadline_date >= filters.deadline_from)

        if filters.deadline_to:
            query = query.where(cls.model.deadline_date <= filters.deadline_to)

        result = await session.execute(query)
        return result.scalars().all()


    @classmethod
    async def search(cls, session: AsyncSession, term: str, limit: int = 20):
        """
        Поиск задач по title, description и comment
        через триграммный fuzzy search (pg_trgm).
        """

        await session.execute(select(func.set_limit(cast(0.05, REAL))))

        # Конкатенация колонок
        columns = (
            func.coalesce(Task.title, "")
            .concat(func.coalesce(Task.description, ""))
            .concat(func.coalesce(Task.comment, ""))
        ).self_group()

        stmt = (
            select(
                Task,
                func.similarity(columns, term).label("rank")
            )
            .where(columns.bool_op("%")(term))
            .order_by(func.similarity(columns, term).desc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        return result.scalars().all()
