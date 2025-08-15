# import asyncio
# from http.client import HTTPException
#
# from fastapi import  APIRouter
# from openai import OpenAI
#
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from docx import Document
# import openai
# import os
# from typing import Optional
# import tempfile
# import pdfplumber  # для чтения PDF
# from PIL import Image  # для обработки изображений
# import pytesseract
# from starlette.responses import JSONResponse
#
# from app.chat_gpt.utils.utils import create_response_gpt
# from app.chat_gpt.utils.utils_docx import process_docx_file
# from app.config import settings
# from app.database import SessionDep
#
# router = APIRouter(prefix="/test_file",
#                    tags=["File"]
#                    )
#
# # Initialize OpenAI client (replace with your API key)
# client = OpenAI(api_key=settings.CHAT_GPT_API_KEY)
#
# # Настройки для обработки изображений (OCR)
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Укажите правильный путь
#
#
#
#
#
# async def send_to_chatgpt(prompt: str, file_content: Optional[str] = None) -> str:
#     """Обновленная функция для новой версии OpenAI API"""
#     messages = []
#
#     if file_content:
#         messages.append({
#             "role": "system",
#             "content": f"Вот содержимое загруженного DOCX файла:\n{file_content}"
#         })
#
#     messages.append({
#         "role": "user",
#         "content": prompt
#     })
#
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4",
#             messages=messages,
#             temperature=0.7
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Ошибка при обращении к ChatGPT API: {str(e)}")
#
#
# @router.post("/process-docx/")
# async def process_docx_file_and_prompt(
#         session: SessionDep,
#         chat_id: int,
#         prompt: str = Form(...),
#         file: UploadFile = File(...)
# ):
#     try:
#         # Проверяем расширение файла
#         if not file.filename.lower().endswith('.docx'):
#             raise HTTPException(status_code=400, detail="Поддерживаются только .docx файлы")
#
#         file_content = await process_docx_file(file)
#         prompt = prompt + f"Содержимое файла {file_content}"
#         response = await create_response_gpt(text=prompt, chat_id=chat_id, session=session)
#
#         return JSONResponse(content={
#             "response": response,
#         })
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
