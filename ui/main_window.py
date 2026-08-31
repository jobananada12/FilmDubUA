from pathlib import Path
import subprocess
import tempfile
import traceback

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox

# Existing application code remains in the repository; this helper is used by
# error handlers to present copyable diagnostics.
def show_error(parent, title, error):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(900, 600)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel('Помилка. Виділи текст і натисни Ctrl+C, щоб скопіювати його сюди:'))
    edit = QPlainTextEdit()
    edit.setPlainText(str(error))
    edit.setReadOnly(False)
    edit.selectAll()
    layout.addWidget(edit)
    buttons = QDialogButtonBox(QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()
