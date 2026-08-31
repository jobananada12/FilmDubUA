from pathlib import Path
import tempfile

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QSpinBox, QPushButton, QLabel, QComboBox
from core.dialogue import Dialogue, DialogueTrack
from core.tts import windows_voices, synthesize_windows, TTSError
from core.dubbing import mix_dialogue, DubbingError

class DialogueEditor(QWidget):
    """Dialogue editor with local Windows SAPI/pyttsx3 voice generation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.track = DialogueTrack()
        self.list = QListWidget()
        self.character = QLineEdit('Персонаж 1')
        self.text = QLineEdit()
        self.start = QSpinBox(); self.start.setRange(0, 24*60*60*1000); self.start.setSuffix(' ms')
        self.end = QSpinBox(); self.end.setRange(0, 24*60*60*1000); self.end.setValue(3000); self.end.setSuffix(' ms')
        self.voice = QComboBox()
        self.rate = QSpinBox(); self.rate.setRange(80, 300); self.rate.setValue(170); self.rate.setSuffix(' сл/хв')
        add = QPushButton('➕ Додати репліку'); remove = QPushButton('🗑 Видалити')
        generate = QPushButton('🔊 Згенерувати українську озвучку')
        mix = QPushButton('🎬 Зібрати дубльований кліп')
        generate.clicked.connect(self.generate_voice)
        mix.clicked.connect(self.mix_current_dialogue)
        add.clicked.connect(self.add_dialogue); remove.clicked.connect(self.remove_dialogue)
        for w in (self.character, self.text, self.start, self.end):
            w.editingFinished.connect(self.apply_current)
        self.list.currentRowChanged.connect(self.load_current)
        self.voice.addItem('Системний голос Windows', '')
        try:
            for voice_id, name, languages in windows_voices():
                marker = ' 🇺🇦' if any('uk' in x.lower() or '041D' in x for x in languages) or 'ukrain' in name.lower() else ''
                self.voice.addItem(f'{name}{marker}', voice_id)
        except Exception:
            pass
        controls=QHBoxLayout()
        controls.addWidget(QLabel('Персонаж')); controls.addWidget(self.character)
        controls.addWidget(QLabel('Текст')); controls.addWidget(self.text, 1)
        controls.addWidget(QLabel('Початок')); controls.addWidget(self.start)
        controls.addWidget(QLabel('Кінець')); controls.addWidget(self.end)
        controls.addWidget(add); controls.addWidget(remove)
        voice_row=QHBoxLayout()
        voice_row.addWidget(QLabel('Голос')); voice_row.addWidget(self.voice, 1)
        voice_row.addWidget(QLabel('Швидкість')); voice_row.addWidget(self.rate)
        voice_row.addWidget(generate)
        voice_row.addWidget(mix)
        layout=QVBoxLayout(self); layout.addLayout(controls); layout.addLayout(voice_row); layout.addWidget(self.list)

    def refresh(self):
        self.list.clear()
        for d in self.track.items:
            ready = ' 🔊' if getattr(d, 'audio_path', '') and Path(d.audio_path).exists() else ''
            self.list.addItem(f'[{d.start_ms/1000:.2f}s–{d.end_ms/1000:.2f}s] {d.character}: {d.text}{ready}')

    def add_dialogue(self):
        self.track.add(Dialogue(self.start.value(), self.end.value(), self.character.text(), self.text.text()))
        self.refresh(); self.list.setCurrentRow(len(self.track.items)-1)

    def remove_dialogue(self):
        self.track.remove(self.list.currentRow()); self.refresh()

    def load_current(self, row):
        if 0 <= row < len(self.track.items):
            d=self.track.items[row]
            for w,v in ((self.character,d.character),(self.text,d.text),(self.start,d.start_ms),(self.end,d.end_ms)):
                if hasattr(w,'setText'): w.setText(v)
                else: w.setValue(v)

    def apply_current(self):
        row=self.list.currentRow()
        if row < 0: return
        self.track.update(row, character=self.character.text(), text=self.text.text(), start_ms=self.start.value(), end_ms=self.end.value())
        self.refresh(); self.list.setCurrentRow(row)

    def generate_voice(self):
        row = self.list.currentRow()
        if row < 0:
            self.status_message('Спочатку виберіть репліку')
            return
        d = self.track.items[row]
        if not d.text.strip():
            self.status_message('У репліці немає тексту')
            return
        if d.end_ms <= d.start_ms:
            self.status_message('Кінець репліки має бути після початку')
            return
        try:
            out_dir = Path(tempfile.mkdtemp(prefix='filmdubua_tts_'))
            out = out_dir / f'dialogue_{row+1:03d}.wav'
            voice_id = self.voice.currentData() or ''
            synthesize_windows(d.text, str(out), voice_id=voice_id, rate=self.rate.value(), volume=d.volume)
            d.audio_path = str(out)
            self.refresh(); self.list.setCurrentRow(row)
            self.status_message(f'✅ Озвучку створено: {out}')
        except Exception as exc:
            self.status_message(f'❌ TTS: {exc}')

    def mix_current_dialogue(self):
        row = self.list.currentRow()
        if row < 0:
            self.status_message('Спочатку виберіть репліку')
            return
        d = self.track.items[row]
        if not getattr(d, 'audio_path', '') or not Path(d.audio_path).exists():
            self.status_message('Спочатку згенеруйте озвучку цієї репліки')
            return

        main = self.window()
        clips = getattr(main, 'montage_clips', [])
        selected_row = getattr(main, 'montage_list', None)
        if selected_row is not None:
            selected_row = selected_row.currentRow()
        else:
            selected_row = -1
        if not (0 <= selected_row < len(clips)):
            self.status_message('Спочатку виберіть кліп на монтажній доріжці')
            return
        clip = clips[selected_row]
        video_path = clip.get('path', '')
        background_path = getattr(main, 'background_path', '')
        if not background_path or not Path(background_path).exists():
            self.status_message('Спочатку натисніть «Прибрати голоси з вибраного уривка AI»')
            return
        clip_start = int(clip.get('start_ms', 0))
        relative_start = max(0, int(d.start_ms) - clip_start)
        out_dir = Path(tempfile.mkdtemp(prefix='filmdubua_dubbed_'))
        out = out_dir / f'dubbed_clip_{selected_row+1:03d}_dialogue_{row+1:03d}.mp4'
        try:
            result = mix_dialogue(video_path, background_path, d.audio_path, str(out), relative_start, d.volume)
            self.status_message(f'✅ Готовий дубльований кліп: {result}')
            if hasattr(main, 'player'):
                main.player.open(result)
            if hasattr(main, 'status'):
                main.status.setText(f'🎬 Українську репліку накладено на кліп {selected_row + 1}')
        except (DubbingError, Exception) as exc:
            self.status_message(f'❌ Дубляж: {exc}')

    def status_message(self, text):
        parent = self.window()
        if hasattr(parent, 'status'):
            parent.status.setText(text)
