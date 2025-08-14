# app/chat_gpt/router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.chat_gpt.utils import create_response_gpt, calculate_daily_usage
from app.database import get_session, SessionDep
from app.chat_gpt.dao import ChatDAO, MessageDAO

router = APIRouter(prefix="/chat_gpt", tags=["ChatGPT"])


# Создать новый чат по tg_id
@router.post("/chats/")
async def create_chat(tg_id: int, title: str, session: AsyncSession = Depends(get_session)):
    new_chat = await ChatDAO.create_chat_by_tg_id(session, tg_id, title)
    if not new_chat:
        raise HTTPException(status_code=404, detail="Пользователь с таким tg_id не найден")
    return {"message": "Чат создан", "chat_id": new_chat.id}


# Получить список чатов по tg_id
@router.get("/chats/{tg_id}", response_model=List[dict])
async def get_chats(tg_id: int, session: AsyncSession = Depends(get_session)):
    chats = await ChatDAO.get_chats_by_tg_id(session, tg_id)
    return [{"id": chat.id, "title": chat.title, "created_at": chat.created_at} for chat in chats]


# Получить все сообщения в чате
@router.get("/messages/{chat_id}", response_model=List[dict])
async def get_messages(chat_id: int, session: AsyncSession = Depends(get_session)):
    messages = await MessageDAO.get_messages_by_chat(session, chat_id)
    return [
        {
            "id": msg.id,
            "is_user": msg.is_user,
            "content": msg.content,
            "created_at": msg.created_at
        }
        for msg in messages
    ]


# Добавить сообщение
@router.post("/messages/")
async def create_message(chat_id: int, content: str, session: AsyncSession = Depends(get_session)):
    try:
        response = await create_response_gpt(session=session, chat_id=chat_id, text=content)
    except Exception as e:
        return f"произошла ошибка {e}"

    await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=content)
    # print(response.text)
    await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=response)
    return {"message": response}


@router.get("/test/")
async def test(session: SessionDep):
    res = await calculate_daily_usage(session)
    return res


