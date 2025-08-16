from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from app.chat_gpt.router import token_info

from app.chat_gpt.router import get_messages

router = APIRouter(prefix='/pages', tags=['Страницы'])
templates = Jinja2Templates(directory='app/templates')


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("base.html", {
        "request": request,
        # "chats": chats
    })


@router.get("/current_chat/{chat_id}", response_class=HTMLResponse)
async def current_chat_page(request: Request, chat_id: int,  messages = Depends(get_messages)):
    return templates.TemplateResponse("pages/current_chat.html", {
        "request": request,
        "messages": messages,
        "chat_id": chat_id
    })


@router.get("/token_info", response_class=HTMLResponse)
async def token_info(request: Request, token_info = Depends(token_info)):
    return templates.TemplateResponse("pages/token_info.html", {
        "request": request,
        "token_info": token_info
    })
