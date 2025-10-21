from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    RUNWAY_API_KEY: str

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    TEMP_DIR: str = "temp_files"

    STATIC_VIDEOS: str = "static/videos"
    STATIC_OVERLAY: str = "static/overlay/efectoluces-logo.mov"
    STATIC_AUDIO: str = "static/audio/audio.mp4"

    AZURE_STORAGE_CONNECTION_STRING: str | None = Field(None, env="AZURE_STORAGE_CONNECTION_STRING")
    AZURE_BLOB_CONTAINER: str = Field("public-data", env="AZURE_BLOB_CONTAINER")

    # Configuración en Pydantic v2 (sustituye a class Config)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Permite definir CORS_ORIGINS="http://a.com,http://b.com" en .env
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
        

settings = Settings()
