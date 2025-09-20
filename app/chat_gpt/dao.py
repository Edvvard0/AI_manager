from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, desc, asc, or_, func, cast, REAL, text, literal, and_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from app.chat_gpt.models import Chat, Message
from app.chat_gpt.schemas import ChatSearchResult
from app.users.models import User
from app.dao.base import BaseDAO


class ChatDAO(BaseDAO):
    model = Chat

    @classmethod
    async def get_chats_by_tg_id(cls, session: AsyncSession, tg_id: int):
        query = (
            select(Chat)
            .join(User, Chat.user_id == User.id)
            .where(User.tg_id == tg_id)
            .where(Chat.project_id == None)
            .order_by(desc(Chat.created_at))
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def create_chat_by_tg_id(
            cls,
            session: AsyncSession,
            tg_id: int,
            title: str,
            project_id: int | None = None
    ):
        # Ищем пользователя по tg_id
        user_query = select(User).where(User.tg_id == tg_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user:
            return None  # пользователь не найден

        new_chat = Chat(user_id=user.id, title=title, project_id=project_id)
        session.add(new_chat)
        await session.commit()
        await session.refresh(new_chat)
        return new_chat

    @classmethod
    async def find_all(cls, session: AsyncSession):
        query = (
            select(Chat)
            .join(User, Chat.user_id == User.id)
            .order_by(desc(Chat.created_at))
        )
        result = await session.execute(query)
        return result.scalars().all()


class MessageDAO(BaseDAO):
    model = Message

    @classmethod
    async def get_messages_by_chat(cls, session: AsyncSession, chat_id: int):
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_history(cls, session: AsyncSession, chat_id: int, limit: int = 10):
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await session.execute(query)
        messages = list(result.scalars().all())

        return list(reversed(messages))


    @classmethod
    async def get_message_today(cls, session: AsyncSession):
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        query = (
            select(Message)
            .where(Message.created_at >= today_start, Message.created_at < today_end)
            .order_by(asc(Message.created_at))
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def add(cls, session: AsyncSession, **values):
        new_instance = cls.model(**values)
        session.add(new_instance)
        await session.flush()  # Только flush, без commit
        await session.refresh(new_instance)  # Обновляем объект чтобы получить ID
        return {
            "id": new_instance.id,
            "is_user": new_instance.is_user,
            "content": new_instance.content,
            "created_at": (
                new_instance.created_at.isoformat()
                if isinstance(new_instance.created_at, datetime) and new_instance.created_at
                else None
            ),
            "file_path": new_instance.file_path,
            "chat_id": new_instance.chat_id
        }


class SearchDAO:
    @classmethod
    async def search_chats_and_messages(
        cls,
        session: AsyncSession,
        query: str,
        tg_id: int,
        threshold: float = 0.05
    ):
        # 0) Кто ищет?
        user = (await session.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User with this tg_id not found")

        # обычный юзер — только свои чаты
        owner_filter = None if user.is_admin else (Chat.user_id == user.id)

        term = (query or "").strip()
        if not term:
            return []

        term_norm = term.lower()

        # 1) Проверяем наличие pg_trgm (similarity) и пытаемся выставить set_limit
        has_trgm = True
        try:
            await session.execute(text("SELECT public.similarity('a','a')"))
        except Exception:
            has_trgm = False

        set_limit_ok = False
        if has_trgm:
            try:
                await session.execute(text("SELECT public.set_limit(:v)"), {"v": threshold})
                set_limit_ok = True
            except Exception:
                set_limit_ok = False

        # 2) Нормализация под регистрозависимые триграммы
        title_l = func.lower(Chat.title)
        content_l = func.lower(Message.content)

        if has_trgm:
            rank = func.greatest(
                func.similarity(title_l, term_norm),
                func.similarity(content_l, term_norm),
            ).label("rank")

            if set_limit_ok:
                where_text = or_(
                    title_l.op("%")(term_norm),
                    content_l.op("%")(term_norm),
                    Chat.title.ilike(f"%{term}%"),
                    Message.content.ilike(f"%{term}%"),
                )
            else:
                where_text = or_(
                    func.similarity(title_l, term_norm) >= threshold,
                    func.similarity(content_l, term_norm) >= threshold,
                    Chat.title.ilike(f"%{term}%"),
                    Message.content.ilike(f"%{term}%"),
                )
        else:
            # без pg_trgm — простой ILIKE
            rank = literal(0).label("rank")
            where_text = or_(
                Chat.title.ilike(f"%{term}%"),
                Message.content.ilike(f"%{term}%"),
            )

        where_clause = where_text if owner_filter is None else and_(owner_filter, where_text)

        stmt = (
            select(
                Chat.id.label("chat_id"),
                Chat.title.label("chat_title"),
                Message.id.label("message_id"),
                Message.content.label("message_content"),
                rank,
            )
            .outerjoin(Message, Chat.id == Message.chat_id)
            .where(where_clause)
            .order_by(text("rank DESC"))
        )

        res = await session.execute(stmt)
        # Если у тебя есть pydantic-модель ChatSearchResult:
        # return [ChatSearchResult(**row._mapping) for row in res.all()]
        return [dict(row._mapping) for row in res.all()]