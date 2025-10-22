import os, base64, uuid, httpx, tempfile, certifi, ssl
import aiohttp
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Body
from core.deps import get_runway_service
from services.runway_service import RunwayService
from utils.files import save_uploaded_file, get_media_url, get_placeholder
from utils.images import compress_image
from schemas.generation import CartelRequest, ParejaVidRequest
from utils.blob_storage import upload_bytes_to_blob_storage, upload_to_blob_storage
from azure.storage.blob import ContentSettings  # Add this import at the top
import logging

logger = logging.getLogger("video_generation_app")
router = APIRouter(prefix="/api")

ssl_ctx = ssl.create_default_context(cafile=certifi.where())

'''@router.post("/create_cartel")
async def create_cartel(req: CartelRequest, runway: RunwayService = Depends(get_runway_service)):
    try:
        img_bytes, vid_bytes = runway.create_cartel_assets(req.nombre1, req.nombre2)
        img_path = f"temp_files/cartel_{uuid.uuid4()}.png"
        vid_path = f"temp_files/video_{uuid.uuid4()}.mp4"
        open(img_path, "wb").write(img_bytes)
        open(vid_path, "wb").write(vid_bytes)
        return {"status": "success", "image_path": img_path, "video_path": vid_path,
                "image_url": get_media_url(img_path), "video_url": get_media_url(vid_path)}
    except Exception:
        ph = get_placeholder("cartel")
        return {"status": "error", "message": "Error generando cartel. Using placeholder.",
                "image_path": None, "video_path": ph, "video_url": get_media_url(ph)}
'''
'''@router.post("/create_polaroid")
async def create_polaroid(fecha: str = Form(...), imagen: UploadFile = File(...),
                          runway: RunwayService = Depends(get_runway_service)):
    try:
        raw = await imagen.read()
        jpeg = compress_image(raw)
        img_bytes, vid_bytes = runway.create_polaroid_assets(fecha, jpeg)
        img_path = f"temp_files/polaroid_{uuid.uuid4()}.png"
        vid_path = f"temp_files/video_{uuid.uuid4()}.mp4"
        open(img_path, "wb").write(img_bytes)
        open(vid_path, "wb").write(vid_bytes)
        return {"status": "success", "image_path": img_path, "video_path": vid_path,
                "image_url": get_media_url(img_path), "video_url": get_media_url(vid_path)}
    except Exception:
        ph = get_placeholder("polaroid")
        return {"status": "error", "message": "Error generando polaroid. Using placeholder.",
                "image_path": None, "video_path": ph, "video_url": get_media_url(ph)}
'''
# Cache simple en memoria para URLs generadas
cartel_image_cache = {}


