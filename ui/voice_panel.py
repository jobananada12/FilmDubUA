from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QPushButton,QLineEdit,QLabel,QFileDialog
from core.tts import synthesize_piper

class VoicePanel(QWidget):
    """Generate a selected dialogue line with a local Piper voice model."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.model=''
        self.out=''
        self.model_label=QLabel('Модель: не вибрана')
        self.voice=QComboBox(); self.voice.addItems(['Piper — локальний голос'])
        self.text=QLineEdit(); self.text.setPlaceholderText('Текст нової репліки...')
        self.choose=QPushButton('📁 Вибрати модель .onnx'); self.choose.clicked.connect(self.choose_model)
        self.generate=QPushButton('🎙️ Згенерувати голос'); self.generate.clicked.connect(self.generate_voice)
        self.status=QLabel('Готово')
        lay=QVBoxLayout(self); lay.addWidget(self.voice); lay.addWidget(self.text); lay.addWidget(self.choose); lay.addWidget(self.model_label); lay.addWidget(self.generate); lay.addWidget(self.status)

    def choose_model(self):
        p,_=QFileDialog.getOpenFileName(self,'Виберіть Piper voice model','','Piper model (*.onnx)')
        if p: self.model=p; self.model_label.setText(f'Модель: {p}')

    def generate_voice(self):
        if not self.model: self.status.setText('Спочатку виберіть модель .onnx'); return
        p,_=QFileDialog.getSaveFileName(self,'Зберегти озвучку','','WAV (*.wav)')
        if not p: return
        try:
            synthesize_piper(self.text.text(),self.model,p); self.status.setText(f'Готово: {p}')
        except Exception as e: self.status.setText(f'Помилка: {e}')
