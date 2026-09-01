"""Speaker diarization helpers for selected FilmDubUA clips."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class DiarizationError(RuntimeError):
    pass


def _get_hf_token() -> str:
    """Get the Hugging Face token from env/.env or the HF CLI cache."""
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except Exception:
        pass

    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        return token

    try:
        from huggingface_hub import get_token
        token = (get_token() or "").strip()
    except Exception:
        token = ""
    return token


def diarize_audio(
    audio_path: str | Path,
    min_speakers: int = 1,
    max_speakers: int = 8,
) -> list[dict[str, Any]]:
    """Return [{start_ms,end_ms,speaker}] using pyannote Community-1."""
    token = _get_hf_token()
    if not token:
        raise DiarizationError(
            "Не знайдено Hugging Face токен. "
            "Встановіть HF_TOKEN або виконайте `hf auth login`."
        )

    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise DiarizationError(
            "Не встановлено pyannote.audio. Виконайте: "
            "python -m pip install -U pyannote.audio"
        ) from exc

    path = Path(audio_path).resolve()
    if not path.exists():
        raise DiarizationError(f"Аудіо не знайдено: {path}")

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1",
            token=token,
        )
        if pipeline is None:
            raise RuntimeError("Hugging Face не повернув pipeline")
        diarization = pipeline(
            str(path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
    except Exception as exc:
        message = str(exc).strip() or repr(exc)
        raise DiarizationError(
            "Не вдалося запустити speaker diarization: " + message
        ) from exc

    annotation = getattr(diarization, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = getattr(diarization, "speaker_diarization", diarization)

    try:
        tracks = annotation.itertracks(yield_label=True)
    except AttributeError:
        try:
            tracks = diarization.itertracks(yield_label=True)
        except AttributeError as exc:
            raise DiarizationError(
                "pyannote повернув результат у непідтримуваному форматі."
            ) from exc

    result: list[dict[str, Any]] = []
    for turn, _, speaker in tracks:
        result.append(
            {
                "start_ms": round(turn.start * 1000),
                "end_ms": round(turn.end * 1000),
                "speaker": str(speaker),
            }
        )
    return result
