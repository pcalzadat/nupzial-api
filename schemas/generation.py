from pydantic import BaseModel
from typing import Optional
from datetime import date

class EditCartelRequest(BaseModel):
    id: str
    nombre1: str
    nombre2: str
    email1: str
    email2: str
    telef1: str
    telef2: str
    fecha: str
    image_url: str

class Persona(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    email: Optional[str] = None

class ParejaCreate(BaseModel):
    persona1: Persona
    persona2: Persona
    fecha: str

class CartelRequest(BaseModel):
    id: str
    nombre1: str
    nombre2: str
    image_url: str
    demo: bool

class PolaroidImgRequest(BaseModel):
    key: str
    fecha: str
    url: str
    demo: bool

class ParejaVidRequest(BaseModel):
    id: str
    image_url: str
    demo: bool

class VideoFinalRequest(BaseModel):
    id: str
    nombre1: str
    nombre2: str
    email1: str
    email2: str
    cartel_video: str
    pareja_video: str

class EmailRequest(BaseModel):
    to_email: str
    subject: str
    message: str
    from_email: str | None = None



