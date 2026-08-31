from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QSlider, QLabel, QHBoxLayout

class Timeline(QWidget):
    positionChanged = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self.positionChanged)
        self.time = QLabel('00:00 / 00:00')
        layout = QHBoxLayout(self)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.time)

    def set_duration(self, ms):
        self.duration = max(0, int(ms))
        self.slider.setRange(0, self.duration)
        self.update_position(0)

    def update_position(self, ms):
        ms = max(0, min(int(ms), self.duration))
        if self.slider.value() != ms:
            self.slider.blockSignals(True); self.slider.setValue(ms); self.slider.blockSignals(False)
        def fmt(v):
            s=v//1000; return f'{s//60:02d}:{s%60:02d}'
        self.time.setText(f'{fmt(ms)} / {fmt(self.duration)}')
