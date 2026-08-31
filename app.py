import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QFileDialog, QMessageBox
from PySide6.QtMultimediaWidgets import QVideoWidget
from ui.video_player import VideoPlayer
from ui.timeline import Timeline
from ui.dialogue_editor import DialogueEditor
from ui.voice_panel import VoicePanel
from ui.mixer_panel import MixerPanel
from ui.reaction_widget import ReactionWidget
from core.media import supported_video_filter
from core.vertical_export import export_vertical

class FilmDubUA(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('FilmDubUA Studio'); self.resize(1280, 800); self.video=''; self._build()
    def _build(self):
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root)
        bar=QHBoxLayout()
        open_btn=QPushButton('🎬 Додати фільм'); open_btn.clicked.connect(self.open_video)
        self.play_btn=QPushButton('▶️ Play'); self.play_btn.clicked.connect(self.toggle_play)
        reaction_btn=QPushButton('👤 Додати моє відео'); reaction_btn.clicked.connect(self.open_reaction)
        export_btn=QPushButton('📱 Експорт 9:16'); export_btn.clicked.connect(self.export)
        for b in (open_btn,self.play_btn,reaction_btn,export_btn): bar.addWidget(b)
        bar.addStretch(); self.status=QLabel('Готово'); bar.addWidget(self.status); main.addLayout(bar)
        top=QHBoxLayout(); self.video_widget=QVideoWidget(); self.video_widget.setMinimumSize(700,400); self.player=VideoPlayer(self.video_widget); top.addWidget(self.video_widget,3)
        self.reaction=ReactionWidget(); self.reaction.setMinimumSize(320,570); top.addWidget(self.reaction,1); main.addLayout(top,1)
        self.timeline=Timeline(); self.timeline.positionChanged.connect(self.player.seek); self.player.player.durationChanged.connect(self.timeline.set_duration); self.player.player.positionChanged.connect(self.timeline.update_position); self.player.player.playbackStateChanged.connect(self.update_play_button); main.addWidget(self.timeline)
        tabs=QTabWidget(); tabs.addTab(DialogueEditor(),'🗣️ Репліки'); tabs.addTab(VoicePanel(),'🎙️ Озвучка'); tabs.addTab(MixerPanel(),'🎚️ Мікшер'); main.addWidget(tabs)
    def open_video(self):
        p,_=QFileDialog.getOpenFileName(self,'Виберіть фільм або сцену','',supported_video_filter())
        if p: self.video=p; self.player.open(p); self.status.setText('Фільм завантажено')
    def toggle_play(self):
        if not self.video: return
        self.player.play_pause()
    def update_play_button(self, state):
        self.play_btn.setText('⏸️ Pause' if self.player.player.isPlaying() else '▶️ Play')
    def open_reaction(self):
        p,_=QFileDialog.getOpenFileName(self,'Виберіть ваше відео','','Video (*.mp4 *.mov *.mkv *.webm)')
        if p: self.reaction.set_video(p); self.status.setText('Reaction-відео додано')
    def export(self):
        if not self.video: QMessageBox.warning(self,'FilmDubUA','Спочатку додайте відео.'); return
        p,_=QFileDialog.getSaveFileName(self,'Експорт готового MP4','','MP4 (*.mp4)')
        if not p: return
        try: export_vertical(self.video,p); self.status.setText(f'Експортовано: {p}')
        except Exception as e: QMessageBox.critical(self,'Помилка експорту',str(e))

if __name__=='__main__':
    app=QApplication(sys.argv); win=FilmDubUA(); win.show(); sys.exit(app.exec())
