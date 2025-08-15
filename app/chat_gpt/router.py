# app/chat_gpt/router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from starlette.responses import JSONResponse

from app.chat_gpt.utils.utils import create_response_gpt
from app.chat_gpt.utils.utils_docx import process_docx_file
from app.chat_gpt.utils.utils_token import calculate_daily_usage
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


@router.get("/token_info/")
async def token_info(session: SessionDep):
    res = await calculate_daily_usage(session)
    return res



@router.post("/process-docx/")
async def process_docx_file_and_prompt(
        session: SessionDep,
        chat_id: int,
        prompt: str = Form(...),
        file: UploadFile = File(...)
):
    try:
        # Проверяем расширение файла
        if not file.filename.lower().endswith('.docx'):
            raise HTTPException(status_code=400, detail="Поддерживаются только .docx файлы")

        file_content = await process_docx_file(file)
        prompt = prompt + f"Содержимое файла {file_content}"
        response = await create_response_gpt(text=prompt, chat_id=chat_id, session=session)

        await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
        await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=response)

        return JSONResponse(content={
            "response": response,
        })
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

