from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QDoubleSpinBox,QPushButton,QLabel,QFileDialog
from core.audio_mixer import mix_audio

class MixerPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.background=''; self.dialogues=[]
        self.bg=QDoubleSpinBox(); self.bg.setRange(0,2); self.bg.setSingleStep(.05); self.bg.setValue(.25)
        self.dv=QDoubleSpinBox(); self.dv.setRange(0,3); self.dv.setSingleStep(.05); self.dv.setValue(1.0)
        self.status=QLabel('Фон і репліки ще не вибрані')
        b1=QPushButton('🎵 Вибрати фон без голосів'); b1.clicked.connect(self.choose_background)
        b2=QPushButton('🗣️ Додати WAV репліку'); b2.clicked.connect(self.add_dialogue)
        b3=QPushButton('🎚️ Змішати аудіо'); b3.clicked.connect(self.mix)
        lay=QVBoxLayout(self); lay.addWidget(b1); lay.addWidget(b2); lay.addWidget(QLabel('Гучність фону')); lay.addWidget(self.bg); lay.addWidget(QLabel('Гучність дубляжу')); lay.addWidget(self.dv); lay.addWidget(b3); lay.addWidget(self.status)
    def choose_background(self):
        p,_=QFileDialog.getOpenFileName(self,'Фон без голосів','','Audio (*.wav *.mp3 *.flac)')
        if p: self.background=p; self.status.setText('Фон вибрано')
    def add_dialogue(self):
        p,_=QFileDialog.getOpenFileName(self,'WAV репліка','','WAV (*.wav)')
        if p:
            self.dialogues.append((p,0)); self.status.setText(f'Реплік: {len(self.dialogues)} (поки старт 0 мс)')
    def mix(self):
        if not self.background or not self.dialogues: self.status.setText('Потрібні фон і хоча б одна репліка'); return
        p,_=QFileDialog.getSaveFileName(self,'Зберегти мікс','','WAV (*.wav)')
        if not p: return
        try: mix_audio(self.background,self.dialogues,p,self.bg.value(),self.dv.value()); self.status.setText(f'Готово: {p}')
        except Exception as e: self.status.setText(f'Помилка: {e}')
