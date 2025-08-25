from aiogram.types import FSInputFile

from app.bot.create_bot import bot


async def send_file(chat_id: int, file_path: str, caption: str = None):
    file = FSInputFile(file_path)
    await bot.send_document(chat_id, document=file, caption=caption)