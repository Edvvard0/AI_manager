import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import quote

import aiofiles
import openai
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File, Body
from multipart import file_path
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from starlette.responses import JSONResponse, FileResponse

from app.bot.create_bot import send_protocol_group
from app.chat_gpt.schemas import ChatOut, SMessageAdd, AnswerResponse, ChatMessageSearchOut, SFirstMessage, \
    MinutesResponse
from app.chat_gpt.utils.export_chats import main
from app.chat_gpt.utils.promts import SYSTEM_MD
from app.chat_gpt.utils.five_minuts import _is_minutes_analysis, transcribe_audio, generate_protocol_from_transcript, _clip
from app.chat_gpt.utils.utils import create_response_gpt, client, extract_json_array, check_keywords
from app.chat_gpt.utils.utils_file import process_file
from app.chat_gpt.utils.utils_message import first_message
from app.chat_gpt.utils.utils_token import calculate_daily_usage
from app.config import settings
from app.database import get_session, SessionDep
from app.chat_gpt.dao import ChatDAO, MessageDAO, SearchDAO

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


@router.post("/chats/")
async def create_chat(
    tg_id: int,
    title: str,
    project_id: int | None = None,
    session: AsyncSession = Depends(get_session)
):
    # print("create chat")
    new_chat = await ChatDAO.create_chat_by_tg_id(session, tg_id, title, project_id)
    if not new_chat:
        raise HTTPException(status_code=404, detail="Пользователь с таким tg_id не найден")

    return JSONResponse(
        status_code=200,
        content={"message": "Чат создан", "chat_id": new_chat.id, "project_id": new_chat.project_id},
        media_type="application/json; charset=utf-8"
    )


@router.get("/chats/{tg_id}")
async def get_chats(tg_id: int, session: AsyncSession = Depends(get_session)):
    chats = await ChatDAO.get_chats_by_tg_id(session, tg_id)
    chats_list = [{"id": c.id, "title": c.title, "user_id": c.user_id, "project_id": c.project_id} for c in chats]

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
            "created_at": msg.created_at,
            "file_path": msg.file_path
        }
        for msg in messages
    ]

#-------------------

@router.post("/first_messages/")
async def create_message(data: SFirstMessage, session: SessionDep):
    # print("first message")
    try:
        response = await client.responses.create(
            model=settings.CHAT_GPT_MODEL,
            input=data.content,
            instructions="сперва придумай короткое название названия этому чату напиши его и после ***, чтобы я понимал где оно заканчивается"
        )
        # print(response.output_text)
        text = response.output_text
        text = text.replace("Название чата: ", "")

        title = text[:text.find("***")]
        text = text.replace("***", "")
        text = text.replace(f"{title}", "")

        chat = await ChatDAO.create_chat_by_tg_id(session, title=title, tg_id=data.tg_id, project_id=data.project_id)

        await MessageDAO.add(session, chat_id=chat.id, is_user=True, content=data.content)
        await MessageDAO.add(session, chat_id=chat.id, is_user=False, content=text)

        return {"message": text,
                "chat_id": chat.id,
                "chat_name": title}

    except Exception as e:
        return {"error": f"произошла ошибка: {e}"}



#-------------------
@router.post("/messages/")
async def create_message(data: SMessageAdd, session: AsyncSession = Depends(get_session)):
    print("message")
    try:
        response = await create_response_gpt(session=session, chat_id=data.chat_id, text=data.content)

        if "РАСПРЕДЕЛИ ЗАДАЧИ" in data.content:
            return response

        text = response if isinstance(response, str) else response.get("message") or str(response)

        await MessageDAO.add(session, chat_id=data.chat_id, is_user=True, content=data.content)
        await MessageDAO.add(session, chat_id=data.chat_id, is_user=False, content=text)

        return {"message": text}

    except Exception as e:
        return {"error": f"произошла ошибка: {e}"}


#-------------------
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


