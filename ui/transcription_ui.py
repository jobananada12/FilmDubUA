from pathlib import Path
import json
import tempfile
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QPushButton
from core.speech_recognition import transcribe_clip
from core.dialogue import Dialogue


class TranscriptionWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)
    def __init__(self, clip_path):
        super().__init__()
        self.clip_path = clip_path
    def run(self):
        try:
            out_dir = Path(tempfile.mkdtemp(prefix='filmdubua_transcript_'))
            self.finished.emit(transcribe_clip(self.clip_path, str(out_dir / 'transcript.json')))
        except Exception as exc:
            self.failed.emit(str(exc))


def install_transcription_button(main_window):
    """Add transcription button without replacing the existing main window code."""
    buttons = main_window.findChildren(QPushButton)
    anchor = next((b for b in buttons if 'Прибрати голоси' in b.text()), None)
    if anchor is None:
        return
    parent_layout = anchor.parentWidget().layout()
    button = QPushButton('📝 5. Розпізнати репліки вибраного кліпу', anchor.parentWidget())
    parent_layout.insertWidget(parent_layout.indexOf(anchor) + 1, button)
    worker = {'value': None}

    def failed(error):
        main_window.status.setText(f'❌ Розпізнавання: {error}')

    def done(path):
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            segments = data.get('segments', [])
            track = main_window.dialogue_editor.track
            track.items.clear()
            for seg in segments:
                start = int(float(seg.get('start', 0)) * 1000)
                end = int(float(seg.get('end', start / 1000)) * 1000)
                text = str(seg.get('text', '')).strip()
                if text:
                    track.add(Dialogue(start, end, 'Голос 1', text))
            main_window.dialogue_editor.refresh()
            main_window.status.setText(f'✅ Розпізнано {len(segments)} реплік вибраного кліпу.')
        except Exception as exc:
            failed(str(exc))

    def start():
        row = main_window.montage_list.currentRow()
        clips = main_window.montage_clips
        if not (0 <= row < len(clips)):
            main_window.status.setText('Спочатку виберіть кліп на монтажній доріжці')
            return
        clip = clips[row].get('path', '')
        if not Path(clip).exists():
            main_window.status.setText('Файл вибраного кліпу не знайдено')
            return
        if worker['value'] is not None and worker['value'].isRunning():
            return
        main_window.status.setText('⏳ AI розпізнає репліки тільки вибраного кліпу...')
        w = TranscriptionWorker(clip)
        worker['value'] = w
        w.finished.connect(done)
        w.failed.connect(failed)
        w.start()

    button.clicked.connect(start)
    main_window._transcription_button = button
    main_window._transcription_worker_holder = worker
