import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from aiogram.types import Update
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from app.bot.create_bot import bot, dp, stop_bot
from app.bot.handlers.router import router as bot_router
from app.tasks.router import router as task_router
from app.chat_gpt.router import router as gpt_router
from app.pages.router import router as pages_router
from app.users.router import router as user_router
from app.project.router import router as project_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Starting bot setup...")
    dp.include_router(bot_router)

    # Запускаем polling в отдельной асинхронной задаче
    asyncio.create_task(dp.start_polling(bot))

    yield  # Дальше запускается сам FastAPI сервер

    logging.info("Shutting down bot...")
    await stop_bot()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем статику
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Роутеры
app.include_router(task_router)
app.include_router(gpt_router)
app.include_router(user_router)
app.include_router(project_router)

app.include_router(pages_router)


@app.post("/webhook")
async def webhook(request: Request) -> None:
    logging.info("Received webhook request")
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    logging.info("Update processed")

#ngrok http --url bursting-smart-eagle.ngrok-free.app 8080

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)