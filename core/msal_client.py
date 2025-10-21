# core/msal_client.py
import uuid
import msal
from fastapi import Request
from core.config import settings

AUTHORITY = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}"
GRAPH_SCOPES = settings.GRAPH_SCOPES.split()

# Cache en memoria por sesión (simple para backend)
_TOKEN_CACHES: dict[str, msal.SerializableTokenCache] = {}

def _get_sid(request: Request) -> str:
    sid = request.session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        request.session["sid"] = sid
    return sid

def load_cache(request: Request) -> msal.SerializableTokenCache:
    sid = _get_sid(request)
    cache = _TOKEN_CACHES.get(sid)
    if not cache:
        cache = msal.SerializableTokenCache()
        _TOKEN_CACHES[sid] = cache
    return cache

def build_cca(request: Request) -> msal.ConfidentialClientApplication:
    cache = load_cache(request)
    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=settings.AZURE_CLIENT_SECRET,
        token_cache=cache,
    )

def get_scopes() -> list[str]:
    return GRAPH_SCOPES
