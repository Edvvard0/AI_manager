# app/chat_gpt/router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from starlette.responses import JSONResponse

from app.chat_gpt.schemas import ChatOut, SMessageAdd
from app.chat_gpt.utils.utils import create_response_gpt, client
from app.chat_gpt.utils.utils_docx import process_docx_file
from app.chat_gpt.utils.utils_file import create_file
from app.chat_gpt.utils.utils_token import calculate_daily_usage
from app.config import settings
from app.database import get_session, SessionDep
from app.chat_gpt.dao import ChatDAO, MessageDAO

router = APIRouter(prefix="/chat_gpt", tags=["ChatGPT"])


# Создать новый чат по tg_id
@router.post("/chats/")
async def create_chat(tg_id: int, title: str, session: AsyncSession = Depends(get_session)):
    print("create chat")
    new_chat = await ChatDAO.create_chat_by_tg_id(session, tg_id, title)
    if not new_chat:
        raise HTTPException(status_code=404, detail="Пользователь с таким tg_id не найден")
    return {"message": "Чат создан", "chat_id": new_chat.id}


@router.get("/chats/{tg_id}")
async def get_chats(tg_id: int, session: AsyncSession = Depends(get_session)) -> list[ChatOut]:
    chats = await ChatDAO.get_chats_by_tg_id(session, tg_id)
    return chats


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


@router.post("/messages/")
async def create_message(data: SMessageAdd, session: AsyncSession = Depends(get_session)):
    print("message")
    try:
        response = await create_response_gpt(session=session, chat_id=data.chat_id, text=data.content)
    except Exception as e:
        return f"произошла ошибка {e}"

    await MessageDAO.add(session, chat_id=data.chat_id, is_user=True, content=data.content)
    # print(response.text)
    await MessageDAO.add(session, chat_id=data.chat_id, is_user=False, content=response)
    return {"message": response}


@router.post("/messages_with_add_task/{chat_id}")
async def create_messages_with_add_task(chat_id: int, content: str, session: AsyncSession = Depends(get_session)):
    print("message task")
    try:
        tasks = await create_response_gpt(session=session, chat_id=chat_id, text=content)
    except Exception as e:
        return f"произошла ошибка {e}"

    return tasks

@router.get("/token_info/")
async def token_info(session: SessionDep):
    res = await calculate_daily_usage(session)
    return res


@router.post("/ask")
async def ask_gpt(session: SessionDep, chat_id: int, prompt: str = Form(...), file: UploadFile = File(...)):
    # 1. Загружаем файл в OpenAI
    vector_store= await create_file(file)

    response = await client.responses.create(
        model=settings.CHAT_GPT_MODEL,
        input=prompt,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store.id]
        }]
    )

    await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
    await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=response.output_text)

    return {"answer": response.output_text}
