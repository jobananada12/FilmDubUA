"""Local speech-to-text helper for selected FilmDubUA clips."""
from pathlib import Path
import subprocess
import sys

class SpeechRecognitionError(RuntimeError):
    pass


def transcribe_clip(input_path: str, output_json: str) -> str:
    """Transcribe a clip with Whisper CLI when available.

    The function intentionally works on the selected montage clip only.
    Whisper is expected to be installed locally; no cloud API is required.
    """
    src = Path(input_path).resolve()
    out = Path(output_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise SpeechRecognitionError(f"Кліп не знайдено: {src}")

    # Prefer faster-whisper CLI/module if installed; fall back to whisper.
    cmd = [sys.executable, '-m', 'whisper', str(src), '--language', 'uk', '--task', 'transcribe', '--output_format', 'json', '--output_dir', str(out.parent)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SpeechRecognitionError(proc.stderr.strip() or proc.stdout.strip() or 'Whisper не зміг розпізнати кліп')

    generated = out.parent / f'{src.stem}.json'
    if not generated.exists():
        candidates = list(out.parent.glob(f'{src.stem}*.json'))
        if not candidates:
            raise SpeechRecognitionError('Whisper завершився, але JSON результат не знайдено')
        generated = candidates[0]
    if generated != out:
        generated.replace(out)
    return str(out)
