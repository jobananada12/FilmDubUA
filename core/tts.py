from pathlib import Path
import subprocess
import shutil
import sys
import wave

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMP_ROOT = PROJECT_ROOT / 'temp'
TTS_ROOT = TEMP_ROOT / 'tts'
MODEL_ROOT = TEMP_ROOT / 'models' / 'tts'
UKRAINIAN_MODEL = MODEL_ROOT / 'uk_UA-ukrainian_tts-medium.onnx'
UKRAINIAN_MODEL_URL = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx'
UKRAINIAN_CONFIG_URL = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx.json'

class TTSError(RuntimeError):
    pass


def ensure_temp_dirs():
    for path in (TEMP_ROOT, TTS_ROOT, MODEL_ROOT):
        path.mkdir(parents=True, exist_ok=True)
    return TEMP_ROOT


def available_engines():
    engines=['piper-uk']
    try:
        import pyttsx3
        engines.append('pyttsx3')
    except ImportError:
        pass
    return engines


def ensure_ukrainian_model() -> Path:
    ensure_temp_dirs()
    config = Path(str(UKRAINIAN_MODEL) + '.json')
    if UKRAINIAN_MODEL.exists() and config.exists():
        return UKRAINIAN_MODEL
    try:
        import urllib.request
        urllib.request.urlretrieve(UKRAINIAN_MODEL_URL, str(UKRAINIAN_MODEL))
        urllib.request.urlretrieve(UKRAINIAN_CONFIG_URL, str(config))
    except Exception as exc:
        raise TTSError(f'Не вдалося завантажити українську модель Piper: {exc}')
    if not UKRAINIAN_MODEL.exists() or UKRAINIAN_MODEL.stat().st_size < 1_000_000:
        raise TTSError('Українська модель Piper завантажилась некоректно')
    return UKRAINIAN_MODEL


def synthesize_ukrainian(text: str, output_wav: str, rate: int = 170, volume: float = 1.0) -> str:
    """Generate Ukrainian speech locally with Piper; no Windows voice is required."""
    if not text.strip():
        raise ValueError('Текст репліки порожній')
    model = ensure_ukrainian_model()
    out = Path(output_wav).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from piper import PiperVoice, SynthesisConfig
        voice = PiperVoice.load(str(model))
        # Piper length_scale: smaller = faster. Map the UI words/minute to a useful range.
        length_scale = max(0.55, min(1.55, 170.0 / max(80, min(300, rate))))
        syn_config = SynthesisConfig(length_scale=length_scale, volume=max(0.0, min(2.0, float(volume))))
        with wave.open(str(out), 'wb') as wav_file:
            voice.synthesize_wav(text.strip(), wav_file, syn_config=syn_config)
    except Exception as exc:
        raise TTSError(f'Український Piper TTS помилка: {exc}')
    if not out.exists() or out.stat().st_size == 0:
        raise TTSError('Piper не створив WAV-файл')
    return str(out)


def synthesize_piper(text: str, voice_model: str, output_wav: str, speaker: str = '') -> str:
    if not text.strip(): raise ValueError('Текст репліки порожній')
    if not Path(voice_model).exists(): raise FileNotFoundError(voice_model)
    out=Path(output_wav).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    cmd=['piper','--model',str(Path(voice_model).resolve()),'--output_file',str(out)]
    if speaker: cmd += ['--speaker', speaker]
    result=subprocess.run(cmd,input=text,encoding='utf-8',capture_output=True)
    if result.returncode != 0: raise TTSError(result.stderr.strip() or result.stdout.strip() or 'Piper failed')
    return str(out)


def windows_voices():
    try:
        import pyttsx3
        engine = pyttsx3.init(); voices=[]
        for voice in engine.getProperty('voices'):
            languages=[]
            for lang in getattr(voice, 'languages', []) or []:
                if isinstance(lang, bytes): lang=lang.decode(errors='ignore')
                languages.append(str(lang))
            voices.append((str(getattr(voice,'id','')),str(getattr(voice,'name','')),languages))
        engine.stop(); return voices
    except Exception as exc:
        raise TTSError(f'Не вдалося отримати голоси Windows: {exc}')


def synthesize_windows(text: str, output_wav: str, voice_id: str = '', rate: int = 170, volume: float = 1.0) -> str:
    """Backward-compatible Windows TTS function. Ukrainian generation is handled by Piper."""
    return synthesize_ukrainian(text, output_wav, rate=rate, volume=volume)
