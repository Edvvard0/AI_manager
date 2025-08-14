import tiktoken

from app.chat_gpt.dao import MessageDAO
from app.config import settings
from app.database import SessionDep


SYSTEM_PROMPT = """
Отвечай строго в формате JSON, соответствующем этой Pydantic-модели:

{
    "title": "string — название задачи",
    "description": "string — описание задачи",
    "deadline_date": "YYYY-MM-DD",
    "executor_id": int,
    "status": "Начал" 
}

Не добавляй ничего кроме JSON.
"""


def count_tokens(messages, model):
    enc = tiktoken.encoding_for_model(model)
    return sum(len(enc.encode(m)) for m in messages)


async def calculate_daily_usage(session: SessionDep, history_limit=10):
    model = settings.CHAT_GPT_MODEL

    MODEL_PRICES = {
        model: {"input": 0.05, "output": 00.40},  # $ per 1M tokens
    }

    all_msgs = await MessageDAO.get_message_today(session)

    total_input_tokens = 0
    total_output_tokens = 0

    # Проходим по всем user-сообщениям — они инициируют запрос к API
    for idx, msg in enumerate(all_msgs):
        if msg.is_user:
            # Берём предыдущие N сообщений для контекста
            start_context_idx = max(0, idx - history_limit)
            context_msgs = all_msgs[start_context_idx:idx]

            # Считаем токены для контекста + текущего сообщения пользователя
            input_texts = [m.content for m in context_msgs if m.is_user or not m.is_user]
            input_texts.append(msg.content)
            input_tokens = count_tokens(input_texts, model)
            total_input_tokens += input_tokens

            # Находим ответ бота (следующее сообщение assistant)
            if idx + 1 < len(all_msgs) and not all_msgs[idx + 1].is_user:
                output_tokens = count_tokens([all_msgs[idx + 1].content], model)
                total_output_tokens += output_tokens

    # Стоимость
    prices = MODEL_PRICES[model]
    input_cost = (total_input_tokens / 1_000_000) * prices["input"]
    output_cost = (total_output_tokens / 1_000_000) * prices["output"]
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(total_cost, 4),
    }
