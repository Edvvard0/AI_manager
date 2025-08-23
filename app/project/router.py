from fastapi import APIRouter

from app.database import SessionDep
from app.project.dao import ProjectDAO
from app.project.schemas import ProjectCreate

router = APIRouter(prefix="/projects",
                   tags=["Projects"])



@router.post("/project")
async def create_project(
    data: ProjectCreate,
    session: SessionDep
):
    await ProjectDAO.add(session, **data.model_dump())
    return {"message" : "Проект создан"}

