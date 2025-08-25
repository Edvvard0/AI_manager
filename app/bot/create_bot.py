from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest

from app.bot.keyboards.kbs import persistent_main_keyboard
from app.config import settings

from app.database import SessionDep
from app.tasks.schemas import TaskCreate
from app.users.dao import UserDAO

bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# БАЗОВАЯ ДИРЕКТОРИЯ, где лежат файлы задач (можешь вынести в settings)
FILES_BASE_DIR = "data_files"

async def start_bot():
    try:
        for admin_id in settings.ADMIN_IDS:
            await bot.send_message(admin_id, 'Я запущен🥳.')
    except:
        pass

async def stop_bot():
    try:
        for admin_id in settings.ADMIN_IDS:
            await bot.send_message(admin_id, 'Бот остановлен.')
    except:
        pass


def _build_task_text(task: TaskCreate) -> str:
    return (
        f"📌 <b>Новая задача</b>\n\n"
        f"<b>Название:</b> {task.title}\n"
        f"<b>Описание:</b> {task.description}\n"
        f"<b>Дедлайн:</b> {task.deadline_date}\n"
        f"<b>Статус:</b> {task.status}"
        + (f"\n<b>Комментарий:</b> {task.comment}" if getattr(task, 'comment', None) else "")
    )


async def send_task_user(session: SessionDep, new_task: TaskCreate):
    user = await UserDAO.find_one_or_none(session, **{"id": new_task.executor_id})
    if not user or not user.tg_id:
        print("Ошибка: не найден tg_id исполнителя")
        return

    tg_id = user.tg_id
    text = _build_task_text(new_task)
    reply_kb = persistent_main_keyboard()

    file_path_rel = getattr(new_task, "file_path", None)
    if not file_path_rel:
        try:
            await bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_kb)
        except Exception as e:
            print(f"Ошибка при отправке уведомления: {e}")
        return

    abs_path = (FILES_BASE_DIR / file_path_rel).resolve()

    # Безопасность: файл должен лежать внутри FILES_BASE_DIR
    try:
        abs_path.relative_to(FILES_BASE_DIR)
    except ValueError:
        print(f"Небезопасный путь к файлу: {abs_path}")
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_kb)
        return

    if not abs_path.exists():
        print(f"Файл не найден: {abs_path}")
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_kb)
        return

    try:
        doc = FSInputFile(str(abs_path))

        caption = text if len(text) <= 1024 else ""
        await bot.send_document(
            chat_id=tg_id,
            document=doc,
            caption=caption,
            reply_markup=reply_kb
        )

        if not caption:
            await bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_kb)
    except TelegramBadRequest as e:
        print(f"TelegramBadRequest при отправке документа: {e}")
        await bot.send_document(chat_id=tg_id, document=doc, reply_markup=reply_kb)
        await bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_kb)
    except Exception as e:
        print(f"Ошибка при отправке документа: {e}")

        await bot.send_message(chat_id=tg_id, text=text, reply_markup=reply_kb)

async def send_task_admin(session: SessionDep, new_task: TaskCreate):
    admin = await UserDAO.find_one_or_none(session, **{"is_admin": True})
    executor = await UserDAO.find_one_or_none(session, **{"id": new_task.executor_id})
    if not admin or not admin.tg_id:
        return
    tg_id = admin.tg_id

    try:
        await bot.send_message(
            chat_id=tg_id,
            text=(
                f"📌 <b>Задача выполнена</b>\n\n"
                f"<b>Исполнитель:</b> {executor.name if executor else '-'}\n"
                f"<b>Название:</b> {new_task.title}\n"
                f"<b>Описание:</b> {new_task.description}\n"
                f"<b>Дедлайн:</b> {new_task.deadline_date}\n"
                f"<b>Статус:</b> {new_task.status}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")