from typing import List

from sqlalchemy import select, func, cast, REAL, text, or_
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
    async def search(cls, session: AsyncSession, term: str, limit: int = 20, threshold: float = 0.08):
        """
        Поиск задач по title/description/comment:
        1) pg_trgm (если доступен): columns % term, сортировка similarity DESC
        2) FTS (если доступен): search_vector @@ plainto_tsquery, сортировка ts_rank DESC
        3) Fallback: ILIKE
        """

        # 0) Собираем «единый текст» задачи
        columns = func.concat_ws(
            " ",
            func.coalesce(Task.title, ""),
            func.coalesce(Task.description, ""),
            func.coalesce(Task.comment, ""),
        ).self_group()

        # 1) Пытаемся использовать pg_trgm
        use_trgm = True
        try:
            # set_limit действует в рамках соединения; вызываем на той же сессии
            await session.execute(text("SELECT set_limit(:v)"), {"v": threshold})
            # быстрая проверка наличия similarity()
            await session.execute(text("SELECT similarity('a','a')"))
        except Exception:
            use_trgm = False

        if use_trgm:
            rank = func.similarity(columns, term).label("rank")
            where_clause = columns.op("%")(term)  # триграммный оператор
            stmt = (
                select(Task)
                .where(where_clause)
                .order_by(rank.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            return res.scalars().all()

        # 2) FTS (у тебя есть TSVectorType + GIN-индекс ix_tasks_search)
        try:
            tsq = func.plainto_tsquery(term)
            rank = func.ts_rank_cd(Task.search_vector, tsq)
            stmt = (
                select(Task)
                .where(Task.search_vector.op("@@")(tsq))
                .order_by(rank.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            return res.scalars().all()
        except Exception:
            pass

        # 3) Fallback: простые ILIKE (медленно, но работает везде)
        like = f"%{term}%"
        stmt = (
            select(Task)
            .where(
                or_(
                    Task.title.ilike(like),
                    Task.description.ilike(like),
                    Task.comment.ilike(like),
                )
            )
            .limit(limit)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def find_task_by_tg_id(cls, session: AsyncSession, **filter_by):
        result = await session.execute(
            select(Task)
            .join(Task.executor)  # связываем с таблицей User (или как она у тебя называется)
            .filter_by(**filter_by)  # сюда попадёт tg_id
            .options(
                joinedload(Task.executor),
                joinedload(Task.project)
            )
        )
        return result.scalars().all()
