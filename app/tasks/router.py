import os
import uuid
from pathlib import Path
from urllib.parse import quote

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.bot.create_bot import send_task_user
from app.database import get_session, SessionDep
from app.tasks.dao import TaskDAO
from app.tasks.schemas import TaskOut, TaskCreate, TaskUpdate, TaskFilter
from app.tasks.utils import save_uploaded_file
from app.users.dao import UserDAO

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Создание задачи
@router.post("/")
async def create_task(task_data: TaskCreate, session: AsyncSession = Depends(get_session)):
    task = await TaskDAO.create_task(session, task_data)
    await send_task_user(session, task_data)
    return {"message": "задача успешно создана",
            "task_id": task.id}


@router.post("/upload_file/{task_id}")
async def upload_file_for_task(
    session: SessionDep,
    task_id: int,
    file: UploadFile = File(...)
):
    # 1) Проверим, что задача есть
    task = await TaskDAO.find_one_or_none_by_id(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

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

    try:
        file.file.seek(0)  # UploadFile.file — обычный file-like объект
    except Exception:
        pass

    public_base = "https://ai-meneger-edward0076.amvera.io"
    relative_path = f"data_files/chat_files/{unique_filename}"
    download_url = f"{public_base}/chat_gpt/file/{quote(relative_path, safe='')}"

    task.file_path = download_url
    await session.commit()

    return {
        "message": "файл успешно сохранен",
        "file_url": download_url,
    }

# Получить все задачи
@router.get("/")
async def get_all_tasks(session: SessionDep):
    tasks = await TaskDAO.find_all(session)
    return tasks


@router.get("/filters/", response_model=List[TaskOut])
async def get_tasks(
    session: SessionDep,
    filters: TaskFilter = Depends(),

):
    tasks = await TaskDAO.find_by_filters(session, filters)
    return tasks


@router.get("/search/tasks")
async def search_tasks(q: str, tg_id: int, session: SessionDep, limit: int = 20):
    try:
        return await TaskDAO.search(session, term=q, tg_id=tg_id, limit=limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


# Получить задачу по id
@router.get("/{task_id}")
async def get_task_by_id(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await TaskDAO.find_one_or_none_by_id(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Получить все задачи конкретного пользователя
@router.get("/user/{tg_id}")
async def get_tasks_for_user(tg_id: int, session: AsyncSession = Depends(get_session)):
    user = await UserDAO.find_one_or_none(session=session, tg_id=tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_admin:
        return await TaskDAO.find_all(session)

    return await TaskDAO.find_task_by_tg_id(session, **{"tg_id": tg_id })


# Обновление задачи — только руководитель
@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    tg_id: int,
    session: AsyncSession = Depends(get_session),
):
    user = await UserDAO.find_one_or_none(session=session, tg_id=tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update tasks")

    try:
        updated_count = await TaskDAO.update(
            session,
            {"id": task_id},
            **task_data.model_dump(exclude_unset=True),
        )
        if updated_count == 0:
            await session.rollback()
            raise HTTPException(status_code=404, detail="Task not found or no changes made")

        await session.commit()
        return {"status": "success", "updated": updated_count}
    except:
        await session.rollback()
        raise

# Удаление задачи — только руководитель
@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    tg_id: int,
    session: AsyncSession = Depends(get_session),
):
    user = await UserDAO.find_one_or_none(session=session, tg_id=tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete tasks")

    try:
        deleted_count = await TaskDAO.delete(session, id=task_id)
        if deleted_count == 0:
            await session.rollback()
            raise HTTPException(status_code=404, detail="Task not found")

        await session.commit()
        return {"status": "success", "deleted": deleted_count}
    except:
        await session.rollback()
        raise