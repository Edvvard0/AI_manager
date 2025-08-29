from sqlalchemy.ext.asyncio import AsyncSession

from app.chat_gpt.dao import MessageDAO, ChatDAO
from app.chat_gpt.schemas import SFirstMessage
from app.chat_gpt.utils.promts import SYSTEM_MD
from app.chat_gpt.utils.utils import client
from app.config import settings
from app.database import SessionDep


async def first_message(prompt: str,
                        tg_id: int,
                        session: AsyncSession,
                        project_id: int | None = None,):
    # try:
        response = await client.responses.create(
            model=settings.CHAT_GPT_MODEL,
            input=f"{SYSTEM_MD}  {prompt}",
            instructions="сперва придумай короткое название названия этому чату напиши его и после ***, \
            чтобы я понимал где оно заканчивается, первая строка должна быть без markdown, в названии чата тоже не должно ничего упоминуться о markdown, ты должен сосредоточиться на сути вопроса"
        )
        # print(response.output_text)
        text = response.output_text
        parts = text.split("***", 1)

        title = parts[0].strip().replace("\n", " ")
        text = parts[1].strip() if len(parts) > 1 else ""

        chat = await ChatDAO.create_chat_by_tg_id(session, title=title, tg_id=tg_id, project_id=project_id)
        # print(chat)

        # await MessageDAO.add(session, chat_id=chat.id, is_user=True, content=prompt)
        # await MessageDAO.add(session, chat_id=chat.id, is_user=False, content=text)

        return {"message": text,
                "chat_id": chat.id,
                "chat_name": title}

    # except Exception as e:
    #     return {"error": f"произошла ошибка: {e}"}