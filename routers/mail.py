"""from fastapi import APIRouter, HTTPException, Depends, Request
from core.deps import get_delegated_graph_service
from services.delegated_graph_service import DelegatedGraphService
from schemas.generation import EmailRequest
from core.config import settings # Import settings

router = APIRouter(prefix="/api")

@router.post("/send_email")
async def send_email(
    data: EmailRequest, 
    graph: DelegatedGraphService = Depends(get_delegated_graph_service)
):
    
    #Send an email using delegated permissions or application permissions.
    
    #The first time this endpoint is called, it will prompt the user to authenticate
    #using a device code flow. The token will be cached for subsequent requests.
    
    try:
        # Send the email using delegated permissions
        success = graph.send_email(
            to_email=data.to_email,
            subject=data.subject or "Sin asunto",
            message=data.message or "",
            from_email=data.from_email or settings.AZURE_USER_EMAIL,  # Use provided email or fallback to configured email
            content_type="HTML" if "<" in (data.message or "") else "Text"
        )
        
        if success:
            return {
                "status": "success", 
                "message": "Correo enviado correctamente"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="No se pudo enviar el correo"
            )
            
    except Exception as e:
        error_detail = str(e)
        status_code = 500
        
        # Provide more specific error messages for common issues
        if "AADSTS65001" in error_detail:
            error_detail = "El usuario o administrador no ha otorgado los permisos necesarios. Por favor, contacta al administrador."
            status_code = 403
        elif "AADSTS7000218" in error_detail:
            error_detail = "Error de autenticación. Por favor, vuelve a autenticarte."
            status_code = 401
            
        raise HTTPException(
            status_code=status_code, 
            detail=error_detail
        )

@router.get("/user_info")
async def get_user_info(
    graph: DelegatedGraphService = Depends(get_delegated_graph_service)
):
    
    #Get information about the currently authenticated user.
    #This can be used to verify authentication and get user details.
    
    try:
        user_info = graph.get_user_info()
        return {
            "status": "success",
            "user": {
                "display_name": user_info.get("displayName"),
                "email": user_info.get("userPrincipalName"),
                "id": user_info.get("id")
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener información del usuario: {str(e)}"
        )
"""


# routers/mail.py
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import httpx
from core.config import settings
from core.msal_client import build_cca, get_scopes
from schemas.mail import SendEmailIn

router = APIRouter(prefix="/mail", tags=["mail"])
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _build_graph_message(p: SendEmailIn) -> dict:
    body = {"contentType": "Text", "content": ""}
    if p.body_html:
        body = {"contentType": "HTML", "content": p.body_html}
    elif p.body_text:
        body = {"contentType": "Text", "content": p.body_text}

    def rl(emails): 
        return [{"emailAddress": {"address": e}} for e in (emails or [])]

    msg = {
        "subject": p.subject,
        "body": body,
        "toRecipients": rl(p.to),
    }
    if p.cc:  msg["ccRecipients"]  = rl(p.cc)
    if p.bcc: msg["bccRecipients"] = rl(p.bcc)

    if p.attachments:
        msg["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": a.name,
                "contentType": a.content_type,
                "contentBytes": a.content_base64,
            } for a in p.attachments
        ]

    return {"message": msg, "saveToSentItems": p.save_to_sent_items}

@router.get("/login")
def login(request: Request,
          popup: bool = Query(False),
          origin: str | None = Query(None)):
    """
    Si popup=1, guardamos el origin (front) para usarlo en el postMessage.
    """
    if popup:
        request.session["pm_origin"] = origin or str(settings.FRONTEND_URL)
    cca = build_cca(request)
    state = "mail"
    request.session["state"] = state
    auth_url = cca.get_authorization_request_url(
        scopes=get_scopes(),
        redirect_uri=settings.REDIRECT_URI,
        state=state,
        prompt="select_account",
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    popup: bool = Query(False)
):
    if error:
        raise HTTPException(status_code=401, detail=f"{error}: {error_description}")
    if not code or state != request.session.get("state"):
        raise HTTPException(status_code=400, detail="Estado inválido o falta 'code'.")

    cca = build_cca(request)
    result = cca.acquire_token_by_authorization_code(
        code=code,
        scopes=get_scopes(),
        redirect_uri=settings.REDIRECT_URI,
    )
    if "access_token" not in result:
        raise HTTPException(status_code=401, detail=result.get("error_description", "No se pudo canjear el código."))

    # Si venimos en modo popup, devolvemos una página mínima que notifica al opener y se cierra
    if popup:
        origin = request.session.get("pm_origin", str(settings.FRONTEND_URL))
        html = f"""
        <!doctype html>
        <html><head><meta charset="utf-8" /></head>
        <body>
        <script>
          (function() {{
            try {{
              const msg = {{ type: "graph-auth-complete", ok: true }};
              if (window.opener) {{
                window.opener.postMessage(msg, "{origin}");
              }}
            }} catch (e) {{}}
            window.close();
          }})();
        </script>
        Autenticación completada. Puede cerrar esta ventana.
        </body></html>
        """
        return HTMLResponse(content=html)

    return JSONResponse({"status": "ok", "message": "Autenticado correctamente"})


@router.get("/me")
def me(request: Request):
    cca = build_cca(request)
    accounts = cca.get_accounts()
    if not accounts:
        return {"authenticated": False}
    result = cca.acquire_token_silent(get_scopes(), account=accounts[0])
    return {"authenticated": bool(result and "access_token" in result)}

@router.post("/send")
async def send(request: Request, payload: SendEmailIn):
    cca = build_cca(request)
    accounts = cca.get_accounts()
    if not accounts:
        return RedirectResponse(url="/mail/login", status_code=307)

    result = cca.acquire_token_silent(get_scopes(), account=accounts[0])
    if not result or "access_token" not in result:
        return RedirectResponse(url="/mail/login", status_code=307)

    graph_payload = _build_graph_message(payload)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/me/sendMail",
            headers={
                "Authorization": f"Bearer {result['access_token']}",
                "Content-Type": "application/json",
            },
            json=graph_payload,
        )
    if resp.status_code not in (200, 202):
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        raise HTTPException(status_code=resp.status_code, detail={"graph_error": err})

    return {"status": "sent"}
