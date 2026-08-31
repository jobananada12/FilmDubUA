"""Local vocal/background separation for FilmDubUA.

Uses Demucs when installed. The original file is never modified; separated
stems are written to an output directory. For a movie soundtrack, the
resulting no-vocals mix is the accompaniment/background track.
"""
from pathlib import Path
import subprocess
import sys

class VoiceSeparationError(RuntimeError):
    pass

def separate_voice(input_path: str, output_dir: str, model: str = "htdemucs") -> str:
    src = Path(input_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise VoiceSeparationError(f"Input file not found: {src}")
    cmd = [sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", model, "-o", str(out), str(src)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VoiceSeparationError(proc.stderr.strip() or proc.stdout.strip() or "Demucs failed")
    # Demucs writes no-vocals.wav inside model/source-name.
    candidate = out / model / src.stem / "no_vocals.wav"
    if not candidate.exists():
        candidates = list(out.rglob("no_vocals.wav"))
        if not candidates:
            raise VoiceSeparationError("Separation completed but no_vocals.wav was not found")
        candidate = candidates[0]
    return str(candidate)
