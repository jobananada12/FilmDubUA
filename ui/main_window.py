from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QCheckBox, QLabel
from PySide6.QtCore import Qt
from core.canvas import VerticalCanvas
from ui.reaction_widget import ReactionWidget
from core.media import supported_video_filter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmDubUA — Stage 3')
        self.resize(1000, 720)
        self.canvas = VerticalCanvas()
        self.reaction = ReactionWidget(self.canvas)
        self.reaction.hide()
        self._build_ui()

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        controls = QVBoxLayout()
        add = QPushButton('👤 Додати моє відео')
        add.clicked.connect(self.add_reaction)
        circle = QCheckBox('⭕ Кругла маска')
        circle.toggled.connect(self.set_circle)
        self.status = QLabel('Reaction: не завантажено')
        controls.addWidget(add); controls.addWidget(circle); controls.addWidget(self.status); controls.addStretch()
        layout.addLayout(controls, 0); layout.addWidget(self.canvas, 1)

    def add_reaction(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Виберіть своє відео', '', supported_video_filter())
        if not path:
            return
        self.reaction.set_video(path)
        self.reaction.setParent(self.canvas)
        self.reaction.setGeometry(int(self.canvas.width()*.28), int(self.canvas.height()*.60), int(self.canvas.width()*.42), int(self.canvas.height()*.30))
        self.reaction.show(); self.reaction.raise_()
        self.status.setText(f'Reaction: {path}')

    def set_circle(self, checked):
        self.reaction.set_circular(checked)
