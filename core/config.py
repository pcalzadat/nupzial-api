from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    RUNWAY_API_KEY: str

    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_USER_EMAIL: str

    SESSION_SECRET:str
    REDIRECT_URI:str
    FRONTEND_URL:str

    WHATSAPP_TOKEN:str
    WHATSAPP_PHONE_NUMBER_ID:int
    GRAPH_API_VERSION:str
    
    # Microsoft Graph API scopes - will be parsed from space-separated string
    GRAPH_SCOPES: str = "Mail.Send User.Read"

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    TEMP_DIR: str = "temp_files"
    GRAPH_BASE: str = "https://graph.microsoft.com/v1.0"
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