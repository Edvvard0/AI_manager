import openai
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from starlette.responses import JSONResponse

from app.chat_gpt.schemas import ChatOut, SMessageAdd, PromptResponse, AnswerResponse
from app.chat_gpt.utils.utils import create_response_gpt
from app.chat_gpt.utils.utils_file import process_file
from app.chat_gpt.utils.utils_token import calculate_daily_usage
from app.config import settings
from app.database import get_session, SessionDep
from app.chat_gpt.dao import ChatDAO, MessageDAO

router = APIRouter(prefix="/chat_gpt", tags=["ChatGPT"])


@router.get("/chats/all")
async def get_all_chats(session: AsyncSession = Depends(get_session)):
    chats = await ChatDAO.find_all(session)
    chats_list = [{"id": c.id, "title": c.title, "user_id": c.user_id} for c in chats]

    return JSONResponse(
        status_code=200,
        content=chats_list,
        media_type="application/json; charset=utf-8"
    )


# Создать новый чат по tg_id
@router.post("/chats/")
async def create_chat(tg_id: int, title: str, session: AsyncSession = Depends(get_session)):
    print("create chat")
    new_chat = await ChatDAO.create_chat_by_tg_id(session, tg_id, title)
    if not new_chat:
        raise HTTPException(status_code=404, detail="Пользователь с таким tg_id не найден")
    return JSONResponse(
        status_code=200,
        content={"message": "Чат создан", "chat_id": new_chat.id},
        media_type="application/json; charset=utf-8"
    )

@router.get("/chats/{tg_id}")
async def get_chats(tg_id: int, session: AsyncSession = Depends(get_session)):
    chats = await ChatDAO.get_chats_by_tg_id(session, tg_id)
    chats_list = [{"id": c.id, "title": c.title, "user_id": c.user_id} for c in chats]

    return JSONResponse(
        status_code=200,
        content=chats_list,
        media_type="application/json; charset=utf-8"
    )


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


# @router.post("/ask")
# async def ask_gpt(session: SessionDep, chat_id: int, prompt: str = Form(...), file: UploadFile = File(...)):
#     # 1. Загружаем файл в OpenAI
#     print("file")
#     vector_store= await create_file(file)
#
#     response = await client.responses.create(
#         model=settings.CHAT_GPT_MODEL,
#         input=prompt,
#         tools=[{
#             "type": "file_search",
#             "vector_store_ids": [vector_store.id]
#         }]
#     )
#
#     await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
#     await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=response.output_text)
#
#     return {"answer": response.output_text}


@router.post("/ask", response_model=AnswerResponse)
async def chatgpt_endpoint(session: SessionDep, chat_id: int, file: UploadFile = File(...), prompt: str = Form(...)):
    try:
        # Чтение содержимого файла
        file_content = await file.read()
        content_type = file.content_type
        filename = file.filename

        # Обработка файла и формирование сообщений
        messages = await process_file(file_content, content_type, filename, prompt)

        # Запрос к OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000
        )

        # Получаем ответ от ChatGPT
        chatgpt_response = response.choices[0].message.content

        # Сохранение сообщений в БД
        await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
        await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=chatgpt_response)

        # Возврат в формате {"answer": "текст"}
        return {"answer": chatgpt_response}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )