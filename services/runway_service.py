import base64, requests
from runwayml import RunwayML
import logging

logger = logging.getLogger("video_generation_app")

class RunwayService:
    def __init__(self, client: RunwayML):
        self.client = client


    # Image_to_video (using data URI)
    def image_to_video(self, data_uri: str, prompt: str, ratio: str = "1280:720", **opts) -> bytes:
        print("Enviando imagen y prompt a Runway:", prompt)
        try:
            logger.info("Antes de crear tarea de video")
            task = self.client.image_to_video.create(model="gen4_turbo", prompt_image=data_uri, prompt_text=prompt, ratio=ratio, duration=5, **opts)
            logger.info("Tarea de video creada, esperando resultado")
            result = task.wait_for_task_output()
            logger.info(f'Resultado recibido de Runway: {result}')
            video_url = result.output[0]
            return video_url
        except Exception as e:
            print("Error en image_to_video:", repr(e))
            raise


    def create_video_pareja(self, image_url: bytes) -> bytes:
        print("URL recibida con imagen:", image_url )
        prompt_vid = ("Subtle and affectionate movement between the subjects, maintaining the direct gaze towards the camera. They must share a gesture of affection without close physical contact, such as a slight head tilt, an exchange of glances, or a soft, warm smile. Strict preservation of the facial and bodily appearance of the people from the original image. Medium shot, soft lighting, cinematic.")
        return self.image_to_video(image_url, prompt_vid, ratio="1280:720")


    def create_cartel_video(self, image_url: str) -> bytes:
        print("URL recibida en service:", image_url )
        logger.info(f'URL recibida en service: %s {image_url}')
        #data_uri = self.bytes_to_data_uri(image_url, "image/png")
        prompt_vid = ('At the venue entrance, a wedding welcome sign stands adorned with flowers and satin ribbons that gently sway in the breeze; petals and confetti quiver faintly. The camera performs a subtle, steady push-in with a soft zoom, introducing mild parallax and natural micro-movement. Ambient elements flutter: fairy lights flicker, dust motes drift in warm daylight. Cinematic live-action, elegant and romantic, golden hour glow, shallow depth of field with creamy bokeh, crisp yet delicate textures, tasteful filmic contrast, 24fps.')
        vid_url = self.image_to_video(image_url, prompt_vid, ratio="1280:720")
        #vid_url = 'https://dnznrvs05pmza.cloudfront.net/154c4ee8-cdd4-4a55-81fe-ebcb7dbe9788.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiZDA3ZDQxYmU2MWEyMDMwYyIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc2MTI2NDAwMH0.h80Id3L0imu7HlgZzUgv-oVLaJ8r6QYWi-z2UPY-6f8'
        return vid_url
