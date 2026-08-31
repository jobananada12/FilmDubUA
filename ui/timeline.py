from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QSlider, QLabel, QHBoxLayout, QPushButton, QSpinBox

class Timeline(QWidget):
    positionChanged = Signal(int)
    rangeChanged = Signal(int, int)
    def __init__(self, parent=None):
        super().__init__(parent); self.duration=0; self.start_ms=0; self.end_ms=0
        self.slider=QSlider(Qt.Horizontal); self.slider.setRange(0,0); self.slider.valueChanged.connect(self.positionChanged)
        self.time=QLabel('00:00 / 00:00')
        self.start=QSpinBox(); self.start.setRange(0,0); self.start.setSuffix(' ms')
        self.end=QSpinBox(); self.end.setRange(0,0); self.end.setSuffix(' ms')
        self.set_start=QPushButton('✂️ Початок'); self.set_end=QPushButton('✂️ Кінець')
        self.set_start.clicked.connect(self.mark_start); self.set_end.clicked.connect(self.mark_end)
        layout=QHBoxLayout(self); layout.addWidget(self.slider,1); layout.addWidget(self.time); layout.addWidget(self.set_start); layout.addWidget(self.start); layout.addWidget(self.set_end); layout.addWidget(self.end)
    def set_duration(self,ms):
        self.duration=max(0,int(ms)); self.slider.setRange(0,self.duration); self.start.setRange(0,self.duration); self.end.setRange(0,self.duration); self.start_ms=0; self.end_ms=self.duration; self.start.setValue(0); self.end.setValue(self.duration); self.update_position(0)
    def update_position(self,ms):
        ms=max(0,min(int(ms),self.duration))
        if self.slider.value()!=ms: self.slider.blockSignals(True); self.slider.setValue(ms); self.slider.blockSignals(False)
        s=ms//1000; d=self.duration//1000; self.time.setText(f'{s//60:02d}:{s%60:02d} / {d//60:02d}:{d%60:02d}')
    def mark_start(self):
        self.start_ms=self.slider.value(); self.start.setValue(self.start_ms); self.end_ms=max(self.end_ms,self.start_ms+1); self.end.setValue(self.end_ms); self.rangeChanged.emit(self.start_ms,self.end_ms)
    def mark_end(self):
        self.end_ms=self.slider.value(); self.end.setValue(self.end_ms); self.start_ms=min(self.start_ms,max(0,self.end_ms-1)); self.start.setValue(self.start_ms); self.rangeChanged.emit(self.start_ms,self.end_ms)
