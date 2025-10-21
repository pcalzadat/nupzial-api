import base64, requests
from runwayml import RunwayML

class RunwayService:
    def __init__(self, client: RunwayML):
        self.client = client


    # Image_to_video (using data URI)
    def image_to_video(self, data_uri: str, prompt: str, ratio: str = "1280:720", **opts) -> bytes:
        print("Enviando imagen y prompt a Runway:", prompt)
        try:
            print("Antes de crear tarea de video")
            task = self.client.image_to_video.create(model="gen4_turbo", prompt_image=data_uri, prompt_text=prompt, ratio=ratio, duration=5, **opts)
            print("Tarea de video creada, esperando resultado")
            result = task.wait_for_task_output()
            print("Resultado recibido de Runway:", result)
            video_url = result.output[0]
            return video_url
        except Exception as e:
            print("Error en image_to_video:", repr(e))
            raise


    def create_video_pareja(self, image_url: bytes) -> bytes:
        print("URL recibida con imagen:", image_url )
        prompt_vid = ("a romantic couple walking hand in hand through a beautiful garden at sunset, soft lighting, cinematic style, 24fps, smooth camera movement")
        return self.image_to_video(image_url, prompt_vid, ratio="1280:720")


    def create_cartel_video(self, image_url: str) -> bytes:
        print("URL recibida en service:", image_url )
        #data_uri = self.bytes_to_data_uri(image_url, "image/png")
        prompt_vid = ('At the venue entrance, a wedding welcome sign stands adorned with flowers and satin ribbons that gently sway in the breeze; petals and confetti quiver faintly. The camera performs a subtle, steady push-in with a soft zoom, introducing mild parallax and natural micro-movement. Ambient elements flutter: fairy lights flicker, dust motes drift in warm daylight. Cinematic live-action, elegant and romantic, golden hour glow, shallow depth of field with creamy bokeh, crisp yet delicate textures, tasteful filmic contrast, 24fps.')
        vid_url = self.image_to_video(image_url, prompt_vid, ratio="1280:720")
        return vid_url
