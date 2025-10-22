import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers import ai_generation, final_video, mail, media, whatsapp, image_generation
from utils.files import init_temp_dir, cleanup_temp_files
import os

# === LOGGING CONFIGURATION ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

app = FastAPI(title="Video Generation API")

# Formato uniforme y legible
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotación: máximo 5 MB por archivo, guarda 5 copias
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Salida a consola (Azure App Service captura stdout/stderr automáticamente)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Configurar root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
)

# Logger principal de la app
logger = logging.getLogger("video_generation_app")

logger.info("Logger configurado correctamente.")

app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SESSION_SECRET, 
    same_site="lax",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_temp_dir(settings.TEMP_DIR)

@app.on_event("startup")
async def _startup():
    cleanup_temp_files()

app.include_router(media.router)
app.include_router(ai_generation.router)
app.include_router(final_video.router)
app.include_router(mail.router)
app.include_router(whatsapp.router)
app.include_router(image_generation.router)

@app.get("/")
def root():
    logger.info("Logger configurado correctamente. | API Root accessed.")
    return {"message": "Video Generation API is running"}



