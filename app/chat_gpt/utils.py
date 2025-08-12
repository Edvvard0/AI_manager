import asyncio

from openai import AsyncOpenAI, OpenAI

from app.config import settings

client = AsyncOpenAI(api_key="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")

async def create_response_gpt(text: str):
    # response = await client.responses.create(
    #     model="gpt-4.1",
    #     input=text
    # )
    # print(response)
    # return response
    return "Сообщение от нейросети"

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

# if __name__ == "__main__":
#     asyncio.run(create_response_gpt(" в чем различия intel и amd"))

