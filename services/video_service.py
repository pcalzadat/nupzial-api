import os, uuid
import numpy as np
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip
from utils.blob_storage import upload_bytes_to_blob_storage
from azure.storage.blob import ContentSettings
from io import BytesIO

class VideoService:
    def __init__(self, static_videos_dir: str, overlay_path: str, audio_path: str, temp_dir: str):
        self.static_videos_dir = static_videos_dir
        self.overlay_path = overlay_path
        self.audio_path = audio_path
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def _subclip(self, clip: VideoFileClip, seconds: float) -> VideoFileClip:
        return clip.subclipped(seconds)

    # --- blend helpers ---
    @staticmethod
    def _screen_blend(bg, fg):
        bg = bg.astype(np.float32) / 255.0
        fg = fg.astype(np.float32) / 255.0
        scr = 1.0 - (1.0 - bg) * (1.0 - fg)
        return np.clip(scr * 255.0, 0, 255).astype(np.uint8)

    @staticmethod
    def _compose_screen(bg_clip, fg_clip_same_size):
        """
        Aplica screen entre bg y fg respetando la máscara del fg.
        Ambos deben tener mismo tamaño/duración.
        """
        def make_frame(get_frame, t):
            bg = bg_clip.get_frame(t)
            fg = fg_clip_same_size.get_frame(t)
            if fg_clip_same_size.mask is not None:
                m = fg_clip_same_size.mask.get_frame(t).astype(np.float32)  # [H,W]
            else:
                m = np.ones(bg.shape[:2], dtype=np.float32)

            scr = VideoService._screen_blend(bg, fg)
            m3 = m[..., None]
            out = bg * (1.0 - m3) + scr * m3
            return np.clip(out, 0, 255).astype(np.uint8)

        # transform aplica la función sobre cada frame
        return bg_clip.transform(make_frame)

    # -----------------------

    def compose_final(self, file_id:str, cartel: str, pareja: str) -> str:
        v1 = os.path.join(self.static_videos_dir, "nupzial1.mp4")
        v2 = os.path.join(self.static_videos_dir, "nupzial3.mp4")
        v3 = os.path.join(self.static_videos_dir, "nupzial4.mp4")

        print("Usando videos fijos:", v1, v2, v3)

        print(v1, os.path.exists(v1))
        print(v2, os.path.exists(v2))
        print(v3, os.path.exists(v3))

        if not (os.path.exists(v1) and os.path.exists(v2)):
            raise FileNotFoundError("Uno o más videos fijos no se encontraron")

        clips = []
        try:
            clip1 = VideoFileClip(v1);      
            clips.append(clip1)

            start_time_cartel = 0.5
            duration_cartel = 1.32 
            end_time_cartel = start_time_cartel + duration_cartel
            clip_cartel = VideoFileClip(self._local(cartel));
            subclip_cartel = clip_cartel.subclipped(start_time_cartel, end_time_cartel)   
            clips.append(subclip_cartel)

            clip2 = VideoFileClip(v2);                
            clips.append(clip2)

            #Clip pareja
            start_time_pareja = 0.5
            duration_pareja = 2.32 
            end_time_pareja = start_time_pareja + duration_pareja
            clip_pareja = VideoFileClip(self._local(pareja));
            subclip_pareja = clip_pareja.subclipped(start_time_pareja, end_time_pareja)   
            clips.append(subclip_pareja)

            clip3 = VideoFileClip(v3); 
            clips.append(clip3)

            '''clip_polaroid = self._subclip(VideoFileClip(self._local(polaroid)), 2); 
            clips.append(clip_polaroid)
            
            clip2 = VideoFileClip(v2);                
            clips.append(clip2)

            clip_pareja = self._subclip(VideoFileClip(self._local(pareja)), 3);     
            clips.append(clip_pareja)

            clip3 = VideoFileClip(v3); 
            clips.append(clip3)'''

            min_h = min(int(c.h) for c in clips)
            resized = [c.resized(height=min_h) for c in clips]
            final_clip = concatenate_videoclips(resized, method="compose")
            
            # Efectos overlay
            if os.path.exists(self.overlay_path):
                overlay = (VideoFileClip(self.overlay_path, has_mask=True)
                           .with_duration(final_clip.duration)
                           .resized(final_clip.size))
                final_clip = self._compose_screen(final_clip, overlay)
                overlay.close()

            # Audio
            if os.path.exists(self.audio_path):
                audio = AudioFileClip(self.audio_path).subclipped(0, final_clip.duration)
                final_clip = final_clip.with_audio(audio)
            

            # Escribir a archivo temporal, leer bytes y subir a Blob Storage
            tmp_out = os.path.join(self.temp_dir, f"{uuid.uuid4().hex}.mp4")
            audio_tmp = os.path.join(self.temp_dir, f"temp-audio-{uuid.uuid4()}.m4a")
            final_clip.write_videofile(
                tmp_out,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=audio_tmp,
                remove_temp=True,
                fps=24
            )

            # Leer bytes del archivo generado
            with open(tmp_out, "rb") as f:
                video_bytes = f.read()

            # Subir a blob storage usando la función de bytes
            filename = f'vid_final_{file_id}'

            content_settings = ContentSettings(content_type="video/mp4")
            _, public_url = upload_bytes_to_blob_storage(
                video_content= video_bytes,
                content_settings=content_settings,
                filename=filename,
                folder=file_id,
                generate_sas=True
            )

            print("Video final subido a blob storage:", public_url)
            
            return public_url
        finally:
            # Cerrar clips individuales
            for c in clips:
                try:
                    if hasattr(c, "close"): c.close()
                except:
                    pass
            # Cerrar final_clip si existe
            if 'final_clip' in locals():
                try:
                    if hasattr(final_clip, "close"): final_clip.close()
                except:
                    pass
            # Eliminar archivo temporal si quedó
            if 'tmp_out' in locals():
                try:
                    if os.path.exists(tmp_out):
                        os.remove(tmp_out)
                except:
                    pass

    def _local(self, url_path: str) -> str:
        return url_path.replace("/api/media/", "") if url_path.startswith("/api/media/") else url_path
