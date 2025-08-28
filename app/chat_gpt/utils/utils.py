import json
import re
from datetime import date

from openai import AsyncOpenAI
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.chat_gpt.dao import  MessageDAO
from app.chat_gpt.utils.promts import SYSTEM_PROMPT, SYSTEM_MD

from app.config import settings
from app.database import SessionDep
from app.tasks.dao import TaskDAO
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate
from app.users.dao import UserDAO

client = AsyncOpenAI(api_key=settings.CHAT_GPT_API_KEY)


async def get_minutes_tasks(session: SessionDep):
    today = date.today()

    query = (
        select(Task)
        .where(
            and_(
                Task.tag == "пятиминутка",
                Task.deadline_date <= today,
                Task.status != "готово"
            )
        )
        .order_by(Task.deadline_date.asc())
    )

    result = await session.execute(query)
    tasks = result.scalars().all()

    # print(tasks)
    if not tasks:
        return "Задач с тегом 'пятиминутка' не найдено."

    summary = "\n".join(
        f"📝 {t.title} — {t.status}\n"
        f"📄 Описание: {t.description}\n"
        f"📅 Дедлайн: {t.deadline_date}\n"
        f"👤 Исполнитель: {t.executor.name if t.executor else '—'} "
        f"(@{t.executor.username if t.executor and t.executor.username else '—'})\n"
        for t in tasks
    )

    return f"📌 Список задач с тегом 'пятиминутка':\n\n{summary}"


def check_keywords(text: str):
    if "РАСПРЕДЕЛИ ЗАДАЧИ" in text:
        return "distribute"
    elif "СТАТУС ПО ЗАДАЧАМ" in text:
        return "status"
    elif "СТАТУС ПО ВСЕМ ЗАДАЧАМ" in text:
        return "status_all"
    elif "НАЧАЛО ПЯТИМИНУТКИ" in text:
        return "minutes_start"
    else:
        return None


async def get_last_messages(session: SessionDep, chat_id: int):
    messages = await MessageDAO.get_history(session, chat_id)
    return  messages


async def get_worker_info(session: SessionDep):
    workers = await UserDAO.find_all(session, **{"is_admin": False})
    summary = "\n".join(f"Имя {w.name}, Отдел {w.department},  Username: {w.username}" for w in workers)
    # print(summary)
    return f"Список сотрудников:\n{summary}"


async def get_tasks_info(session: SessionDep, chat_id: int = 0):
    if chat_id:
        tasks = await session.execute(
            select(Task).options(joinedload(Task.executor))
            .where(Task.chat_id == chat_id)
        )
        tasks = tasks.scalars().all()
    else:
        tasks = await session.execute(
            select(Task).options(joinedload(Task.executor))
        )
        tasks = tasks.scalars().all()

    summary = "\n".join(
        f"{t.title} — {t.status} | \n"
        f"Описание: {t.description} \n "
        f"Дедлайн: {t.deadline_date} \n"
        f"Исполнитель: {t.executor.name if t.executor else '—'} \n"
        f"({t.executor.username if t.executor and t.executor.username else '—'})\n"
        for t in tasks
    )

    return f"Информация по задачам проанализируй и подробно расскажи про каждую задачу:\n{summary}"


async def create_response_gpt(session: SessionDep, text: str, chat_id: int):
    messages = await get_last_messages(session, chat_id)
    instructions = ""

    gpt_input = []
    action = check_keywords(text)

    if action == "distribute":
        gpt_input = [{"role": "system", "content": SYSTEM_PROMPT}]
        instructions = SYSTEM_PROMPT

        worker_info = await get_worker_info(session)
        gpt_input.append({"role": "user", "content": worker_info})

    elif action == "minutes_start":
        minutes_tasks = await get_minutes_tasks(session)
        gpt_input.append({"role": "user", "content": minutes_tasks})

    elif action == "status":
        task_info = await get_tasks_info(session, chat_id)
        worker_info = await get_worker_info(session)

        gpt_input.append({"role": "user", "content": task_info})
        gpt_input.append({"role": "user", "content": worker_info})


    elif action == "status_all":
        task_info = await get_tasks_info(session)
        worker_info = await get_worker_info(session)

        gpt_input.append({"role": "user", "content": task_info})
        gpt_input.append({"role": "user", "content": worker_info})

    for msg in messages:
        gpt_input.append({
            "role": "user" if msg.is_user else "assistant",
            "content": msg.content
        })

    gpt_input.append({"role": "user", "content": text})
    gpt_input.append( {"role": "system", "content": SYSTEM_MD})

    response = await client.responses.create(
        model=settings.CHAT_GPT_MODEL,
        input=gpt_input,
        instructions=instructions
    )

    if action == "distribute":
        try:
            output = re.sub(r'}\s*{', '},{', response.output_text.strip())
            output = f"[{output}]"

            tasks_data = json.loads(output)  # список словарей
            tasks = [TaskCreate.model_validate(t) for t in tasks_data]

            return tasks

        except Exception as e:
            print(f"[ERROR PARSING TASK] {e}")
            print(f"GPT output was:\n{response}")

            return  response.output_text
    return response.output_text
