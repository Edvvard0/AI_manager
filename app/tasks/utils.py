import os
from pathlib import Path
from fastapi import UploadFile, HTTPException


async def save_uploaded_file(file: UploadFile, upload_dir: str = "data_files") -> str:
    try:
        # Создаем директорию если не существует
        os.makedirs(upload_dir, exist_ok=True)

        if not file.filename:
            raise ValueError("No filename provided")

        # Генерируем уникальное имя файла
        original_name = Path(file.filename).stem
        extension = Path(file.filename).suffix
        counter = 1

        while True:
            new_filename = f"{original_name}_{counter}{extension}" if counter > 1 else f"{original_name}{extension}"
            file_path = os.path.join(upload_dir, new_filename)

            if not os.path.exists(file_path):
                break
            counter += 1

        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return file_path

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при сохранении файла: {str(e)}"
        )