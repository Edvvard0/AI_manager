
from http.client import HTTPException

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from docx import Document

import os

import tempfile


async def process_docx_file(file: UploadFile) -> str:
    """Обработка .docx файлов"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
        content = await file.read()
        temp_docx.write(content)
        temp_docx_path = temp_docx.name

    try:
        doc = Document(temp_docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        print(text)
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing DOCX file: {str(e)}")
    finally:
        os.unlink(temp_docx_path)