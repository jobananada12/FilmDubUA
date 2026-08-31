from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

class VideoPlayer:
    """Small Qt multimedia player used by FilmDubUA."""
    def __init__(self, video_widget: QVideoWidget):
        self.widget = video_widget
        self.audio = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(video_widget)

    def open(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))

    def play_pause(self):
        if self.player.isPlaying():
            self.player.pause()
        else:
            self.player.play()

    def seek(self, position_ms: int):
        self.player.setPosition(max(0, position_ms))
