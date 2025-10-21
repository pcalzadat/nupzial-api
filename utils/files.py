import os, uuid, shutil
from fastapi import UploadFile
from fastapi.responses import FileResponse
from .images import compress_image

TEMP_DIR = None  # se fija en main al arrancar (o usa settings)

PLACEHOLDERS = {
    "cartel_img": "placeholder_assets/cartel.png",
    "cartel": "placeholder_assets/cartel.mp4",
    "polaroid_img": "placeholder_assets/polaroid.png",
    "polaroid": "placeholder_assets/polaroid.mp4",
    "video": "placeholder_assets/pareja.mp4",
}

def init_temp_dir(path: str):
    global TEMP_DIR
    TEMP_DIR = path
    os.makedirs(TEMP_DIR, exist_ok=True)

def save_uploaded_file(upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename or "")[1] or ".png"
    path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}{ext}")
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path

def get_media_url(rel_path: str) -> str:
    return f"/api/media/{rel_path.replace('\\', '/')}"

def get_placeholder(kind: str) -> str:
    return PLACEHOLDERS.get(kind, PLACEHOLDERS["cartel"])

def cleanup_temp_files():
    # (opcional: criterio por edad)
    for name in os.listdir(TEMP_DIR):
        fp = os.path.join(TEMP_DIR, name)
        if os.path.isfile(fp):
            try: os.unlink(fp)
            except: pass
