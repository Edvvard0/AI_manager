from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from app.bot.create_bot import send_task_user
from app.database import get_session, SessionDep
from app.tasks.dao import TaskDAO
from app.tasks.schemas import TaskOut, TaskCreate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Создание задачи
@router.post("/")
async def create_task(task_data: TaskCreate, session: AsyncSession = Depends(get_session)):
    await TaskDAO.add(session, **task_data.dict())
    await send_task_user(session, task_data)
    return {"message": "задача успешно создана"}


# Получить все задачи
@router.get("/", response_model=List[TaskOut | None])
async def get_all_tasks(session: SessionDep):
    tasks = await TaskDAO.find_all(session)
    return tasks


# Получить задачу по id
@router.get("/{task_id}", response_model=TaskOut)
async def get_task_by_id(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await TaskDAO.find_one_or_none_by_id(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Получить все задачи конкретного пользователя
@router.get("/user/{user_id}", response_model=List[TaskOut])
async def get_tasks_for_user(user_id: int, session: AsyncSession = Depends(get_session)):
    tasks = await TaskDAO.find_all_by_user_id(session, user_id)
    return tasks


# Обновление задачи
@router.patch("/{task_id}")
async def update_task(task_id: int, task_data: TaskUpdate, session: AsyncSession = Depends(get_session)):
    updated_count = await TaskDAO.update(session, {"id": task_id}, **task_data.dict(exclude_unset=True))
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Task not found or no changes made")
    return {"status": "success", "updated": updated_count}


# Удаление задачи
@router.delete("/{task_id}")
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    deleted_count = await TaskDAO.delete(session, id=task_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "deleted": deleted_count}