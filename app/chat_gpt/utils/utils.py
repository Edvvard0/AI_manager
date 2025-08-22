import asyncio
import json
import re

import openai
from openai import AsyncOpenAI
from pyasn1_modules.rfc5990 import aes128_Wrap
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.bot.create_bot import send_task_user
from app.chat_gpt.dao import  MessageDAO
from app.chat_gpt.utils.promts import SYSTEM_PROMPT

from app.config import settings
from app.database import SessionDep, async_session_maker
from app.tasks.dao import TaskDAO
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate
from app.users.dao import UserDAO

client = AsyncOpenAI(api_key=settings.CHAT_GPT_API_KEY)


# async def format_text(session: SessionDep, text: str):
#     # Получаем данные об исполнителях из базы
#     tasks_db = await session.execute(
#         select(Task).options(selectinload(Task.executor))
#     )
#     tasks_db = tasks_db.scalars().all()
#
#     # Создаем словарь для быстрого доступа к данным исполнителей по executor_id
#     executor_map = {
#         task.executor_id: task.executor for task in tasks_db if task.executor_id
#     }
#
#     # Преобразуем входной текст в JSON
#     text = re.sub(r'}\s*{', '},{', text.strip())
#     json_array_str = f"[{text}]"
#     tasks = json.loads(json_array_str)
#
#     # Карта ключей для Markdown
#     key_map = {
#         "title": "Название",
#         "description": "Описание",
#         "deadline_date": "Дедлайн",
#         "executor_id": "Исполнитель",
#         "status": "Статус"
#     }
#
#     # Форматируем в Markdown
#     md_lines = []
#     for i, task in enumerate(tasks, start=1):
#         md_lines.append(f"### 📝 Задача {i}")
#         for key, value in task.items():
#             if key == "executor_id":
#                 executor = executor_map.get(value)
#                 executor_str = f"{executor.name if executor else '—'} ({executor.username if executor and executor.username else '—'})"
#                 md_lines.append(f"**{key_map.get(key, key)}:** {executor_str}")
#             else:
#                 md_lines.append(f"**{key_map.get(key, key)}:** {value}")
#         md_lines.append("")  # Пустая строка между задачами
#
#     markdown_output = "\n".join(md_lines)
#     return markdown_output


async def check_keywords(session, text: str, chat_id: int):
    if "РАСПРЕДЕЛИ ЗАДАЧИ" in text:
        return "distribute"
    elif "СТАТУС ПО ЗАДАЧАМ" in text:
        return "status"
    elif "СТАТУС ПО ВСЕМ ЗАДАЧАМ" in text:
        return "status_all"
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
    action = await check_keywords(session, text, chat_id)

    if action == "distribute":
        gpt_input = [{"role": "system", "content": SYSTEM_PROMPT}]
        instructions = SYSTEM_PROMPT

        worker_info = await get_worker_info(session)
        gpt_input.append({"role": "user", "content": worker_info})

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

            for task in tasks:
                print(task.title)
                # await TaskDAO.add(session, **task.model_dump())
                # await send_task_user(session, task)

            return tasks

        except Exception as e:
            print(f"[ERROR PARSING TASK] {e}")
            print(f"GPT output was:\n{response}")

            return  response.output_text

    print(response.output_text)
    return response.output_text
    # return "Сообщение от нейросети"


async def main():
    async with async_session_maker() as session:
        print(await check_keywords(session=session, text="ЗАДАЧИ ПО ВСЕМ ПРОЕКТАМ", chat_id=1))

if __name__ == "__main__":
    # asyncio.run(create_response_gpt("хранит ли gpt контекст диалога если я подключаюсь по api. и как это сделать"))
    asyncio.run(main())
