from pathlib import Path
import subprocess
import tempfile

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QCheckBox, QLabel, QGroupBox
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QThread, Signal

from core.canvas import VerticalCanvas
from core.voice_separation import separate_voice
from ui.reaction_widget import ReactionWidget
from ui.video_player import VideoPlayer
from ui.timeline import Timeline
from ui.dialogue_editor import DialogueEditor
from core.media import supported_video_filter


class MontageWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, input_path, start_ms, end_ms, output_path):
        super().__init__()
        self.input_path = input_path
        self.start_ms = int(start_ms)
        self.end_ms = int(end_ms)
        self.output_path = output_path

    def run(self):
        try:
            src = Path(self.input_path).resolve()
            if not src.exists():
                raise FileNotFoundError(str(src))
            if self.end_ms <= self.start_ms:
                raise ValueError('Кінець уривка має бути після початку')

            start = self.start_ms / 1000.0
            duration = (self.end_ms - self.start_ms) / 1000.0

            # Re-encode so the selected start/end are frame-accurate instead
            # of depending on the source video's keyframes.
            cmd = [
                'ffmpeg', '-y', '-ss', str(start), '-i', str(src),
                '-t', str(duration),
                '-map', '0:v:0', '-map', '0:a:0?',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', str(self.output_path)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr[-4000:] or 'FFmpeg не зміг створити основу монтажу')
            if not Path(self.output_path).exists() or Path(self.output_path).stat().st_size == 0:
                raise RuntimeError('FFmpeg не створив файл основи монтажу')

            self.finished.emit(str(self.output_path))
        except Exception as exc:
            self.failed.emit(str(exc))


class SeparationWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, input_path, start_ms, end_ms):
        super().__init__()
        self.input_path = input_path
        self.start_ms = int(start_ms)
        self.end_ms = int(end_ms)

    def run(self):
        try:
            src = Path(self.input_path).resolve()
            if not src.exists():
                raise FileNotFoundError(str(src))
            if self.end_ms <= self.start_ms:
                raise ValueError('Кінець уривка має бути після початку')

            temp_dir = Path(tempfile.mkdtemp(prefix='filmdubua_selection_'))
            audio_clip = temp_dir / 'selected_scene.wav'
            start = self.start_ms / 1000.0
            duration = (self.end_ms - self.start_ms) / 1000.0

            cmd = [
                'ffmpeg', '-y', '-ss', str(start), '-i', str(src),
                '-t', str(duration), '-vn', '-ac', '2', '-ar', '44100',
                '-c:a', 'pcm_s16le', str(audio_clip)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr[-4000:] or 'FFmpeg не зміг підготувати аудіо уривка')

            stems_dir = temp_dir / 'stems'
            background = separate_voice(str(audio_clip), str(stems_dir))
            self.finished.emit(background)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmDubUA — монтаж дубляжу')
        self.resize(1200, 820)

        self.movie_path = ''
        self.montage_path = ''
        self.background_path = ''
        self.worker = None
        self.montage_worker = None
        self.montage_temp_dir = None
        self.selection_start_ms = 0
        self.selection_end_ms = 0
        self.selection_ready = False
        self.previewing_selection = False
        self.montage_ready = False

        self.canvas = VerticalCanvas()
        self.reaction = ReactionWidget(self.canvas)
        self.reaction.hide()

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(600, 340)
        self.player = VideoPlayer(self.video_widget)
        self.timeline = Timeline()
        self.dialogue_editor = DialogueEditor()

        self.timeline.positionChanged.connect(self.player.seek)
        self.timeline.rangeChanged.connect(self.selection_changed)
        self.player.player.durationChanged.connect(self.timeline.set_duration)
        self.player.player.positionChanged.connect(self.on_position_changed)

        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        top = QHBoxLayout()
        controls = QVBoxLayout()

        add_movie = QPushButton('🎬 1. Додати фільм / сцену')
        add_movie.clicked.connect(self.add_movie)
        play = QPushButton('▶ / ⏸ Відтворити')
        play.clicked.connect(self.player.play_pause)
        preview = QPushButton('🎬 ▶ 2. Переглянути вибраний уривок')
        preview.clicked.connect(self.preview_selection)
        prepare = QPushButton('🧩 3. Зробити уривок основою монтажу')
        prepare.clicked.connect(self.prepare_montage)
        separate = QPushButton('🔇 4. Прибрати голоси з вибраного уривка AI')
        separate.clicked.connect(self.separate_selected_voice)
        add = QPushButton('👤 Додати моє відео')
        add.clicked.connect(self.add_reaction)
        circle = QCheckBox('⭕ Кругла маска')
        circle.toggled.connect(self.set_circle)

        self.selection_status = QLabel('Уривок: не вибрано')
        self.montage_status = QLabel('Монтаж: ще не підготовлений')
        self.status = QLabel('Фільм: не завантажено')

        for widget in (add_movie, play, preview, prepare, separate, add, circle,
                       self.selection_status, self.montage_status, self.status):
            controls.addWidget(widget)
        controls.addStretch()

        top.addLayout(controls, 0)
        top.addWidget(self.video_widget, 1)
        top.addWidget(self.canvas, 0)
        main.addLayout(top, 1)
        main.addWidget(self.timeline)

        dialogue_box = QGroupBox('🎙️ Нові репліки — підготовка дубляжу')
        dialogue_layout = QVBoxLayout(dialogue_box)
        dialogue_layout.addWidget(self.dialogue_editor)
        main.addWidget(dialogue_box, 0)

    def add_movie(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Виберіть фільм або сцену', '', supported_video_filter()
        )
        if not path:
            return
        self.movie_path = path
        self.montage_path = ''
        self.background_path = ''
        self.selection_ready = False
        self.montage_ready = False
        self.previewing_selection = False
        self.player.open(path)
        self.status.setText(f'Фільм: {path}')
        self.selection_status.setText('Уривок: виберіть Початок і Кінець')
        self.montage_status.setText('Монтаж: ще не підготовлений')

    def selection_changed(self, start_ms, end_ms):
        self.selection_start_ms = int(start_ms)
        self.selection_end_ms = int(end_ms)
        self.selection_ready = self.selection_end_ms > self.selection_start_ms
        self.montage_ready = False
        self.montage_path = ''
        self.background_path = ''
        self.previewing_selection = False
        self.player.player.pause()

        if self.selection_ready:
            self.selection_status.setText(
                f'🎬 Уривок: {self.format_ms(start_ms)} → {self.format_ms(end_ms)} '
                f'({(end_ms - start_ms) / 1000:.2f} с)'
            )
            self.montage_status.setText('Монтаж: натисніть «Зробити уривок основою монтажу»')
            self.status.setText('✅ Початок і кінець запамʼятовано. Експорт не виконується.')

    def preview_selection(self):
        if not self.movie_path:
            self.status.setText('Спочатку додайте фільм / сцену')
            return
        if not self.selection_ready:
            self.status.setText('Спочатку встановіть Початок і Кінець уривка')
            return

        self.previewing_selection = True
        self.player.player.setPosition(self.selection_start_ms)
        self.player.player.play()
        self.status.setText(
            f'▶ Перегляд: {self.format_ms(self.selection_start_ms)} → '
            f'{self.format_ms(self.selection_end_ms)}'
        )

    def on_position_changed(self, position_ms):
        self.timeline.update_position(position_ms)
        if self.previewing_selection and position_ms >= self.selection_end_ms:
            self.player.player.pause()
            self.player.player.setPosition(self.selection_end_ms)
            self.previewing_selection = False
            self.status.setText(
                f'✅ Перегляд завершено: {self.format_ms(self.selection_start_ms)} → '
                f'{self.format_ms(self.selection_end_ms)}'
            )

    def prepare_montage(self):
        if not self.movie_path:
            self.status.setText('Спочатку додайте фільм / сцену')
            return
        if not self.selection_ready:
            self.status.setText('Спочатку встановіть Початок і Кінець уривка')
            return
        if self.montage_worker and self.montage_worker.isRunning():
            return

        self.montage_temp_dir = Path(tempfile.mkdtemp(prefix='filmdubua_montage_'))
        output_path = self.montage_temp_dir / 'base_clip.mp4'
        self.montage_ready = False
        self.montage_path = ''
        self.status.setText('🧩 Створюю реальний файл основи монтажу через FFmpeg...')
        self.montage_worker = MontageWorker(
            self.movie_path,
            self.selection_start_ms,
            self.selection_end_ms,
            output_path,
        )
        self.montage_worker.finished.connect(self.montage_done)
        self.montage_worker.failed.connect(self.montage_failed)
        self.montage_worker.start()

    def montage_done(self, path):
        self.montage_path = path
        self.montage_ready = True
        self.montage_status.setText(
            f'🎬 Основа монтажу ГОТОВА: {self.format_ms(self.selection_start_ms)} → '
            f'{self.format_ms(self.selection_end_ms)}'
        )
        self.status.setText(
            f'✅ Реальний кліп створено: {path}. Оригінальний фільм не змінено.'
        )
        # Keep the selected clip as the active preview source so the user can
        # immediately inspect the actual montage base that was created.
        self.player.open(path)
        self.timeline.set_duration(self.selection_end_ms - self.selection_start_ms)
        self.timeline.update_position(0)

    def montage_failed(self, error):
        self.montage_ready = False
        self.montage_path = ''
        self.montage_status.setText('Монтаж: не створено')
        self.status.setText(f'❌ Не вдалося створити основу монтажу: {error}')

    def separate_selected_voice(self):
        if not self.movie_path:
            self.status.setText('Спочатку додайте фільм / сцену')
            return
        if not self.selection_ready:
            self.status.setText('Спочатку виберіть Початок і Кінець')
            return
        if not self.montage_ready or not self.montage_path:
            self.status.setText('Спочатку зробіть уривок основою монтажу')
            return
        if self.worker and self.worker.isRunning():
            return

        self.status.setText('🤖 AI: готую аудіо вибраного уривка та відділяю голоси...')
        self.worker = SeparationWorker(
            self.movie_path, self.selection_start_ms, self.selection_end_ms
        )
        self.worker.finished.connect(self.separation_done)
        self.worker.failed.connect(self.separation_failed)
        self.worker.start()

    def separation_done(self, background):
        self.background_path = background
        self.status.setText(f'✅ Фон вибраного уривка готовий: {background}')
        self.montage_status.setText(
            '🎵 Основа готова: відео + фон без оригінального вокального шару. '
            'Далі — нові репліки.'
        )

    def separation_failed(self, error):
        self.status.setText(f'❌ Не вдалося відділити голоси: {error}')

    def add_reaction(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Виберіть своє відео', '', supported_video_filter()
        )
        if not path:
            return
        self.reaction.set_video(path)
        self.reaction.setGeometry(
            int(self.canvas.width() * .28),
            int(self.canvas.height() * .60),
            int(self.canvas.width() * .42),
            int(self.canvas.height() * .30)
        )
        self.reaction.show()
        self.reaction.raise_()

    def set_circle(self, checked):
        self.reaction.set_circular(checked)

    @staticmethod
    def format_ms(ms):
        total_seconds = max(0, int(ms)) // 1000
        return f'{total_seconds // 60:02d}:{total_seconds % 60:02d}'
