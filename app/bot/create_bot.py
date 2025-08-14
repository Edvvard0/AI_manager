from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings

from app.database import SessionDep
from app.tasks.schemas import TaskCreate
from app.users.dao import UserDAO

bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def start_bot():
    try:
        for admin_id in settings.ADMIN_IDS:
            await bot.send_message(admin_id, f'Я запущен🥳.')
    except:
        pass


async def stop_bot():
    try:
        for admin_id in settings.ADMIN_IDS:
            await bot.send_message(admin_id, 'Бот остановлен.')
    except:
        pass


async def send_task_user(session: SessionDep, new_task: TaskCreate):
    # print("Send message")
    user = await UserDAO.find_one_or_none(session, **{"id": new_task.executor_id})
    tg_id = user.tg_id

    try:
        await bot.send_message(
            chat_id=tg_id,
            text=(
                f"📌 <b>Новая задача</b>\n\n"
                f"<b>Название:</b> {new_task.title}\n"
                f"<b>Описание:</b> {new_task.description}\n"
                f"<b>Дедлайн:</b> {new_task.deadline_date}\n"
                f"<b>Статус:</b> {new_task.status}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")


async def send_task_admin(session: SessionDep, new_task: TaskCreate):

    admin = await UserDAO.find_one_or_none(session, **{"is_admin": True})
    executor = await UserDAO.find_one_or_none(session, **{"id": new_task.executor_id})
    tg_id = admin.tg_id

    try:
        await bot.send_message(
            chat_id=tg_id,
            text=(
                f"📌 <b>Задача выполнена</b>\n\n"
                f"<b>Исполнитель:</b> {executor.name}\n"
                f"<b>Название:</b> {new_task.title}\n"
                f"<b>Описание:</b> {new_task.description}\n"
                f"<b>Дедлайн:</b> {new_task.deadline_date}\n"
                f"<b>Статус:</b> {new_task.status}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")
