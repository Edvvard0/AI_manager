from fastapi import APIRouter, HTTPException

from app.database import SessionDep
from app.project.dao import ProjectDAO
from app.project.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects",
                   tags=["Projects"])


@router.post("/")
async def create_project(data: ProjectCreate, session: SessionDep):
    """
    Создать проект по tg_id: ищем пользователя с таким tg_id и привязываем проект к нему.
    Возвращаем сам созданный проект (все поля).
    """
    project = await ProjectDAO.create_by_tg_id(
        session=session,
        title=data.title,
        tg_id=data.tg_id,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="User with this tg_id not found")

    project = {
        "id": project.id,
        "title": project.title,
        "tg_id": data.tg_id
    }
    await session.commit()

    return project


@router.get("/", response_model=list[ProjectOut])
async def get_projects(session: SessionDep):
    return await ProjectDAO.find_all(session)


@router.get("/by_tg/{tg_id}", response_model=list[ProjectOut])
async def get_projects_by_tg_id(tg_id: int, session: SessionDep):
    try:
        return await ProjectDAO.find_by_tg_id(session, tg_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/{project_id}/chats")
async def get_project_chats(project_id: int, session: SessionDep):
    try:
        chats = await ProjectDAO.get_chats(session, project_id)
        if not chats:
            raise HTTPException(status_code=404, detail="Chats not found")
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, session: SessionDep):
    try:
        project = await ProjectDAO.find_one_or_none(session, id=project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.patch("/{project_id}")
async def update_project(project_id: int, data: ProjectUpdate, session: SessionDep):
    try:
        project = await ProjectDAO.update(session, {"id": project_id}, **data.model_dump(exclude_unset=True))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        await session.commit()
        return {"message": "Данные о проекте успешно обновлены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: int, session: SessionDep):
    try:
        success = await ProjectDAO.delete(session, **{"id": project_id})
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        await session.commit()
        return {"message": f"Проект удалён c id {project_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


