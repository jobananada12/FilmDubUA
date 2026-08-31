import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.transcription_ui import install_transcription_button


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    install_transcription_button(win)
    win.show()
    sys.exit(app.exec())
