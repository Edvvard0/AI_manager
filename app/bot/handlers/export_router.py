import os
import tempfile
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import aiofiles
import asyncio

from app.chat_gpt.utils.export_chats import main
from app.database import async_session_maker

# Создаем роутер
export_router = Router()


# Состояния для FSM
class ExportStates(StatesGroup):
    waiting_for_html = State()


async def download_file_with_timeout(bot: Bot, file_path: str, destination: Path, timeout: int = 300):
    """Скачивание файла с увеличенным таймаутом"""
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.get(file_url) as response:
            response.raise_for_status()

            async with aiofiles.open(destination, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                    await f.write(chunk)


@export_router.message(Command("export_chats"))
async def command_export_chats(message: Message, state: FSMContext):
    """Обработчик команды /export_chats"""
    await message.answer("📁 Пришлите мне файл chat.html с экспортом чатов")
    await state.set_state(ExportStates.waiting_for_html)


@export_router.message(ExportStates.waiting_for_html, F.document)
async def handle_html_file(message: Message, state: FSMContext, bot: Bot):
    """Обработка полученного файла chat.html"""
    try:
        # Проверяем, что это HTML файл
        if not message.document.file_name or not message.document.file_name.endswith(('.html', '.htm')):
            await message.answer("❌ Пожалуйста, пришлите HTML файл (chat.html)")
            return

        # Проверяем размер файла
        max_size = 100 * 1024 * 1024  # 100 МБ
        if message.document.file_size > max_size:
            await message.answer("❌ Файл слишком большой. Максимальный размер: 100 МБ")
            return

        # Получаем информацию о файле
        file_id = message.document.file_id
        file = await bot.get_file(file_id)

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Скачиваем файл с увеличенным таймаутом
            await message.answer("⏳ Скачиваю файл...")

            await download_file_with_timeout(
                bot=bot,
                file_path=file.file_path,
                destination=temp_path,
                timeout=300  # 5 минут
            )

            # Проверяем, что файл скачался
            if not temp_path.exists() or temp_path.stat().st_size == 0:
                await message.answer("❌ Не удалось скачать файл")
                return

            # Создаем целевую директорию
            target_dir = Path("data_files/file_export")
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / "chat.html"

            # Копируем файл
            import shutil
            shutil.copy2(temp_path, target_path)

            await message.answer("✅ Файл успешно сохранен. Начинаю обработку...")

            # Запускаем обработку в отдельной таске чтобы не блокировать
            asyncio.create_task(process_chat_file(message, target_path))

        finally:
            # Удаляем временный файл
            if temp_path.exists():
                temp_path.unlink()

    except asyncio.TimeoutError:
        await message.answer("❌ Время скачивания истекло. Попробуйте еще раз.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {str(e)}")
        print(f"Error handling HTML file: {e}")
    finally:
        await state.clear()


async def process_chat_file(message: Message, file_path: Path):
    """Обработка файла в отдельной таске"""
    try:
        async with async_session_maker() as session:
            await main(session=session, file_path=str(file_path))
            await message.answer("✅ Все чаты успешно сохранены в базу данных!")
    except Exception as e:
        error_msg = f"❌ Ошибка при обработке чатов: {str(e)}"
        if len(error_msg) > 4000:  # Ограничение Telegram
            error_msg = error_msg[:4000] + "..."
        await message.answer(error_msg)
        print(f"Error in main: {e}")


@export_router.message(ExportStates.waiting_for_html)
async def handle_wrong_content_type(message: Message, state: FSMContext):
    """Обработка неправильного типа контента"""
    await message.answer("❌ Пожалуйста, пришлите файл chat.html как документ")