@router.post("/create_cartel_video")
async def create_cartel_video(
    data: CartelRequest,
    runway: RunwayService = Depends(get_runway_service),
):
    print("isDemo:", data.demo)
    logger.info(f'isDemo: {data.demo}')

    if data.demo:
        vid_url = "https://showroomblob.blob.core.windows.net/demo-data/cartel_vid_demo.mp4"
        logger.info(f'Demo vid url: {vid_url}')
    else:
        image_url = data.image_url
        logger.info(f'Image URL for cartel video generation: {image_url}')
        vid_url = runway.create_cartel_video(image_url)
        logger.info(f'Runway vid url: {vid_url}')

    logger.info(f'Generating cartel video for: {data.nombre1}, {data.nombre2} Demo: {data.demo}')
    filename = f'vid_cartel_{data.id}'

    out_path = os.path.join(tempfile.gettempdir(), filename)

    '''# Download video from Runway
    async with aiohttp.ClientSession() as session:
        async with session.get(vid_url) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Error downloading video from Runway")
            video_content = await response.read()
'''
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0), follow_redirects=True, headers={
            "User-Agent": "efor-appservice/1.0",
            "Accept": "*/*",
        }, verify=ssl_ctx) as client:
            logger.info("Cliente httpx creado correctamente")
            async with client.stream("GET", vid_url) as resp:
                logger.info(f"Respuesta recibida: HTTP {resp.status_code} de {resp.url}")
                if resp.status_code != 200:
                    snippet = (await resp.aread())[:1024]
                    logger.error(f"Error HTTP {resp.status_code}. Cuerpo parcial: {snippet!r}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Runway download failed (HTTP {resp.status_code}). "
                               f"URL final: {str(resp.url)} Body: {snippet!r}"
                    )
                with open(out_path, "wb") as f:
                    logger.info("Comenzando escritura del archivo en disco...")
                    total_bytes = 0
                    async for chunk in resp.aiter_bytes(1024 * 64):
                        if chunk:
                            f.write(chunk)
                            total_bytes += len(chunk)
                    logger.info(f"Descarga completada. Bytes escritos: {total_bytes}")

        file_id, public_url = upload_to_blob_storage(
            file_path=out_path,
            filename=filename,
            content_type=ContentSettings(content_type='video/mp4'),
            folder=data.id  # Optional: organize files in folders
        )

        return {
            "status": "success",
            "video_url": public_url
        }
        #return out_path
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading video from Runway: {e}")
    '''
    # Upload to blob storage
    file_id, public_url = upload_bytes_to_blob_storage(
        folder=data.id,
        filename=filename,
        video_content=video_content,
        content_settings=ContentSettings(
            content_type='video/mp4'
        )
    )

    return {
        "status": "success",
        "video_url": public_url
    }
    '''
    '''
    try:
        image_url = data.url
        print("Response from URL:", image_url)

        # Get video URL from Runway
        vid_url = runway.create_cartel_video(image_url)

        # Download video from Runway
        async with aiohttp.ClientSession() as session:
            async with session.get(vid_url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Error downloading video from Runway")
                video_content = await response.read()

        # Generate unique filename
        video_filename = f"cartel_{uuid.uuid4()}.mp4"
        
        # Upload to blob storage
        blob_url = await blob_storage.upload_to_blob_storage(
            container_name="videos",
            blob_name=video_filename,
            data=video_content,
            content_type="video/mp4"
        )

        return {
            "status": "success",
            "video_url": blob_url
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        ph = get_placeholder("cartel")
        return {
            "status": "error",
            "message": "Error generando video. Using placeholder.",
            "video_path": ph,
            "video_url": get_media_url(ph)
        }
    '''

    ''' 
    try:
        response = await data.url
        response.raise_for_status()

        vid_bytes = runway.create_cartel_video(response.content)
        vid_path = f"temp_files/video_{uuid.uuid4()}.mp4"
        with open(vid_path, "wb") as f:
            f.write(vid_bytes)

        return {
            "status": "success",
            "video_path": vid_path,
            "video_url": get_media_url(vid_path)
        }
    except Exception:
        ph = get_placeholder("cartel")
        return {
            "status": "error",
            "message": "Error generando video. Using placeholder.",
            "video_path": ph,
            "video_url": get_media_url(ph)
        }
    '''


    '''try:
        image_url = data.url
        print("Response from URL:", image_url)

        vid_url = runway.create_cartel_video(image_url)

        return {
            "status": "success",
            "video_url": vid_url
        }
    except Exception:
        ph = get_placeholder("cartel")
        return {
            "status": "error",
            "message": "Error generando video. Using placeholder.",
            "video_path": ph,
            "video_url": get_media_url(ph)
        }'''


@router.post("/create_video_pareja")
async def create_video_pareja(
    data: ParejaVidRequest,
    runway: RunwayService = Depends(get_runway_service),
):
    print("isDemo:", data.demo)

    if data.demo:
        vid_url = "https://showroomblob.blob.core.windows.net/demo-data/pareja_vid_demo.mp4"
    else:
        image_url = data.image_url
        print("Image URL for cartel video generation:", image_url)
        vid_url = "https://dnznrvs05pmza.cloudfront.net/879a7cb1-627b-4644-ac96-2404a6b91ea0.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiNzQyZGNjOTFmMmExZjdlYiIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc2MTI2NDAwMH0.wqkPAROtHxRkwhjhHsJmgJZccuptxkW-lz8PNpo4-Ro"
        #vid_url = runway.create_video_pareja(image_url)

    print("Generating pareja video for:", data.id, data.demo)

    # Download video from Runway
    async with aiohttp.ClientSession() as session:
        async with session.get(vid_url) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Error downloading video from Runway")
            video_content = await response.read()

    filename = f'vid_pareja_{data.id}'

    # Upload to blob storage
    file_id, public_url = upload_bytes_to_blob_storage(
        video_content=video_content,
        folder=data.id,
        filename=filename,
        content_settings=ContentSettings(
            content_type='video/mp4'
        )
    )

    return {
        "status": "success",
        "video_url": public_url
    }

'''@router.post("/create_video_pareja_v0")
async def create_video_pareja_v0(imagen: UploadFile = File(...), runway: RunwayService = Depends(get_runway_service)):
    try:
        raw = await imagen.read()
        vid_bytes = runway.create_video_from_image(raw)
        vid_path = f"temp_files/couple_video_{uuid.uuid4()}.mp4"
        open(vid_path, "wb").write(vid_bytes)
        return {"status": "success", "video_path": vid_path, "video_url": get_media_url(vid_path)}
    except Exception:
        ph = get_placeholder("video")
        return {"status": "error", "message": "Error generando video. Using placeholder.",
                "video_path": ph, "video_url": get_media_url(ph)}
'''