import asyncio
import base64
import os
from io import BytesIO

import PyPDF2
import docx
import openai
from fastapi import UploadFile
from openai import OpenAI
from pydantic import BaseModel

from app.chat_gpt.utils.utils import client
from app.config import settings


# async def create_file(file: UploadFile):
#     file_content = await file.read()
#     result = await client.files.create(
#         file=(file.filename, BytesIO(file_content)),
#         purpose="assistants"
#     )
#
#     # 2. Создаем векторное хранилище
#     vector_store = await client.vector_stores.create(name="my-store")
#
#     # 3. Добавляем файл в векторное хранилище
#     await client.vector_stores.files.create(
#         vector_store_id=vector_store.id,
#         file_id=result.id
#     )
#     await asyncio.sleep(1)
#     print(vector_store.id)
#
#     return vector_store


async def process_file(file_content: bytes, content_type: str, filename: str, prompt: str) -> list:
    openai.api_key = settings.CHAT_GPT_API_KEY
    """
    Обрабатывает файл в зависимости от его типа и формирует сообщения для OpenAI.
    Возвращает список сообщений для API.
    """
    messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
    file_extension = os.path.splitext(filename)[1].lower()

    if content_type.startswith('text/') or file_extension in ['.txt', '.csv', '.md']:
        # Текстовые файлы
        file_text = file_content.decode("utf-8")
        full_prompt = f"{prompt}\n\nFile content:\n{file_text}"
        messages.append({"role": "user", "content": full_prompt})

    elif file_extension in ['.doc', '.docx']:
        # Обработка .doc и .docx
        try:
            doc = docx.Document(BytesIO(file_content))
            file_text = "\n".join([para.text for para in doc.paragraphs if para.text])
            full_prompt = f"{prompt}\n\nDocument content:\n{file_text}"
            messages.append({"role": "user", "content": full_prompt})
        except Exception as e:
            raise ValueError(f"Failed to process .doc/.docx file: {str(e)}")

    elif content_type == 'application/pdf' or file_extension == '.pdf':
        # PDF файлы: извлечение текста
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        file_text = ""
        for page in pdf_reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                file_text += extracted_text + "\n"
        full_prompt = f"{prompt}\n\nPDF content:\n{file_text}"
        messages.append({"role": "user", "content": full_prompt})

    elif content_type.startswith('image/') or file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
        # Изображения: отправка как base64 для vision модели
        base64_image = base64.b64encode(file_content).decode('utf-8')
        image_url = f"data:{content_type};base64,{base64_image}"
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        })

    elif content_type.startswith('audio/') or file_extension in ['.mp3', '.wav', '.m4a']:
        # Аудио файлы: транскрипция с Whisper
        audio_file = BytesIO(file_content)
        audio_file.name = filename  # OpenAI требует имя файла
        transcription = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        file_text = transcription.text
        full_prompt = f"{prompt}\n\nAudio transcription:\n{file_text}"
        messages.append({"role": "user", "content": full_prompt})

    else:
        # Неизвестный тип: попытка прочитать как текст
        try:
            file_text = file_content.decode("utf-8")
            full_prompt = f"{prompt}\n\nFile content (unknown type, read as text):\n{file_text}"
            messages.append({"role": "user", "content": full_prompt})
        except:
            raise ValueError("Unsupported file type or unable to process.")

    return messages