from pathlib import Path
import subprocess

class ClipExportError(RuntimeError): pass

def export_clip(input_video: str, output_video: str, start_ms: int, end_ms: int) -> str:
    if not Path(input_video).exists(): raise FileNotFoundError(input_video)
    if end_ms <= start_ms: raise ValueError('Кінець уривка має бути після початку')
    out=Path(output_video).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    start=max(0,start_ms)/1000; duration=(end_ms-start_ms)/1000
    vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920'
    cmd=['ffmpeg','-y','-ss',str(start),'-i',input_video,'-t',str(duration),'-vf',vf,'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: raise ClipExportError(r.stderr[-4000:])
    return str(out)
