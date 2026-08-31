from pathlib import Path
import subprocess
import shutil

class TTSError(RuntimeError):
    pass


def available_engines():
    """Return locally available TTS backends. Piper is preferred when installed."""
    engines=[]
    if shutil.which('piper'):
        engines.append('piper')
    return engines


def synthesize_piper(text: str, voice_model: str, output_wav: str, speaker: str = '') -> str:
    """Generate a WAV locally with Piper. No cloud/API is required."""
    if not text.strip():
        raise ValueError('Текст репліки порожній')
    if not Path(voice_model).exists():
        raise FileNotFoundError(voice_model)
    out=Path(output_wav).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    cmd=['piper','--model',str(Path(voice_model).resolve()),'--output_file',str(out)]
    if speaker:
        cmd += ['--speaker', speaker]
    result=subprocess.run(cmd,input=text,encoding='utf-8',capture_output=True)
    if result.returncode != 0:
        raise TTSError(result.stderr.strip() or result.stdout.strip() or 'Piper failed')
    return str(out)
