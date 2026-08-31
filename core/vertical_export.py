from pathlib import Path
import subprocess

class VerticalExportError(RuntimeError): pass

def export_vertical(input_video: str, output_video: str, subtitle_file: str = '') -> str:
    """Create a 1080x1920 9:16 base export with optional SRT subtitles."""
    if not Path(input_video).exists(): raise FileNotFoundError(input_video)
    out=Path(output_video).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    vf="scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    if subtitle_file:
        # Escape Windows drive separators for the FFmpeg subtitles filter.
        sub=str(Path(subtitle_file).resolve()).replace('\\','/').replace(':','\\:')
        vf += f",subtitles='{sub}'"
    cmd=['ffmpeg','-y','-i',input_video,'-vf',vf,'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: raise VerticalExportError(r.stderr[-3000:])
    return str(out)
