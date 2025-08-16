from fastapi import APIRouter

from app.database import SessionDep
from app.users.dao import UserDAO

router = APIRouter(prefix="/users",
                   tags=["User"])


@router.get("/")
async def get_worker(session: SessionDep):
    worker = await UserDAO.find_all(session, **{"is_admin": False})
    return worker