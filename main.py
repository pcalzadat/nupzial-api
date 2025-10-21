from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers import ai_generation, final_video, mail, media, whatsapp, image_generation
from utils.files import init_temp_dir, cleanup_temp_files

app = FastAPI(title="Video Generation API")

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
    return {"message": "Video Generation API is running"}



