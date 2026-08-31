from pathlib import Path
import subprocess
import shutil

class TTSError(RuntimeError):
    pass


def available_engines():
    """Return locally available TTS backends."""
    engines=[]
    if shutil.which('piper'):
        engines.append('piper')
    try:
        import pyttsx3
        engines.append('pyttsx3')
    except ImportError:
        pass
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


def windows_voices():
    """Return installed Windows SAPI voices as (id, name, languages)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = []
        for voice in engine.getProperty('voices'):
            languages = []
            for lang in getattr(voice, 'languages', []) or []:
                if isinstance(lang, bytes):
                    lang = lang.decode(errors='ignore')
                languages.append(str(lang))
            voices.append((str(getattr(voice, 'id', '')), str(getattr(voice, 'name', '')), languages))
        engine.stop()
        return voices
    except Exception as exc:
        raise TTSError(f'Не вдалося отримати голоси Windows: {exc}')


def synthesize_windows(text: str, output_wav: str, voice_id: str = '', rate: int = 170, volume: float = 1.0) -> str:
    """Generate a WAV with Windows SAPI via pyttsx3."""
    if not text.strip():
        raise ValueError('Текст репліки порожній')
    out = Path(output_wav).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        if voice_id:
            engine.setProperty('voice', voice_id)
        engine.setProperty('rate', int(rate))
        engine.setProperty('volume', max(0.0, min(1.0, float(volume))))
        engine.save_to_file(text.strip(), str(out))
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        raise TTSError(f'Windows TTS помилка: {exc}')
    if not out.exists() or out.stat().st_size == 0:
        raise TTSError('Windows TTS не створив WAV-файл')
    return str(out)
