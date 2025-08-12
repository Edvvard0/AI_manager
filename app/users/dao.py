import asyncio

from fastapi.params import Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dao.base import BaseDAO
from app.users.models import User


class UserDAO(BaseDAO):
    model = User

    @classmethod
    async def find_chats_by_user_id(cls, session: AsyncSession, user_id: int, options=None):
        query = select(User).filter_by(**{"id": user_id})
        if options:
            query = query.options(*options)
        rez = await session.execute(query)
        otv = rez.scalar_one_or_none()

        return otv

    @classmethod
    async def users_chats_with_me(cls, session: AsyncSession, user):
        # print(user)

        chats_id = [chat.id for chat in user.chats]
        print(chats_id)
        # query = (select(User)
        #          .join(Message, or_(Message.user_from_id == User.id, Message.user_to_id == User.id))
        #          .filter(Chat.user_id.in_(chats_id))
        #          .filter(User.id != user.id)
        #          .distinct()
        #          )
        #
        # rez = await session.execute(query)
        # users = rez.scalars().all()
        #
        # return users
