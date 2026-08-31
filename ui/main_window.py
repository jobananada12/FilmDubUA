from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QCheckBox, QLabel
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QThread, Signal
from core.canvas import VerticalCanvas
from ui.reaction_widget import ReactionWidget
from ui.video_player import VideoPlayer
from ui.timeline import Timeline
from core.media import supported_video_filter
from core.voice_separation import separate_voice


class SeparationWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, input_path):
        super().__init__()
        self.input_path = input_path

    def run(self):
        try:
            output = Path(self.input_path).parent / "filmdubua_stems"
            self.finished.emit(separate_voice(self.input_path, str(output)))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmDubUA — Stage 5')
        self.resize(1100, 760)
        self.movie_path = ''
        self.background_path = ''
        self.worker = None
        self.selection_start_ms = 0
        self.selection_end_ms = 0
        self.previewing_selection = False

        self.canvas = VerticalCanvas()
        self.reaction = ReactionWidget(self.canvas)
        self.reaction.hide()
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(600, 340)
        self.player = VideoPlayer(self.video_widget)
        self.timeline = Timeline()

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

        add_movie = QPushButton('🎬 Додати фільм / сцену')
        add_movie.clicked.connect(self.add_movie)
        play = QPushButton('▶ / ⏸ Відтворити')
        play.clicked.connect(self.player.play_pause)
        preview = QPushButton('🎬 ▶ Переглянути вибраний уривок')
        preview.clicked.connect(self.preview_selection)
        separate = QPushButton('🤖 Прибрати голоси AI')
        separate.clicked.connect(self.separate_movie_voice)
        add = QPushButton('👤 Додати моє відео')
        add.clicked.connect(self.add_reaction)
        circle = QCheckBox('⭕ Кругла маска')
        circle.toggled.connect(self.set_circle)

        self.selection_status = QLabel('Уривок: не вибрано')
        self.status = QLabel('Фільм: не завантажено')

        controls.addWidget(add_movie)
        controls.addWidget(play)
        controls.addWidget(preview)
        controls.addWidget(separate)
        controls.addWidget(add)
        controls.addWidget(circle)
        controls.addWidget(self.selection_status)
        controls.addWidget(self.status)
        controls.addStretch()

        top.addLayout(controls, 0)
        top.addWidget(self.video_widget, 1)
        top.addWidget(self.canvas, 0)
        main.addLayout(top, 1)
        main.addWidget(self.timeline)

    def add_movie(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Виберіть фільм або сцену',
            '',
            supported_video_filter()
        )
        if path:
            self.movie_path = path
            self.selection_start_ms = 0
            self.selection_end_ms = 0
            self.previewing_selection = False
            self.player.open(path)
            self.status.setText(f'Фільм: {path}')
            self.selection_status.setText('Уривок: виберіть Початок і Кінець')

    def selection_changed(self, start_ms, end_ms):
        self.selection_start_ms = int(start_ms)
        self.selection_end_ms = int(end_ms)
        self.previewing_selection = False
        self.player.player.pause()
        self.selection_status.setText(
            f'🎬 Уривок: {self.format_ms(start_ms)} → {self.format_ms(end_ms)} '
            f'({(end_ms - start_ms) / 1000:.2f} с)'
        )
        self.status.setText('✅ Вибраний уривок став основою монтажу. Експорт не виконується.')

    def preview_selection(self):
        if not self.movie_path:
            self.status.setText('Спочатку додайте фільм / сцену')
            return
        if self.selection_end_ms <= self.selection_start_ms:
            self.status.setText('Спочатку встановіть Початок і Кінець уривка')
            return

        self.previewing_selection = True
        self.player.player.setPosition(self.selection_start_ms)
        self.player.player.play()
        self.status.setText(
            f'▶ Перегляд уривка: {self.format_ms(self.selection_start_ms)} → '
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

    @staticmethod
    def format_ms(ms):
        total_seconds = max(0, int(ms)) // 1000
        return f'{total_seconds // 60:02d}:{total_seconds % 60:02d}'

    def separate_movie_voice(self):
        if not self.movie_path:
            self.status.setText('Спочатку додайте фільм / сцену')
            return
        if self.worker and self.worker.isRunning():
            return
        self.status.setText('🤖 AI: розділяю голоси та фон...')
        self.worker = SeparationWorker(self.movie_path)
        self.worker.finished.connect(self.separation_done)
        self.worker.failed.connect(lambda e: self.status.setText(f'❌ Помилка: {e}'))
        self.worker.start()

    def separation_done(self, background):
        self.background_path = background
        self.status.setText(f'✅ Голоси прибрано. Фон: {background}')

    def add_reaction(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Виберіть своє відео',
            '',
            supported_video_filter()
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
