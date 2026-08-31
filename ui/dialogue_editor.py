from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QSpinBox, QPushButton, QLabel
from core.dialogue import Dialogue, DialogueTrack

class DialogueEditor(QWidget):
    """Simple dialogue editor: character, text and exact start/end timing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.track = DialogueTrack()
        self.list = QListWidget()
        self.character = QLineEdit('Персонаж 1')
        self.text = QLineEdit()
        self.start = QSpinBox(); self.start.setRange(0, 24*60*60*1000); self.start.setSuffix(' ms')
        self.end = QSpinBox(); self.end.setRange(0, 24*60*60*1000); self.end.setValue(3000); self.end.setSuffix(' ms')
        add = QPushButton('➕ Додати репліку'); remove = QPushButton('🗑 Видалити')
        add.clicked.connect(self.add_dialogue); remove.clicked.connect(self.remove_dialogue)
        for w in (self.character, self.text, self.start, self.end):
            w.editingFinished.connect(self.apply_current)
        self.list.currentRowChanged.connect(self.load_current)
        controls=QHBoxLayout(); controls.addWidget(QLabel('Персонаж')); controls.addWidget(self.character); controls.addWidget(QLabel('Текст')); controls.addWidget(self.text); controls.addWidget(QLabel('Початок')); controls.addWidget(self.start); controls.addWidget(QLabel('Кінець')); controls.addWidget(self.end); controls.addWidget(add); controls.addWidget(remove)
        layout=QVBoxLayout(self); layout.addLayout(controls); layout.addWidget(self.list)

    def refresh(self):
        self.list.clear()
        for d in self.track.items:
            self.list.addItem(f'[{d.start_ms/1000:.2f}s–{d.end_ms/1000:.2f}s] {d.character}: {d.text}')

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
