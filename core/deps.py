from fastapi import Depends
from runwayml import RunwayML
from .config import settings
from services.runway_service import RunwayService
from services.video_service import VideoService
from services.graph_service import GraphService
from services.delegated_graph_service import DelegatedGraphService
from pathlib import Path
from typing import List
import os
from core.delegated_graph_config import get_delegated_graph_settings

def get_runway_client() -> RunwayML:
    return RunwayML(api_key=settings.RUNWAY_API_KEY)

def get_runway_service(client: RunwayML = Depends(get_runway_client)) -> RunwayService:
    return RunwayService(client)

def get_video_service() -> VideoService:
    return VideoService(
        static_videos_dir=settings.STATIC_VIDEOS,
        overlay_path=settings.STATIC_OVERLAY,
        audio_path=settings.STATIC_AUDIO,
        temp_dir=settings.TEMP_DIR,
    )

settings = get_delegated_graph_settings()

def get_graph_service() -> GraphService:
    return GraphService(
        tenant_id=settings.AZURE_TENANT_ID,
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET,
        user_email=settings.AZURE_USER_EMAIL,
        graph_base=settings.GRAPH_BASE,
    )


def get_delegated_graph_service():
    s = get_delegated_graph_settings()

    # Token cache file
    cache_dir = os.path.join(Path.home(), ".video_editor_app")
    os.makedirs(cache_dir, exist_ok=True)
    token_cache_path = os.path.join(cache_dir, "msal_token_cache.json")

    # ¿Secreto realmente presente?
    has_secret = bool(s.AZURE_CLIENT_SECRET and s.AZURE_CLIENT_SECRET.strip())

    if has_secret:
        print("client secret", s.AZURE_CLIENT_SECRET)
        # Flujo de aplicación
        scopes = ["https://graph.microsoft.com/.default"]
        client_secret = s.AZURE_CLIENT_SECRET
    else:
        # Delegado: sin URLs ni /.default
        raw = s.AZURE_SCOPES
        scopes = raw if isinstance(raw, list) else [p for p in str(raw).replace(",", " ").split() if p]
        scopes = [sc for sc in scopes if "://" not in sc and not sc.endswith("/.default")]
        if not scopes:
            scopes = ["User.Read", "Mail.Send"]
        client_secret = None

    return DelegatedGraphService(
        client_id=s.AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{s.AZURE_TENANT_ID}",
        scopes=scopes,
        token_cache_path=token_cache_path,
        client_secret=client_secret,
    )