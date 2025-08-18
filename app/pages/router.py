from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from app.chat_gpt.router import token_info, create_messages_with_add_task, get_all_chats

from app.chat_gpt.router import get_messages
from app.users.router import get_worker

router = APIRouter(prefix='/pages', tags=['Страницы'])
templates = Jinja2Templates(directory='app/templates')


# @router.get("/", response_class=HTMLResponse)
# async def main_page(request: Request):
#     return templates.TemplateResponse("pages/main_page.html", {
#         "request": request,
#     })


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request, chats = Depends(get_all_chats)):
    return templates.TemplateResponse("pages/main_page.html", {
        "request": request,
        "chats": chats
    })


@router.get("/current_chat/{chat_id}", response_class=HTMLResponse)
async def current_chat_page(request: Request,
                            chat_id: int,  messages = Depends(get_messages),
                            chats = Depends(get_all_chats)
                            ):
    return templates.TemplateResponse("pages/current_chat.html", {
        "request": request,
        "messages": messages,
        "chat_id": chat_id,
        "chats": chats
    })


@router.get("/token_info", response_class=HTMLResponse)
async def token_info(request: Request,
                     token_info = Depends(token_info),
                     chats = Depends(get_all_chats)):
    return templates.TemplateResponse("pages/token_info.html", {
        "request": request,
        "token_info": token_info,
        "chats": chats
    })


@router.get("/add_tasks/{chat_id}", response_class=HTMLResponse)
async def add_tasks_page(request: Request,
                     chat_id: int,
                     executors = Depends(get_worker),
                     tasks = Depends(create_messages_with_add_task)):
    return templates.TemplateResponse("pages/add_tasks.html", {
        "request": request,
        "executors": executors,
        "tasks": tasks,
        "chat_id": chat_id
    })

