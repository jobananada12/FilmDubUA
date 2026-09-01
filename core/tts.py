from pathlib import Path
import subprocess
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

VOICE_PROFILES = {
    'male': {'label': 'Чоловічий', 'pitch': -2.0, 'rate': 0.95},
    'female': {'label': 'Жіночий', 'pitch': 2.5, 'rate': 1.00},
    'young': {'label': 'Молодий', 'pitch': 4.0, 'rate': 1.10},
    'deep': {'label': 'Низький', 'pitch': -4.0, 'rate': 0.90},
    'neutral': {'label': 'Нейтральний', 'pitch': 0.0, 'rate': 1.00},
}

def ensure_temp_dirs():
    for path in (TEMP_ROOT, TTS_ROOT, MODEL_ROOT): path.mkdir(parents=True, exist_ok=True)
    return TEMP_ROOT

def available_engines():
    engines = ['piper-uk']
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

def _apply_pitch(src: Path, dst: Path, semitones: float) -> None:
    """Change pitch while keeping the original duration.

    Do not use `sample_rate` as an expression variable in `asetrate`:
    FFmpeg 8.x does not accept it there. Read the actual WAV sample rate
    and calculate the target rate in Python instead.
    """
    if abs(semitones) < 0.01:
        if src != dst:
            dst.write_bytes(src.read_bytes())
        return

    try:
        with wave.open(str(src), 'rb') as wav_file:
            source_rate = wav_file.getframerate()
    except (OSError, wave.Error) as exc:
        raise TTSError(f'Не вдалося прочитати частоту WAV перед зміною тембру: {exc}')

    factor = 2.0 ** (float(semitones) / 12.0)
    target_rate = max(8000, min(192000, int(round(source_rate * factor))))
    tempo = 1.0 / factor

    # asetrate changes pitch and duration; atempo restores the duration.
    # Both values are concrete numbers, so this works with FFmpeg 8.x.
    filt = f'asetrate={target_rate},aresample={source_rate},atempo={tempo:.8f}'
    cmd = [
        'ffmpeg', '-y', '-i', str(src),
        '-filter:a', filt,
        '-c:a', 'pcm_s16le', str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise TTSError(proc.stderr[-3000:] or 'Не вдалося змінити тембр голосу')


def synthesize_ukrainian(text: str, output_wav: str, rate: int = 170, volume: float = 1.0, profile: str = 'neutral') -> str:
    if not text.strip():
        raise ValueError('Текст репліки порожній')
    model = ensure_ukrainian_model()
    out = Path(output_wav).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    p = VOICE_PROFILES.get(profile, VOICE_PROFILES['neutral'])
    effective_rate = int(max(80, min(300, rate * p['rate'])))
    try:
        from piper import PiperVoice, SynthesisConfig
        voice = PiperVoice.load(str(model))
        length_scale = max(0.55, min(1.55, 170.0 / effective_rate))
        syn_config = SynthesisConfig(
            length_scale=length_scale,
            volume=max(0.0, min(2.0, float(volume))),
        )
        raw = out.with_name(out.stem + '_raw.wav')
        with wave.open(str(raw), 'wb') as wav_file:
            voice.synthesize_wav(text.strip(), wav_file, syn_config=syn_config)
        _apply_pitch(raw, out, float(p['pitch']))
        try:
            raw.unlink()
        except OSError:
            pass
    except Exception as exc:
        raise TTSError(f'Український Piper TTS помилка: {exc}')
    if not out.exists() or out.stat().st_size == 0:
        raise TTSError('Piper не створив WAV-файл')
    return str(out)


def synthesize_piper(text: str, voice_model: str, output_wav: str, speaker: str = '') -> str:
    if not text.strip():
        raise ValueError('Текст репліки порожній')
    if not Path(voice_model).exists():
        raise FileNotFoundError(voice_model)
    out = Path(output_wav).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['piper', '--model', str(Path(voice_model).resolve()), '--output_file', str(out)]
    if speaker:
        cmd += ['--speaker', speaker]
    result = subprocess.run(cmd, input=text, encoding='utf-8', capture_output=True)
    if result.returncode != 0:
        raise TTSError(result.stderr.strip() or result.stdout.strip() or 'Piper failed')
    return str(out)


def windows_voices():
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
    return synthesize_ukrainian(text, output_wav, rate=rate, volume=volume)
