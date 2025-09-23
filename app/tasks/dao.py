from typing import List

from fastapi import HTTPException
from sqlalchemy import select, func, cast, REAL, text, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from sqlalchemy import update as sa_update, delete as sa_delete

from app.dao.base import BaseDAO
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskFilter
from app.users.models import User


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
    async def search(
            cls,
            session: AsyncSession,
            term: str,
            tg_id: int,
            limit: int = 20,
            threshold: float = 0.10,
    ):
        # кто ищет
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User with this tg_id not found")

        only_my_filter = None if user.is_admin else (Task.executor_id == user.id)

        term = (term or "").strip()
        if not term:
            return []

        # нормализуем под триграммы (регистрозависимость)
        columns = func.lower(
            func.concat_ws(
                " ",
                func.coalesce(Task.title, ""),
                func.coalesce(Task.description, ""),
                func.coalesce(Task.comment, ""),
            )
        ).self_group()
        term_norm = term.lower()

        # помощник: сериализация задачи с исполнителем
        def _serialize_task(t: Task) -> dict:
            exec_ = t.executor
            return {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "deadline_date": t.deadline_date,
                "status": t.status,
                "comment": t.comment,
                "file_path": t.file_path,
                "tag": t.tag,
                "project_id": t.project_id,
                "executor_id": t.executor_id,
                "executor": None if not exec_ else {
                    "id": exec_.id,
                    "name": exec_.name,
                    "username": exec_.username,
                    "department": exec_.department,
                    "tg_id": exec_.tg_id,
                    "is_admin": exec_.is_admin,
                },
            }

        # пробуем pg_trgm
        use_trgm = True
        try:
            await session.execute(text("SELECT public.set_limit(:v)"), {"v": threshold})
            await session.execute(text("SELECT public.similarity('a','a')"))
        except Exception:
            use_trgm = False

        if use_trgm:
            rank = func.similarity(columns, term_norm).label("rank")
            where_clause = columns.op("%")(term_norm)
            if only_my_filter is not None:
                where_clause = and_(where_clause, only_my_filter)

            stmt = (
                select(Task)
                .options(joinedload(Task.executor))
                .where(where_clause)
                .order_by(rank.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            tasks: List[Task] = res.scalars().unique().all()
            return [_serialize_task(t) for t in tasks]

        # FTS
        try:
            tsq = func.plainto_tsquery(term_norm)
            rank = func.ts_rank_cd(Task.search_vector, tsq)
            where_clause = Task.search_vector.op("@@")(tsq)
            if only_my_filter is not None:
                where_clause = and_(where_clause, only_my_filter)

            stmt = (
                select(Task)
                .options(joinedload(Task.executor))
                .where(where_clause)
                .order_by(rank.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            tasks: List[Task] = res.scalars().unique().all()
            return [_serialize_task(t) for t in tasks]
        except Exception:
            pass

        # ILIKE fallback
        like = f"%{term}%"
        where_clause = or_(
            Task.title.ilike(like),
            Task.description.ilike(like),
            Task.comment.ilike(like),
        )
        if only_my_filter is not None:
            where_clause = and_((where_clause), only_my_filter)

        stmt = (
            select(Task)
            .options(joinedload(Task.executor))
            .where(where_clause)
            .limit(limit)
        )
        res = await session.execute(stmt)
        tasks: List[Task] = res.scalars().unique().all()
        return [_serialize_task(t) for t in tasks]

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


    @classmethod
    async def update(cls, session, filters: dict, **values) -> int:
        conds = [(getattr(cls.model, k) == v) for k, v in filters.items()]
        stmt = sa_update(cls.model).where(*conds).values(**values)
        res = await session.execute(stmt)
        # коммит НЕ здесь
        return res.rowcount or 0

    @classmethod
    async def delete(cls, session, **filters) -> int:
        conds = [(getattr(cls.model, k) == v) for k, v in filters.items()]
        stmt = sa_delete(cls.model).where(*conds)
        res = await session.execute(stmt)
        # коммит НЕ здесь
        return res.rowcount or 0
