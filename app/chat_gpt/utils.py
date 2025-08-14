import asyncio

from openai import AsyncOpenAI, OpenAI

from app.config import settings

client = AsyncOpenAI(api_key=settings.CHAT_GPT_API_KEY)

async def create_response_gpt(text: str):
    response = await client.responses.create(
        model="gpt-4.1",
        input=text
    )
    # print(response.output_text)
    return response
    # return "Сообщение от нейросети"

# def ask_gpt(chat_id, user_message):
#     # 1. Получаем историю чата
#     history = get_messages_from_db(chat_id)  # list[{"role": "user", "content": "..."}]
#
#     # 2. Добавляем новое сообщение
#     history.append({"role": "user", "content": user_message})
#
#     # 3. Отправляем в API
#     completion = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=history
#     )
#
#     # 4. Сохраняем ответ модели в БД
#     save_message(chat_id, "assistant", completion.choices[0].message.content)
#
#     return completion.choices[0].message.content

if __name__ == "__main__":
    asyncio.run(create_response_gpt("хранит ли gpt контекст диалога если я подключаюсь по api. и как это сделать"))

