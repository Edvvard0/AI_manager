from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.users.dao import UserDAO
from app.users.schemas import UserCreate, UserUpdate

router = APIRouter(prefix="/users",
                   tags=["User"])


@router.post("/")
async def create_user(user: UserCreate, session: SessionDep):
    await UserDAO.add(session, **user.model_dump())
    return {"message": f"Пользователь: {user.name} добавлен"}


@router.get("/")
async def get_worker(session: SessionDep):
    worker = await UserDAO.find_all(session, **{"is_admin": False})
    return worker


@router.get("/{user_id}")
async def get_user_by_id(user_id: int, session: SessionDep):
    user = await UserDAO.find_one_or_none(session, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/tg/{tg_id}")
async def get_user_by_tg_id(tg_id: int, session: SessionDep):
    user = await UserDAO.find_one_or_none(session, tg_id=tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}")
async def update_user(user_id: int, user_update: UserUpdate, session: SessionDep):
    await UserDAO.update(session, {"id": user_id}, **user_update.model_dump(exclude_unset=True))
    return {"message": "Данные о пользователе успешно обновлены"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, session: SessionDep):
    user = await UserDAO.find_one_or_none(session, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await UserDAO.delete(session, id=user_id)
    return {"message": "Пользователь удален"}