#-------------------
@router.post("/ask", response_model=AnswerResponse)
async def chatgpt_endpoint(session: SessionDep, chat_id: int, file: UploadFile = File(...), prompt: str = Form(...)):
    try:
        file_content = await file.read()
        content_type = file.content_type
        filename = file.filename

        messages = await process_file(file_content, content_type, filename, prompt)

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000
        )

        chatgpt_response = response.choices[0].message.content

        await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
        await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=chatgpt_response)

        print(chatgpt_response)
        return {"answer": chatgpt_response}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )


def _serialize_message(msg) -> dict:
    """Безопасная сериализация созданного сообщения."""
    # поддержка как ORM-объекта, так и pydantic-модели/словаря
    if isinstance(msg, dict):
        return {
            "id":            msg.get("id"),
            "is_user":       msg.get("is_user"),
            "content":       msg.get("content"),
            "created_at":    msg.get("created_at"),
            "file_path":     msg.get("file_path"),
        }
    return {
        "id":            getattr(msg, "id", None),
        "is_user":       getattr(msg, "is_user", None),
        "content":       getattr(msg, "content", None),
        "created_at":    getattr(msg, "created_at", None),
        "file_path":     getattr(msg, "file_path", None),
    }


@router.post("/message_all")
async def chatgpt_endpoint(
    session: SessionDep,
    chat_id: int | None = Body(None),
    prompt: str = Body(...),
    project_id: int | None = Body(None),
    tg_id: int = Body(...),
    file: UploadFile | None = File(None)
):
    try:
        mode = check_keywords(prompt)

        # --- ВСЕГДА ОБРАБАТЫВАЕМ РАСПРЕДЕЛЕНИЕ ОТДЕЛЬНО ---
        if mode == "distribute":
            # если чата нет — сначала создаём его, НО не возвращаем первый ответ
            if not chat_id:
                if project_id:
                    first = await first_message(prompt=prompt, project_id=project_id, tg_id=tg_id, session=session)
                else:
                    first = await first_message(prompt=prompt, tg_id=tg_id, session=session)
                chat_id = first["chat_id"]

            # выполняем распределение (project_id может быть None → все задачи)
            result = await create_response_gpt(session=session, text=prompt, chat_id=chat_id, project_id=project_id)

            # результат должен быть JSON-массивом
            if isinstance(result, list):
                return result
            if isinstance(result, str):
                arr = extract_json_array(result)
                if arr is not None:
                    return arr
                raise HTTPException(status_code=422, detail="Модель вернула невалидный JSON для распределения задач.")
            # на всякий случай
            raise HTTPException(status_code=422, detail="Ожидался JSON-массив задач.")

        # --- ОСТАЛЬНЫЕ СЛУЧАИ (как раньше) ---
        if not chat_id:
            if project_id:
                response = await first_message(prompt=prompt, project_id=project_id, tg_id=tg_id, session=session)
            else:
                response = await first_message(prompt=prompt, tg_id=tg_id, session=session)

            chat_id = response["chat_id"]

            if not file:
                await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
                assistant_msg = await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=response["message"])
                await session.commit()

                assistant_msg["chat_id"] = chat_id
                return {"message": assistant_msg}

        if not file:
            response = await create_response_gpt(session=session, chat_id=chat_id, text=prompt, project_id=project_id)

            # обычная переписка → сохраняем
            msg_text = response if isinstance(response, str) else (response.get("message") if isinstance(response, dict) else str(response))
            await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt)
            assistant_msg = await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=msg_text)
            await session.commit()

            assistant_msg["chat_id"] = chat_id
            return {"message": assistant_msg}


        elif file:
            file_bytes = await file.read()

            if not file_bytes:
                raise HTTPException(status_code=400, detail="Файл пуст или не был передан.")
            directory = "data_files/chat_files"
            os.makedirs(directory, exist_ok=True)
            orig_name = file.filename or "upload.bin"

            suffix = Path(orig_name).suffix  # сохраним расширение, если есть

            unique_filename = f"{uuid.uuid4().hex}{suffix}"
            file_path = os.path.join(directory, unique_filename)
            async with aiofiles.open(file_path, "wb") as out:
                await out.write(file_bytes)

            content_type = file.content_type or "application/octet-stream"

            filename = orig_name

            try:
                file.file.seek(0)  # UploadFile.file — обычный file-like объект
            except Exception:
                pass

            if _is_minutes_analysis(prompt):
                transcript = await transcribe_audio(file)

                if not transcript.strip():
                    raise HTTPException(status_code=422, detail="Расшифровка пуста. Проверьте качество аудио.")

                protocol = await generate_protocol_from_transcript(transcript)

                await send_protocol_group(protocol)

                return JSONResponse(

                    status_code=200,

                    content=MinutesResponse(protocol=protocol).model_dump()

                )

            messages = await process_file(file_bytes, content_type, filename, prompt)

            messages.append({"role": "system", "content": SYSTEM_MD})

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000
            )

            public_base = "https://ai-meneger-edward0076.amvera.io"  # например, https://ai-meneger-edward0076.amvera.io
            relative_path = f"data_files/chat_files/{unique_filename}"
            download_url = f"{public_base}/chat_gpt/file/{quote(relative_path, safe='')}"

            model_text = response.choices[0].message.content
            await MessageDAO.add(session, chat_id=chat_id, is_user=True, content=prompt, file_path=download_url)

            assistant_msg = await MessageDAO.add(session, chat_id=chat_id, is_user=False, content=model_text,
                                                 file_path=None)

            await session.commit()

            assistant_msg["chat_id"] = chat_id
            assistant_msg["file_path"] = download_url

            return {"message": assistant_msg}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )


