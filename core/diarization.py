"""Speaker diarization helpers for selected FilmDubUA clips.

Uses pyannote.audio when installed. The Hugging Face token is read from
HF_TOKEN and is never stored in the project.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class DiarizationError(RuntimeError):
    pass


def diarize_audio(audio_path: str | Path, min_speakers: int = 1, max_speakers: int = 8) -> list[dict[str, Any]]:
    """Return [{start_ms,end_ms,speaker}] for the selected clip."""
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise DiarizationError(
            "Не задано HF_TOKEN. Для speaker diarization потрібен токен Hugging Face "
            "з доступом до моделі pyannote. Встановіть його як змінну середовища HF_TOKEN."
        )
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise DiarizationError("Не встановлено pyannote.audio. Виконайте: python -m pip install -U pyannote.audio") from exc

    path = Path(audio_path).resolve()
    if not path.exists():
        raise DiarizationError(f"Аудіо не знайдено: {path}")
    try:
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=token)
        diarization = pipeline(str(path), min_speakers=min_speakers, max_speakers=max_speakers)
    except Exception as exc:
        raise DiarizationError(f"Не вдалося виконати speaker diarization: {exc}") from exc

    result: list[dict[str, Any]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        result.append({"start_ms": round(turn.start * 1000), "end_ms": round(turn.end * 1000), "speaker": str(speaker)})
    return result
