from fastapi import APIRouter, Depends
from core.deps import get_video_service
from services.video_service import VideoService
from schemas.generation import VideoFinalRequest

import os
import uuid
import requests
from urllib.parse import urlparse

router = APIRouter(prefix="/api")

def _download_to_dir(url: str, dest_dir: str) -> str:
    """
    Descarga la URL al directorio dest_dir y devuelve la ruta absoluta del fichero.
    Usa streaming y genera un nombre con uuid. Intenta inferir extensión desde la URL o el header.
    """
    parsed = urlparse(url)
    # intenta sacar extensión de la ruta
    ext = os.path.splitext(parsed.path)[1]
    tmp_name = f"input_{uuid.uuid4()}{ext or ''}"
    out_path = os.path.join(dest_dir, tmp_name)

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        # si no hay ext, intenta del content-type
        if not ext:
            ct = r.headers.get("content-type", "")
            if "mp4" in ct: out_path += ".mp4"
            elif "mpeg" in ct: out_path += ".mp4"
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return out_path


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


@router.post("/generate_final_video")
async def generate_final_video(req: VideoFinalRequest, vs: VideoService = Depends(get_video_service)):
    """
    Recibe en req URLs públicas (blob). Descarga localmente y llama a VideoService.compose_final.
    Devuelve path absoluto y URL pública usando get_media_url.
    """
    downloaded = []
    print("Generando video final con entradas:", req.cartel_video, req.pareja_video)
    try:
        # Asegurar que el directorio temporal exista (VideoService ya crea temp_dir)
        temp_dir = vs.temp_dir

        # Cartel_video
        cartel_local = _download_to_dir(req.cartel_video, temp_dir)
        downloaded.append(cartel_local)

        # Pareja_video
        pareja_local = _download_to_dir(req.pareja_video, temp_dir)
        downloaded.append(pareja_local)

        # Llamada al servicio (pasa rutas locales)
        out = vs.compose_final(req.id, cartel_local, pareja_local)

        send_power_automate(nombre1=req.nombre1, nombre2=req.nombre2, email1=req.email1, email2=req.email2, video_uri=out)

        # Devolver ruta y URL pública (get_media_url debe aceptar path absoluto o convertir)
        return {"status": "success", "video_path": out}
    finally:
        # limpiar ficheros de entrada descargados
        for p in downloaded:
            try:
                if os.path.exists(p): os.remove(p)
            except:
                pass