@router.post("/analyze", response_model=MinutesResponse)
async def analyze_minutes(
    prompt: str = Form(..., description="Должно содержать ключевую команду АНАЛИЗ ПЯТИМИНУТКИ"),
    file: UploadFile = File(..., description="Аудиофайл совещания (.mp3/.wav/.m4a/.ogg)")
):
    """
    Отдельный эндпоинт: принимает аудио + команду 'АНАЛИЗ ПЯТИМИНУТКИ', возвращает протокол по жёсткому шаблону.
    """
    if not _is_minutes_analysis(prompt):
        raise HTTPException(status_code=400, detail="В prompt должна быть команда 'АНАЛИЗ ПЯТИМИНУТКИ'.")

    transcript = await transcribe_audio(file)
    if not transcript.strip():
        raise HTTPException(status_code=422, detail="Расшифровка пуста. Проверьте качество аудио.")

    protocol = await generate_protocol_from_transcript(transcript)

    return JSONResponse(
        status_code=200,
        content=MinutesResponse(
            protocol=protocol
        ).model_dump()
    )

@router.get("/search", response_model=list[ChatMessageSearchOut])
async def search_chats_and_messages(
    q: str,
    session: SessionDep,
):
    results = await SearchDAO.search_chats_and_messages(session, q)
    return results


@router.get("/file/{file_path:path}")
async def get_file(file_path: str):
    """
    Возвращает файл по указанному пути
    """
    try:
        # Создаем объект Path для безопасной работы с путями
        file_location = Path(file_path)

        # Проверяем, что файл существует
        if not file_location.exists():
            raise HTTPException(status_code=404, detail="Файл не найден")

        # Проверяем, что это файл, а не директория
        if not file_location.is_file():
            raise HTTPException(status_code=400, detail="Указанный путь ведет к директории, а не к файлу")

        # Возвращаем файл с правильным content-type
        return FileResponse(
            path=file_location,
            filename=file_location.name,
            media_type="application/octet-stream"
        )

    except PermissionError:
        raise HTTPException(status_code=403, detail="Нет доступа к файлу")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении файла: {str(e)}")


@router.delete("/{chat_id}")
async def delete_task(chat_id: int, session: AsyncSession = Depends(get_session)):
    deleted_count = await ChatDAO.delete(session, id=chat_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "deleted": deleted_count}