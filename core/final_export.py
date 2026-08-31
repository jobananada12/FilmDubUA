from pathlib import Path
import subprocess

class FinalExportError(RuntimeError):
    pass


def export_final(video: str, audio: str, reaction: str, output: str, subtitles: str = '', reaction_scale: float = .34) -> str:
    """Compose 9:16 video + mixed audio + optional reaction overlay + subtitles."""
    for p in (video, audio, reaction):
        if p and not Path(p).exists():
            raise FileNotFoundError(p)
    out=Path(output).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if subtitles:
        sub=str(Path(subtitles).resolve()).replace('\\','/').replace(':','\\:')
        vf += f",subtitles='{sub}'"
    # Reaction is scaled to the lower part and overlaid on the 9:16 canvas.
    if reaction:
        vf += ";[1:v]scale=367:650:force_original_aspect_ratio=decrease[rx];[0:v][rx]overlay=(W-w)/2:H-h-35[v]"
        cmd=['ffmpeg','-y','-i',video,'-i',reaction,'-i',audio,'-filter_complex',vf,'-map','[v]','-map','2:a:0','-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(out)]
    else:
        cmd=['ffmpeg','-y','-i',video,'-i',audio,'-vf',vf,'-map','0:v:0','-map','1:a:0','-shortest','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: raise FinalExportError(r.stderr[-4000:])
    return str(out)
