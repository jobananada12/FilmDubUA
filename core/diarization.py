"""Speaker diarization helpers for selected FilmDubUA clips."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any

class DiarizationError(RuntimeError): pass


def diarize_audio(audio_path: str | Path, min_speakers: int = 1, max_speakers: int = 8) -> list[dict[str, Any]]:
    """Return [{start_ms,end_ms,speaker}] using pyannote Community-1."""
    token=os.getenv('HF_TOKEN','').strip()
    if not token:
        raise DiarizationError('Не задано HF_TOKEN. Встановіть токен Hugging Face у змінній середовища HF_TOKEN.')
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise DiarizationError('Не встановлено pyannote.audio. Виконайте: python -m pip install -U pyannote.audio') from exc
    path=Path(audio_path).resolve()
    if not path.exists(): raise DiarizationError(f'Аудіо не знайдено: {path}')
    try:
        pipeline=Pipeline.from_pretrained('pyannote/speaker-diarization-community-1', token=token)
        diarization=pipeline(str(path))
    except Exception as exc:
        raise DiarizationError(f'Не вдалося виконати speaker diarization: {exc}') from exc
    result=[]
    annotation=getattr(diarization,'speaker_diarization',diarization)
    try:
        tracks=annotation.itertracks(yield_label=True)
    except AttributeError:
        tracks=diarization.itertracks(yield_label=True)
    for turn,_,speaker in tracks:
        result.append({'start_ms':round(turn.start*1000),'end_ms':round(turn.end*1000),'speaker':str(speaker)})
    return result
