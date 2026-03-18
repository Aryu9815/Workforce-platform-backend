import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.constants import IMAGE_DIR as UPLOAD_DIR

async def save_image(file: UploadFile):

    if not file:
        return None

    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"

    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return file_path