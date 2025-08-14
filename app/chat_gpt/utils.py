import asyncio
from datetime import datetime, timedelta

from openai import AsyncOpenAI, OpenAI
import tiktoken
from sqlalchemy import select, asc

from app.chat_gpt.dao import ChatDAO, MessageDAO
from app.chat_gpt.models import Message
from app.config import settings
from app.database import SessionDep, async_session_maker, get_session

client = AsyncOpenAI(api_key=settings.CHAT_GPT_API_KEY)


async def get_last_messages(session: SessionDep, chat_id: int):
    messages = await MessageDAO.get_history(session, chat_id)
    return  messages


async def create_response_gpt(session: SessionDep, text: str, chat_id: int):
    messages = await get_last_messages(session, chat_id)

    gpt_input = []
    for msg in messages:
        gpt_input.append({
            "role": "user" if msg.is_user else "assistant",
            "content": msg.content
        })

    gpt_input.append({"role": "user", "content": text})

    response = await client.responses.create(
        model=settings.CHAT_GPT_MODEL,
        input=gpt_input
    )

    # print(response.output_text)
    return response.output_text
    # return "Сообщение от нейросети"


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


async def main():
    async with async_session_maker() as session:
        print(await calculate_daily_usage(session))


if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(create_response_gpt("хранит ли gpt контекст диалога если я подключаюсь по api. и как это сделать"))

