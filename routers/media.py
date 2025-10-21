import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import Tuple
import requests
from utils.blob_storage import upload_bytes_to_blob_storage

router = APIRouter(prefix="/api")

'''@router.get("/media/{file_path:path}")
def serve_media(file_path: str):
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")
    full_path = os.path.join(os.getcwd(), os.path.normpath(file_path))
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if file_path.endswith(".mp4"): mt = "video/mp4"
    elif file_path.endswith(".png"): mt = "image/png"
    elif file_path.endswith((".jpg", ".jpeg")): mt = "image/jpeg"
    else: mt = "application/octet-stream"
    return FileResponse(full_path, media_type=mt)'''


@router.post("/saveImage")
async def save_image(file: UploadFile = File(...)):
    """
    Recibe una imagen desde el front, la sube a Azure Blob Storage usando
    upload_bytes_to_blob_storage y devuelve la URL pública.
    """
    unique_id = str(uuid.uuid4().hex) #id único para el archivo y nombre de la carpeta
    filename = f'img_pareja_{unique_id}'

    # Validar tipo de archivo
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    # Leer contenido
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded file: {e}")

    # Preparar content settings como dict (upload_bytes_to_blob_storage acepta dict)
    content_settings = {"content_type": file.content_type}

    try:
        file_id, public_url = upload_bytes_to_blob_storage(
            video_content=content,
            content_settings=content_settings,
            filename=filename,
            folder=unique_id,
            generate_sas=False
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    
    #send_power_automate(nombre1="N/A", nombre2="N/A", email1="pcalzada@integratecnologia.es", email2="pcalzada@integratecnologia.es", video_uri=public_url)

    return {"id": unique_id, "file_id": file_id, "image_url": public_url}


def send_power_automate(nombre1: str, nombre2: str, email1: str, email2: str, video_uri: str, timeout: int = 30):
    """
    Llama a la API externa de Power Automate enviando los parámetros en el body JSON.
    Devuelve el JSON de respuesta si existe, o el texto de la respuesta.
    Lanza RuntimeError si falla la llamada.
    """
    url = ("https://default63722aa14f5d494d89d25ae5974aab.fc.environment.api.powerplatform.com:443/"
            "powerautomate/automations/direct/workflows/d69522d29974438b8ffbfa614f2d904f/"
            "triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Lx2g4vD_XPZey5kGryFjJmgHBnp9yIGTfF58CGD05rg")

    payload = {
        "nombre1": nombre1,
        "nombre2": nombre2,
        "email1": email1,
        "email2": email2,
        "videoURI": video_uri
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"Error calling external API: {e}") from e
