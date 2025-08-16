from aiogram.types import FSInputFile

from app.bot.create_bot import bot


async def send_file(chat_id: int, file_path: str, caption: str = None):
    """
    Отправляет файл любого типа пользователю.

    :param chat_id: ID чата или пользователя
    :param file_path: путь к файлу
    :param caption: подпись к файлу (опционально)
    """
    file = FSInputFile(file_path)
    await bot.send_document(chat_id, document=file, caption=caption)