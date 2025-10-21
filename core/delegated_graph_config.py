# delegated_graph_config.py
from typing import List, Optional, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class DelegatedGraphSettings(BaseSettings):
    AZURE_SCOPES: str = "https://graph.microsoft.com/.default"
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: Optional[str] = None   # <-- opcional
    AZURE_USER_EMAIL: str

    # Por defecto para delegado:
    AZURE_SCOPES: List[str] = ["Mail.Send", "User.Read"]

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    TEMP_DIR: str = "temp_files"
    GRAPH_BASE: str = "https://graph.microsoft.com/v1.0"
    STATIC_VIDEOS: str = "static/videos"
    STATIC_OVERLAY: str = "static/overlay/efectoluces-logo.mov"
    STATIC_AUDIO: str = "static/audio/audio.mp4"
    
    RUNWAY_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("AZURE_SCOPES", mode="after")
    @classmethod
    def parse_azure_scopes(cls, v):
        if isinstance(v, str):
            return [scope.strip() for scope in v.split()]
        return v

    @field_validator("AZURE_CLIENT_SECRET", mode="before")
    @classmethod
    def clean_secret(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None     # "" -> None
        return v

    @field_validator("AZURE_SCOPES", mode="before")
    @classmethod
    def coerce_scopes(cls, v: Any) -> List[str]:
        # Acepta: lista, JSON, o string con espacios/comas
        if v is None:
            return ["Mail.Send", "User.Read"]
        if isinstance(v, list):
            return [s for s in v if isinstance(s, str) and s.strip()]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["Mail.Send", "User.Read"]
            # JSON array
            if s.startswith("[") and s.endswith("]"):
                import json
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            # coma o espacio
            parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
            return parts or ["Mail.Send", "User.Read"]
        # fallback
        return ["Mail.Send", "User.Read"]


def get_delegated_graph_settings() -> DelegatedGraphSettings:
    return DelegatedGraphSettings()
