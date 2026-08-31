from pathlib import Path

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v'}


def is_video_file(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def supported_video_filter() -> str:
    return 'Video (*.mp4 *.mkv *.mov *.avi *.webm *.m4v)'
