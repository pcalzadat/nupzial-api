from fastapi import APIRouter, HTTPException, Depends

import uuid
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import os, sys
from schemas.generation import EditCartelRequest
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from utils.blob_storage import upload_to_blob_storage

router = APIRouter(prefix="/api")

W, H = 1920, 1080

CRIMSON_FONT = "./static/fonts/Crimson-Bouquet.otf"
PLAYFAIR_FONT = "./static/fonts/PlayfairDisplay-Regular.ttf"

def load_font(path, size):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró la fuente: {path}")
    return ImageFont.truetype(path, size=size)

def visible_height(font, text):
    dummy = Image.new("L", (10, 10), 0)
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), text if text else " ", font=font)
    return bbox[3] - bbox[1]

def text_width(draw, text, font):
    return int(draw.textlength(text, font=font))

def draw_text_with_shadow(base_img, text, font, x, y,
                          text_color="#FFFFFF",
                          shadow_color="#35302C37",
                          shadow_offset=(1, 2),
                          shadow_blur=5):
    """Dibuja texto con sombra difusa."""
    shadow_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sx, sy = shadow_offset
    sd.text((x + sx, y + sy), text, font=font, fill=shadow_color)
    if shadow_blur > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    base_img = Image.alpha_composite(base_img, shadow_layer)

    d = ImageDraw.Draw(base_img)
    d.text((x, y), text, font=font, fill=text_color)
    return base_img

def render_save_the_date(
    input_image: str,
    output_image: str,
    names: str = "Lucia y Juan",
    date_str: str = "26/07/26",
    line_spacing_main: int = 32,     # Espacio entre líneas 2 y 3
    line_spacing_top: int = 2,       # Espacio entre línea 1 y 2 (más pequeño)
    vertical_shift: int = -78,       # Desplaza todo el bloque (negativo = hacia arriba)
    shadow_color: str = "#35302C37",
    shadow_offset: tuple = (1, 2),
    shadow_blur: int = 5,
    l2_size: int = 76,
):
    img = Image.open(input_image).convert("RGBA")
    img = ImageOps.exif_transpose(img)

    if img.size != (W, H):
        raise ValueError(f"La imagen debe ser {W}x{H}. Actual: {img.size}")

    draw = ImageDraw.Draw(img)

    # Textos y tamaños fijos
    l1_text, l1_size, l1_font = "Save the Date", 120, CRIMSON_FONT
    l2_text, l2_font = names, PLAYFAIR_FONT
    l3_text, l3_size, l3_font = date_str, 66, PLAYFAIR_FONT

    # Cargar fuentes
    f1 = load_font(l1_font, l1_size)
    f2 = load_font(l2_font, l2_size)
    f3 = load_font(l3_font, l3_size)

    # Calcular alturas visibles
    h1 = visible_height(f1, l1_text)
    h2 = visible_height(f2, l2_text)
    h3 = visible_height(f3, l3_text)

    total_h = h1 + line_spacing_top + h2 + line_spacing_main + h3
    cur_y = (H - total_h) // 2 + vertical_shift

    def draw_centered_line(text, font, y):
        w = text_width(draw, text, font)
        x = (W - w) // 2
        nonlocal img
        img = draw_text_with_shadow(
            img,
            text,
            font,
            x,
            y,
            text_color="#FFFFFF",
            shadow_color=shadow_color,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
        )

    draw_centered_line(l1_text, f1, cur_y)
    cur_y += h1 + line_spacing_top
    draw_centered_line(l2_text, f2, cur_y)
    cur_y += h2 + line_spacing_main
    draw_centered_line(l3_text, f3, cur_y)

    ext = os.path.splitext(output_image)[1].lower()
    if ext == ".png":
        img.save(output_image)
    else:
        img.convert("RGB").save(output_image, quality=100, subsampling=0)



@router.post("/edit_cartel_image")
async def edit_cartel_image(data: EditCartelRequest):

    # input fijo
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    input_img = os.path.join(base_dir, "static", "img", "WoodenSign.jpg")
    if not os.path.exists(input_img):
        raise HTTPException(status_code=500, detail=f"Imagen de entrada no encontrada: {input_img}")

    # output temporal
    out_name = f"img_cartel_{data.id}.jpg"
    out_path = os.path.join(tempfile.gettempdir(), out_name)

    # Llamada a la función de render
    names = f"{data.nombre1} y {data.nombre2}"
    fecha = f"{data.fecha}"

    sum_chars = len(data.nombre1) + len(data.nombre2)

    if sum_chars > 10:
        render_save_the_date(input_image=input_img, output_image=out_path, names=names, date_str=fecha)
    else:
        render_save_the_date(input_image=input_img, output_image=out_path, names=names, date_str=fecha, vertical_shift=-74, line_spacing_top=1, line_spacing_main=38, l2_size=102)

    # Upload to Blob
    file_id, public_url = upload_to_blob_storage(
        file_path=out_path,
        filename=f'img_cartel_{data.id}',
        content_type="image/jpeg",
        folder=data.id  # Optional: organize files in folders
    )

    return {
        "image_id": file_id,
        "image_url": public_url
    }