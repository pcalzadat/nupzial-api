import os
from typing import Optional
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel, constr
import httpx
from core.config import settings

WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID
GRAPH_API_VERSION = settings.GRAPH_API_VERSION
API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"

class SendMessageReq(BaseModel):
    to: constr(strip_whitespace=True)
    text: Optional[str] = None
    template_name: Optional[str] = "hello_world"
    template_language: str = "es"

def ensure_e164(msisdn: str) -> str:
    msisdn = msisdn.strip().replace(" ", "")
    if not msisdn.startswith("+"):
        # Asume España (+34) si viene sin prefijo; AJUSTA esto a tu caso
        if msisdn.startswith("0"):
            msisdn = msisdn[1:]
        msisdn = "+34" + msisdn
    return msisdn

router = APIRouter(prefix="/api")

@router.post("/whatsapp/send")
async def send_whatsapp(req: SendMessageReq):

    print("Enviando WhatsApp a", req.to)
    
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    to = ensure_e164(req.to)

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    }

    """if req.template_name and not req.text:
        # Mensaje de TEMPLATE (fuera de 24h o para iniciar conversación)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"}
            }
        }
    else:
        # Mensaje de TEXTO libre (dentro de ventana de 24h)
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": req.text or "¡Hola! 👋"
            }
        }"""

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(API_URL, headers=headers, json=payload)
        if r.status_code >= 400:
            # WhatsApp devuelve errores útiles en JSON
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()