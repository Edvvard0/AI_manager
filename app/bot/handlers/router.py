from email.policy import default

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.bot.create_bot import send_task_admin
from app.users.dao import UserDAO
from app.tasks.dao import TaskDAO
from app.bot.keyboards.kbs import main_keyboard, new_status_keyboard, change_keyboard
from app.database import connection, SessionDep, async_session_maker
from app.users.models import User

router = Router()


@router.message(CommandStart())
@connection()
async def cmd_start(message: Message, session, **kwargs):
    welcome_text = (
        "Вас приветствует нейробот, помогающий распределять задачи между сотрудниками"
    )

    user_id = message.from_user.id
    user_info = await UserDAO.find_one_or_none(session=session, tg_id=user_id)

    if not user_info:
        await message.answer("Извините, но вы не зарегистрированы в системе")
        return

    await message.answer(welcome_text, reply_markup=main_keyboard())


@router.callback_query(F.data == "my_tasks")
@connection()
async def get_user_tasks(call: CallbackQuery, session, **kwargs):
    user_id = call.from_user.id
    user = await UserDAO.find_one_or_none(session=session, tg_id=user_id)

    if not user:
        await call.message.answer("Вы не зарегистрированы в системе")
        return

    tasks = await TaskDAO.find_all_by_user_id(session, user.id)

    if not tasks:
        await call.message.answer("У вас нет задач.")
        return

    for task in tasks:
        text = (
            f"<b>{task.title}</b>\n"
            f"{task.description}\n"
            f"Дедлайн: {task.deadline_date}\n"
            f"Статус: {task.status}"
        )
        await call.message.answer(
            text,
            reply_markup=change_keyboard(task.id)
        )


@router.callback_query(F.data.startswith("change_status:"))
async def change_status_handler(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await call.message.answer(
        "Выберите новый статус задачи:",
        reply_markup=new_status_keyboard(task_id)
    )


@router.callback_query(F.data.startswith("status:"))
@connection()
async def set_new_status(call: CallbackQuery, session, **kwargs):
    _, task_id, new_status = call.data.split(":")
    task_id = int(task_id)

    updated = await TaskDAO.update(session, {"id": task_id}, status=new_status)
    new_task = await TaskDAO.find_one_or_none_by_id(session, task_id)

    if new_status == "Готово":
        await send_task_admin(session, new_task)

    if updated:
        await call.message.answer(f"✅ Статус задачи обновлён на: <b>{new_status}</b>")
    else:
        await call.message.answer("❌ Не удалось обновить статус задачи.")


@router.callback_query(F.data.startswith("back_to_task:"))
@connection()
async def back_to_task(call: CallbackQuery, session, **kwargs):
    task_id = int(call.data.split(":")[1])
    task = await TaskDAO.find_one_or_none_by_id(session, task_id)

    if not task:
        await call.message.answer("Задача не найдена.")
        return

    text = (
        f"<b>{task.title}</b>\n"
        f"{task.description}\n"
        f"Дедлайн: {task.deadline_date}\n"
        f"Статус: {task.status}"
    )
    await call.message.answer(
        text,
        reply_markup=change_keyboard(task.id)
    )


class Registration(StatesGroup):
    name = State()
    department = State()


@router.message(F.text == "/register")
async def start_registration(message: Message, state: FSMContext):
    async with async_session_maker() as session:

        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        if result.scalar():
            await message.answer("Вы уже зарегистрированы ✅")
            return

    await state.set_state(Registration.name)
    await message.answer("Введите ваше ФИО:")


@router.message(Registration.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Registration.department)
    await message.answer("Введите ваш департамент:")


@router.message(Registration.department)
async def process_department(message: Message, state: FSMContext):
    data = await state.get_data()

    async with async_session_maker() as session:
        user = User(
            name=data["name"],
            username="@" + str(message.from_user.username),  # Telegram username
            tg_id=message.from_user.id,           # Telegram ID
            department=message.text,
            is_admin=False
        )
        session.add(user)
        await session.commit()

    await message.answer("✅ Вы успешно зарегистрированы!")
    await state.clear()