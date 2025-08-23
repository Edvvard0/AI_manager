from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.project.dao import ProjectDAO
from app.project.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects",
                   tags=["Projects"])


@router.post("/")
async def create_project(data: ProjectCreate, session: SessionDep):
    await ProjectDAO.add(session, **data.model_dump())
    return {"message": "Проект создан"}


@router.get("/", response_model=list[ProjectOut])
async def get_projects(session: SessionDep):
    return await ProjectDAO.find_all(session)


@router.get("/by_tg/{tg_id}", response_model=list[ProjectOut])
async def get_projects_by_tg_id(tg_id: int, session: SessionDep):
    return await ProjectDAO.find_by_tg_id(session, tg_id)


@router.get("/{project_id}/chats")
async def get_project_chats(project_id: int, session: SessionDep):
    chats = await ProjectDAO.get_chats(session, project_id)
    return chats


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, session: SessionDep):
    project = await ProjectDAO.find_one_or_none(session, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate, session: SessionDep):
    project = await ProjectDAO.update(session, {"id": project_id}, **data.model_dump(exclude_unset=True))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Данные о проекте успешно обновлены"}


@router.delete("/{project_id}")
async def delete_project(project_id: int, session: SessionDep):
    success = await ProjectDAO.delete(session, **{"id" : project_id})
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Проект удалён"}


