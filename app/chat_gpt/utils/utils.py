import json
import re
from datetime import date
from typing import Optional, List, Any

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

    print(tasks)
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


def check_keywords(text: str) -> Optional[str]:
    """Надёжно определяем режим по тексту (регистр/пробелы не важны)."""
    t = re.sub(r"\s+", " ", (text or "")).strip().lower()
    if re.search(r"\bраспредел(и|ить)\s+задач[ауеы]?\b", t) or "распредели задачи" in t:
        return "distribute"
    if "статус по всем задачам" in t:
        return "status_all"
    if "статус по задачам" in t:
        return "status"
    if "начало пятиминутки" in t:
        return "minutes_start"
    return None


def extract_json_array(text: str) -> Optional[List[Any]]:
    """Пытаемся достать JSON-массив из строки (в т.ч. из ```json ...``` блоков)."""
    if not text:
        return None
    # 1) как есть
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    # 2) из код-блока
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, flags=re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 3) грубый поиск первого массива
    m2 = re.search(r"(\[[\s\S]*\])", text)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass
    # 4) исторический хак: склейка `}{` → `},{`
    try:
        candidate = re.sub(r'}\s*{', '},{', text.strip())
        candidate = f"[{candidate}]"
        obj = json.loads(candidate)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    return None


async def get_last_messages(session: SessionDep, chat_id: int):
    messages = await MessageDAO.get_history(session, chat_id)
    return  messages


async def get_worker_info(session: SessionDep):
    workers = await UserDAO.find_all(session, **{"is_admin": False})
    summary = "\n".join(f"Имя {w.name}, Отдел {w.department},  Username: {w.username} ,  ID: {w.id}" for w in workers)
    # print(summary)
    return f"Список сотрудников:\n{summary}"


async def get_tasks_info(session: SessionDep, project_id: int | None = None, only_active: bool = False) -> str:
    """
    Дайджест задач. Если project_id=None — берём ВСЕ задачи.
    """
    q = select(Task).options(joinedload(Task.executor))
    if project_id:
        q = q.where(Task.project_id == project_id)

    tasks = (await session.execute(q)).scalars().all()
    if only_active:
        tasks = [t for t in tasks if (t.status or "").lower() not in {"готово", "done", "closed"}]

    if not tasks:
        scope = f"проекта {project_id}" if project_id else "всех проектов"
        return f"Задач для {scope} нет."

    summary = "\n".join(
        f"{t.title} — {t.status or '—'} |\n"
        f"Описание: {t.description or '—'}\n"
        f"Дедлайн: {t.deadline_date or '—'}\n"
        f"Исполнитель: {t.executor.name if t.executor else '—'} "
        f"ID Исполнителя: {t.executor.id if t.executor else '—'} "
        f"(@{t.executor.username if t.executor and t.executor.username else '—'})\n"
        for t in tasks
    )
    return f"Информация по задачам (проанализируй и распиши по сотрудникам):\n{summary}"


async def create_response_gpt(session: SessionDep, text: str, chat_id: int, project_id: int | None = None):
    """
    В режиме 'distribute' возвращает ВСЕГДА JSON-массив задач (как list[TaskCreate] при успехе, иначе сырой list[dict]).
    В остальных режимах — обычный текст.
    """
    messages = await get_last_messages(session, chat_id)
    action = check_keywords(text)

    gpt_input = []
    instructions = ""

    if action == "distribute":
        # Системный промпт + жёсткая инструкция вернуть JSON-массив БЕЗ пояснений
        sys = (
            f"{SYSTEM_PROMPT}\n\n"
            "ВНИМАНИЕ: Верни СТРОГО JSON-массив объектов задач без Markdown и без пояснений. "
            "Каждый элемент должен содержать как минимум: title, description, deadline_date (YYYY-MM-DD), executor_id. "
            "Допустимые поля: status, comment, file_path, tag, project_id. "
            "Если project_id не указан во входных данных, оставь его пустым (или не добавляй) — сервер подставит сам."
            "ты должен "
        )
        gpt_input = [{"role": "system", "content": sys}]
        instructions = sys

        # Подкладываем Сотрудников И Задачи (по проекту или все)
        worker_info = await get_worker_info(session)
        tasks_info = await get_tasks_info(session, project_id=project_id, only_active=True)

        gpt_input.append({"role": "user", "content": worker_info})
        gpt_input.append({"role": "user", "content": tasks_info})

    elif action == "minutes_start":
        sys_minutes = (
            "Ты ассистент для короткой планёрки («пятиминутки»). "
            "Дай компактный список открытых и просроченных задач на сегодня: "
            "пунктами: [Исполнитель] — Задача — дедлайн — текущий статус. "
            "Сначала просроченные, затем на сегодня, затем прочие. Без лишних вступлений."
        )
        gpt_input = [{"role": "system", "content": sys_minutes}]
        minutes_tasks = await get_minutes_tasks(session)
        gpt_input.append({"role": "user", "content": minutes_tasks})
        gpt_input.append({"role": "user", "content": text})

    elif action == "status":
            task_info = await get_tasks_info(session, project_id=project_id)
            worker_info = await get_worker_info(session)
            gpt_input.append({"role": "user", "content": task_info})
            gpt_input.append({"role": "user", "content": worker_info})

    elif action == "status_all":
        sys_status_all = (
            "Кратко отдай статус по всем задачам: сгруппируй по исполнителям, отметь просрочки и близкие дедлайны."
        )
        gpt_input = [{"role": "system", "content": sys_status_all}]
        task_info = await get_tasks_info(session, project_id=None)
        worker_info = await get_worker_info(session)
        gpt_input.append({"role": "user", "content": task_info})
        gpt_input.append({"role": "user", "content": worker_info})
        gpt_input.append({"role": "user", "content": text})

    # История → текущий вопрос
    for msg in messages:
        gpt_input.append({
            "role": "user" if msg.is_user else "assistant",
            "content": msg.content
        })
    gpt_input.append({"role": "user", "content": text})

    # для НЕ distribute добавим SYSTEM_MD в конец как у тебя
    if action != "distribute":
        gpt_input.append({"role": "system", "content": SYSTEM_MD})

    # Вызов (Responses API без response_format)
    resp = await client.responses.create(
        model=settings.CHAT_GPT_MODEL,
        input=gpt_input,
        instructions=instructions
    )

    if action == "distribute":
        # Стабильный парсинг массива задач
        txt = resp.output_text or ""
        tasks_data = extract_json_array(txt)

        if tasks_data is None:
            # Последняя попытка: "}{"
            try:
                fixed = re.sub(r'}\s*{', '},{', txt.strip())
                tasks_data = json.loads(f"[{fixed}]")
            except Exception:
                tasks_data = None

        if tasks_data is None:
            # пусть роут решит вернуть 422
            return txt

        # подставим project_id (может быть None — это ок; ты решишь в слое сохранения)
        enriched = []
        for t in tasks_data:
            if isinstance(t, dict) and "project_id" not in t:
                t = {**t, "project_id": project_id}
            enriched.append(t)

        # Если получается — валидируем pydantic-моделью
        try:
            tasks = [TaskCreate.model_validate(t) for t in enriched]
            return tasks
        except Exception:
            return enriched

    # Обычный ответ
    return resp.output_text
