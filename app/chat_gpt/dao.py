from datetime import datetime, timedelta

from sqlalchemy import select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.chat_gpt.models import Chat, Message
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
            .order_by(desc(Chat.created_at))
        )
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def create_chat_by_tg_id(cls, session: AsyncSession, tg_id: int, title: str):
        # Ищем пользователя по tg_id
        user_query = select(User).where(User.tg_id == tg_id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user:
            return None  # пользователь не найден

        new_chat = Chat(user_id=user.id, title=title)
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
