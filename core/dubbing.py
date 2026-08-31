"""Mix a generated dialogue WAV into a montage clip.

The source video is never modified. A new MP4 is written with the video's
picture, the selected/background soundtrack, and the Ukrainian TTS dialogue
placed at the dialogue start time.
"""
from pathlib import Path
import subprocess


class DubbingError(RuntimeError):
    pass


def mix_dialogue(video_path: str, background_path: str, voice_path: str,
                 output_path: str, start_ms: int = 0, volume: float = 1.0) -> str:
    video = Path(video_path).resolve()
    background = Path(background_path).resolve()
    voice = Path(voice_path).resolve()
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    for p in (video, background, voice):
        if not p.exists():
            raise DubbingError(f"Файл не знайдено: {p}")
    if start_ms < 0:
        raise DubbingError("Початок репліки не може бути від'ємним")

    delay = int(start_ms)
    # Background is the full scene soundtrack without vocals. TTS is delayed
    # to the dialogue start and mixed over it. The video stream is copied.
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-i", str(background),
        "-i", str(voice),
        "-filter_complex",
        f"[2:a]volume={max(0.0, float(volume))},adelay={delay}|{delay}[voice];"
        "[1:a][voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]",
        "-map", "0:v:0",
        "-map", "[mix]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(output),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DubbingError(proc.stderr[-5000:] or "FFmpeg не зміг зібрати дубльований кліп")
    if not output.exists() or output.stat().st_size == 0:
        raise DubbingError("FFmpeg не створив дубльований кліп")
    return str(output)
