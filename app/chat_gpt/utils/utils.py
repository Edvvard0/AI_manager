import asyncio
import json
import re

from openai import AsyncOpenAI
from pyasn1_modules.rfc5990 import aes128_Wrap

from app.bot.create_bot import send_task_user
from app.chat_gpt.dao import  MessageDAO
from app.chat_gpt.utils.utils_token import SYSTEM_PROMPT

from app.config import settings
from app.database import SessionDep, async_session_maker
from app.tasks.dao import TaskDAO
from app.tasks.schemas import TaskCreate
from app.users.dao import UserDAO

client = AsyncOpenAI(api_key=settings.CHAT_GPT_API_KEY)


async def check_keywords(session, text: str, chat_id: int):
    if "РАСПРЕДЕЛИ ЗАДАЧИ" in text:
        return "distribute"
    elif "СТАТУС ПО ЗАДАЧАМ" in text:
        return "status"
    else:
        return None


async def distribute_task(task: TaskCreate):
    # Тут потом будет логика записи задачи в БД
    print(f"[DISTRIBUTE TASK] {task}")


async def get_last_messages(session: SessionDep, chat_id: int):
    messages = await MessageDAO.get_history(session, chat_id)
    return  messages


async def get_worker_info(session: SessionDep):
    workers = await UserDAO.find_all(session)
    summary = "\n".join(f"Имя {w.name}, Отдел {w.department},  Username: {w.username}" for w in workers)
    # print(summary)
    return f"Список сотрудников:\n{summary}"


async def get_tasks_info(session: SessionDep):
    tasks = await TaskDAO.find_all(session)
    # print(tasks[0].title)
    summary = "\n".join(f"{t.title} — {t.status}  Описание задачи: {t.description}, Дедлайн {t.deadline_date}," for t in tasks)
    # print(summary)
    return f"Информация по задачам:\n{summary}"


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
                print(task)
                await distribute_task(task)

                await TaskDAO.add(session, **task.model_dump())
                await send_task_user(session, task)

        except Exception as e:
            print(f"[ERROR PARSING TASK] {e}")
            print(f"GPT output was:\n{response}")

    # print(response.output_text)
    return response.output_text
    # return "Сообщение от нейросети"


async def main():
    async with async_session_maker() as session:
        print(await check_keywords(session=session, text="ЗАДАЧИ ПО ВСЕМ ПРОЕКТАМ", chat_id=1))

if __name__ == "__main__":
    # asyncio.run(create_response_gpt("хранит ли gpt контекст диалога если я подключаюсь по api. и как это сделать"))
    asyncio.run(main())
