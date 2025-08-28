from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai
import os
import re
from io import BytesIO
from typing import List

from app.config import settings

openai.api_key = settings.CHAT_GPT_API_KEY

MINUTES_TRIGGER = "АНАЛИЗ ПЯТИМИНУТКИ"

# ==== Вспомогалки ====

def _is_minutes_analysis(prompt: str) -> bool:
    return MINUTES_TRIGGER.casefold() in (prompt or "").casefold()

def _clip(text: str, limit: int = 12000) -> str:
    if text is None:
        return ""
    return text if len(text) <= limit else text[:limit] + "\n\n[...обрезано для модели...]"

def build_minutes_messages(transcript_text: str) -> List[dict]:
    """
    Формирует жёсткие сообщения для сборки протокола.
    """
    clipped = _clip(transcript_text)

    system = (
        "Ты — секретарь совещаний. Составляешь протокол «Пятиминутки» строго по шаблону.\n"
        "Требования:\n"
        "• Всегда те же заголовки и эмодзи.\n"
        "• Никаких пояснений, преамбул и рассуждений — только готовый протокол.\n"
        "• Если нет данных — пиши «(уточнить)».\n"
        "• В блоке ✅ задачи расписывай тремя отдельными строками дат/срока/ответственного (📅, ⏳, 👤) для КАЖДОЙ задачи.\n"
        "• Без пустых пунктов и без объединения нескольких задач в одну строку.\n"
        "• Язык ответа: русский.\n"
    )

    template = (
        "📄 Протокол № {{номер или (уточнить)}}\n"
        "📌 Совещание «Пятиминутка»\n"
        "📅 {{дата из стенограммы или текущая}}\n"
        "💬 Регулярное совещание по будням\n\n"
        "⸻\n\n"
        "👥 Участники:\n"
        "{{по одному в строке, «👤 Фамилия И. О.» или (уточнить)}}\n\n"
        "⸻\n\n"
        "📑 Основные вопросы:\n"
        " 1. {{...}}\n"
        " 2. {{...}}\n"
        " 3. {{...}}\n\n"
        "⸻\n\n"
        "✅ Решения (фиксируются как задачи):\n"
        " 1. {{краткое формулирование}}\n"
        "📅 {{дата совещания}}\n"
        "⏳ {{дедлайн или (уточнить)}}\n"
        "👤 {{ответственный или (уточнить)}}\n"
        " 2. {{...}}\n"
        "📅 {{...}}\n"
        "⏳ {{...}}\n"
        "👤 {{...}}\n"
    )

    user = (
        f"Стенограмма (после автоматической расшифровки):\n\n{clipped}\n\n"
        f"Собери протокол строго по шаблону ниже и верни ТОЛЬКО протокол без комментариев:\n\n{template}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

REQUIRED_BLOCKS = [
    r"^📄 Протокол № .+",
    r"^📌 Совещание «Пятиминутка»$",
    r"^📅 .+",
    r"^💬 Регулярное совещание по будням$",
    r"^⸻$",
    r"^👥 Участники:\s*(?:\n👤 .+)+",
    r"^⸻$",
    r"^📑 Основные вопросы:\s*(?:\n \d+\. .+)+",
    r"^⸻$",
    r"^✅ Решения \(фиксируются как задачи\):\s*(?:\n \d+\. .+\n📅 .+\n⏳ .+\n👤 .+)+"
]

def validate_minutes(text: str) -> bool:
    flags = re.MULTILINE
    return all(re.search(p, text, flags) for p in REQUIRED_BLOCKS)

async def transcribe_audio(file: UploadFile) -> str:
    """
    Расшифровка аудио через Whisper-1.
    """
    # Проверяем тип
    filename = file.filename or "audio"
    content_type = file.content_type or ""
    ext_ok = any(filename.lower().endswith(x) for x in [".mp3", ".wav", ".m4a", ".ogg"])
    type_ok = content_type.startswith("audio/")
    if not (ext_ok or type_ok):
        raise HTTPException(status_code=400, detail="Пришлите аудио-файл (mp3/wav/m4a/ogg).")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Пустой файл.")

    bio = BytesIO(raw)
    bio.name = filename

    try:
        tr = openai.audio.transcriptions.create(
            model="whisper-1",
            file=bio
        )
        return tr.text or ""
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка расшифровки аудио: {e}")

async def generate_protocol_from_transcript(transcript_text: str) -> str:
    """
    Сборка протокола GPT-4o по жёстким messages.
    """
    messages = build_minutes_messages(transcript_text)

    try:
        resp = await _run_chat(messages, temperature=0.1, max_tokens=1400)
        text = resp
        if not validate_minutes(text):
            # Одна попытка автопочинки формата
            fix_messages = [
                {"role": "system", "content": (
                    "Исправь формат ровно под шаблон протокола «Пятиминутка». "
                    "Никаких комментариев — только конечный протокол. "
                    "Сохрани все эмодзи и блоки. Если данных нет — «(уточнить)». "
                    "Каждая задача: три строки дат/срока/ответственного (📅, ⏳, 👤)."
                )},
                {"role": "user", "content": f"Вот твой предыдущий ответ, приведи его к строгому шаблону:\n\n{text}"}
            ]
            text2 = await _run_chat(fix_messages, temperature=0.0, max_tokens=1400)
            if validate_minutes(text2):
                return text2
        return text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка генерации протокола: {e}")

async def _run_chat(messages: List[dict], temperature: float, max_tokens: int) -> str:
    """
    Обёртка вызова chat.completions (совместимо с используемым у тебя SDK).
    """
    resp = await _to_thread(
        openai.chat.completions.create,
        model="gpt-4o",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content

# Простая утилита для переноса синхронного CPU/IO-bound в отдельный поток
import asyncio
def _to_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: func(*args, **kwargs))