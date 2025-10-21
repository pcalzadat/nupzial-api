from PIL import Image
import io

def compress_image(image_data: bytes, max_size_mb: float = 4.5, quality: int = 85) -> bytes:
    img = Image.open(io.BytesIO(image_data))
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    while len(out.getvalue())/(1024*1024) > max_size_mb and quality > 30:
        quality -= 10
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()
