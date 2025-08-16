from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Мои задачи", callback_data="my_tasks")
    kb.adjust(1)
    return kb.as_markup()


def change_keyboard(task_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="🔄 Обновить статус задачи",
        callback_data=f"change_status:{task_id}"
    )
    kb.button(
        text="✏️ Добавить комментарий",
        callback_data=f"add_comment:{task_id}"
    )
    kb.adjust(1)
    return kb.as_markup()


def new_status_keyboard(task_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Начал", callback_data=f"status:{task_id}:Начал")
    kb.button(text="В процессе", callback_data=f"status:{task_id}:В процессе")
    kb.button(text="На проверке", callback_data=f"status:{task_id}:На проверке")
    kb.button(text="Готово", callback_data=f"status:{task_id}:Готово")
    kb.button(text="⬅ Назад", callback_data=f"back_to_task:{task_id}")
    kb.adjust(1)
    return kb.as_markup()


def persistent_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📈 Мои задачи")]
        ],
        resize_keyboard=True
    )
