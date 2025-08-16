from io import BytesIO

from fastapi import UploadFile

from app.chat_gpt.utils.utils import client


async def create_file(file: UploadFile):
    file_content = await file.read()
    result = await client.files.create(
        file=(file.filename, BytesIO(file_content)),
        purpose="assistants"
    )

    # 2. Создаем векторное хранилище
    vector_store = await client.vector_stores.create(name="my-store")

    # 3. Добавляем файл в векторное хранилище
    await client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=result.id
    )

    return vector_store