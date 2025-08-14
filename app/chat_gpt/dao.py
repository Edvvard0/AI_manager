from sqlalchemy import select, desc
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
