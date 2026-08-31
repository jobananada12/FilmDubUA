import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QLineEdit, QTextEdit, QComboBox, QSlider, QMessageBox,
    QSplitter, QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget


class ClipTimeline(QWidget):
    changed = Signal()
    selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self.clips = []
        self.duration = 60000
        self.current = 0
        self.drag = None
        self.setMouseTracking(True)

    def set_duration(self, ms):
        self.duration = max(1, ms)
        self.update()

    def set_current(self, ms):
        self.current = ms
        self.update()

    def set_clips(self, clips):
        self.clips = clips
        self.update()

    def x_for(self, ms):
        left, right = 55, self.width() - 20
        return left + (right-left) * ms / self.duration

    def ms_for(self, x):
        left, right = 55, self.width() - 20
        return max(0, min(self.duration, int((x-left) / max(1, right-left) * self.duration)))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#15171b'))
        left = 55
        y = 55
        w = max(1, self.width()-75)
        p.setPen(QPen(QColor('#777'), 1))
        for i in range(11):
            x = left + w*i/10
            p.drawLine(int(x), 25, int(x), 155)
            sec = self.duration*i/10/1000
            p.drawText(int(x)-18, 18, f'{sec:.1f}s')
        for i, c in enumerate(self.clips):
            x1, x2 = self.x_for(c['start']), self.x_for(c['end'])
            rect = QRectF(x1, y, max(20, x2-x1), 70)
            selected = i == getattr(self, 'selected_index', -1)
            p.setBrush(QBrush(QColor('#3b82f6') if selected else QColor('#2563eb')))
            p.setPen(QPen(QColor('#93c5fd') if selected else QColor('#60a5fa'), 2))
            p.drawRoundedRect(rect, 6, 6)
            p.setPen(Qt.white)
            text = c['text'].replace('\n', ' ')
            p.drawText(rect.adjusted(8, 5, -8, -5), Qt.AlignVCenter, text[:42])
            p.setPen(QPen(QColor('#dbeafe'), 4))
            p.drawLine(int(x1), 57, int(x1), 123)
            p.drawLine(int(x2), 57, int(x2), 123)
        px = self.x_for(self.current)
        p.setPen(QPen(QColor('#ef4444'), 2))
        p.drawLine(int(px), 20, int(px), 165)
        p.setBrush(QBrush(QColor('#ef4444')))
        p.drawEllipse(int(px)-5, 15, 10, 10)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        for i, c in enumerate(self.clips):
            x1, x2 = self.x_for(c['start']), self.x_for(c['end'])
            if abs(e.position().x()-x1) < 12:
                self.drag = ('start', i); self.selected_index = i; self.selected.emit(i); self.update(); return
            if abs(e.position().x()-x2) < 12:
                self.drag = ('end', i); self.selected_index = i; self.selected.emit(i); self.update(); return
            if x1 <= e.position().x() <= x2 and 55 <= e.position().y() <= 130:
                self.selected_index = i; self.selected.emit(i); self.update(); return
        self.current = self.ms_for(e.position().x()); self.changed.emit(); self.update()

    def mouseMoveEvent(self, e):
        if not self.drag:
            return
        kind, i = self.drag
        value = self.ms_for(e.position().x())
        c = self.clips[i]
        if kind == 'start': c['start'] = min(value, c['end']-100)
        else: c['end'] = max(value, c['start']+100)
        self.changed.emit(); self.update()

    def mouseReleaseEvent(self, e):
        self.drag = None


class FilmDubUA(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmDubUA — Mini CapCut для озвучки')
        self.resize(1280, 820)
        self.video_path = ''
        self.clips = []
        self.selected_index = -1
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget()
        self.player.setVideoOutput(self.video)
        self.timeline = ClipTimeline()
        self.timeline.selected.connect(self.select_clip)
        self.timeline.changed.connect(self.timeline_changed)
        self.build_ui()
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        main = QVBoxLayout(root)
        bar = QHBoxLayout()
        open_btn = QPushButton('🎬 Відкрити відео'); open_btn.clicked.connect(self.open_video)
        add_btn = QPushButton('+ Репліка'); add_btn.clicked.connect(self.add_clip)
        del_btn = QPushButton('Видалити'); del_btn.clicked.connect(self.delete_clip)
        export_btn = QPushButton('🎙 Експорт MP4'); export_btn.clicked.connect(self.export)
        for b in (open_btn, add_btn, del_btn, export_btn): bar.addWidget(b)
        bar.addStretch(); self.file_label = QLabel('Відео не вибрано'); bar.addWidget(self.file_label)
        main.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget(); ll = QVBoxLayout(left)
        ll.addWidget(QLabel('Відео'))
        ll.addWidget(self.video, 1)
        controls = QHBoxLayout()
        self.play = QPushButton('▶ Play'); self.play.clicked.connect(self.toggle_play)
        self.seek = QSlider(Qt.Horizontal); self.seek.sliderMoved.connect(self.seek_to)
        self.time_label = QLabel('00:00 / 00:00')
        controls.addWidget(self.play); controls.addWidget(self.seek, 1); controls.addWidget(self.time_label)
        ll.addLayout(controls)
        splitter.addWidget(left)

        right = QWidget(); rl = QVBoxLayout(right)
        rl.addWidget(QLabel('Репліки'))
        self.list = QListWidget(); self.list.currentRowChanged.connect(self.select_clip)
        rl.addWidget(self.list, 1)
        rl.addWidget(QLabel('Текст'))
        self.text = QTextEdit(); self.text.setMaximumHeight(120); rl.addWidget(self.text)
        times = QHBoxLayout()
        self.start = QDoubleSpinBox(); self.start.setSuffix(' с'); self.start.setDecimals(2); self.start.setRange(0, 99999)
        self.end = QDoubleSpinBox(); self.end.setSuffix(' с'); self.end.setDecimals(2); self.end.setRange(0, 99999)
        times.addWidget(QLabel('Початок')); times.addWidget(self.start); times.addWidget(QLabel('Кінець')); times.addWidget(self.end)
        rl.addLayout(times)
        apply = QPushButton('Застосувати зміни'); apply.clicked.connect(self.apply_clip); rl.addWidget(apply)
        rl.addWidget(QLabel('Голос Windows'))
        self.voice = QComboBox(); self.load_voices(); rl.addWidget(self.voice)
        splitter.addWidget(right); splitter.setSizes([850, 380])
        main.addWidget(splitter, 1)
        main.addWidget(QLabel('ТАЙМЛАЙН — перетягуй краї репліки мишкою'))
        main.addWidget(self.timeline)
        self.status = QLabel('Готово'); main.addWidget(self.status)

    def load_voices(self):
        try:
            import pyttsx3
            e = pyttsx3.init(); voices = e.getProperty('voices')
            for v in voices: self.voice.addItem(getattr(v, 'name', 'Windows Voice'), v.id)
            e.stop()
        except Exception:
            self.voice.addItem('Системний голос')

    def open_video(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Вибери відео', '', 'Video (*.mp4 *.mkv *.mov *.avi)')
        if p:
            self.video_path = p; self.file_label.setText(Path(p).name); self.player.setSource(QUrl.fromLocalFile(p)); self.status.setText('Відео завантажено')

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause(); self.play.setText('▶ Play')
        else:
            self.player.play(); self.play.setText('⏸ Pause')

    def seek_to(self, value): self.player.setPosition(value)

    def position_changed(self, pos):
        self.seek.setValue(pos); self.timeline.set_current(pos); self.time_label.setText(f'{self.fmt(pos)} / {self.fmt(self.player.duration())}')

    def duration_changed(self, dur): self.seek.setRange(0, max(1, dur)); self.timeline.set_duration(dur)

    def fmt(self, ms):
        s = max(0, ms)//1000; return f'{s//60:02d}:{s%60:02d}'

    def add_clip(self):
        start = self.player.position(); end = min(self.player.duration() or start+5000, start+3000)
        self.clips.append({'start': start, 'end': max(start+500, end), 'text': 'Нова репліка'})
        self.refresh_list(); self.select_clip(len(self.clips)-1)

    def delete_clip(self):
        if 0 <= self.selected_index < len(self.clips):
            del self.clips[self.selected_index]; self.selected_index = -1; self.refresh_list()

    def refresh_list(self):
        self.list.blockSignals(True); self.list.clear()
        for c in self.clips: self.list.addItem(f"{c['start']/1000:.2f}s — {c['end']/1000:.2f}s   {c['text'][:45]}")
        self.list.blockSignals(False); self.timeline.set_clips(self.clips)

    def select_clip(self, i):
        if not (0 <= i < len(self.clips)): return
        self.selected_index = i; c = self.clips[i]
        self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
        self.text.setPlainText(c['text']); self.start.setValue(c['start']/1000); self.end.setValue(c['end']/1000)
        self.timeline.selected_index = i; self.timeline.update()

    def timeline_changed(self):
        self.refresh_list()
        if 0 <= self.selected_index < len(self.clips): self.select_clip(self.selected_index)

    def apply_clip(self):
        if not (0 <= self.selected_index < len(self.clips)): return
        c = self.clips[self.selected_index]; a = max(0, self.start.value()*1000); b = max(a+100, self.end.value()*1000)
        c['start'] = int(a); c['end'] = int(b); c['text'] = self.text.toPlainText().strip() or 'Нова репліка'; self.refresh_list(); self.select_clip(self.selected_index)

    def export(self):
        if not self.video_path: QMessageBox.warning(self, 'FilmDubUA', 'Спочатку відкрий відео.'); return
        if not self.clips: QMessageBox.warning(self, 'FilmDubUA', 'Додай репліки.'); return
        out, _ = QFileDialog.getSaveFileName(self, 'Зберегти', 'filmdubua_output.mp4', 'MP4 (*.mp4)')
        if not out: return
        try:
            import pyttsx3, subprocess, tempfile
            self.status.setText('Створюю озвучку...'); QApplication.processEvents()
            with tempfile.TemporaryDirectory() as td:
                files=[]
                for i,c in enumerate(self.clips):
                    wav=str(Path(td)/f'voice_{i}.wav'); e=pyttsx3.init(); e.setProperty('rate', 165)
                    if self.voice.currentData(): e.setProperty('voice', self.voice.currentData())
                    e.save_to_file(c['text'], wav); e.runAndWait(); e.stop(); files.append(wav)
                ins=[]; fs=[]
                for i,(c,wav) in enumerate(zip(self.clips,files)):
                    ins += ['-i', wav]; d=int(c['start']); fs.append(f'[{i+1}:a]adelay={d}|{d}[a{i}]')
                labels=''.join(f'[a{i}]' for i in range(len(files))); fs.append(f'{labels}amix=inputs={len(files)}:duration=longest:dropout_transition=0[voice]')
                cmd=['ffmpeg','-y','-i',self.video_path]+ins+['-filter_complex',';'.join(fs),'-map','0:v:0','-map','[voice]','-c:v','copy','-c:a','aac','-shortest',out]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self.status.setText('ГОТОВО — MP4 створено'); QMessageBox.information(self,'FilmDubUA','Готово! Відео збережено.')
        except FileNotFoundError: QMessageBox.critical(self,'FFmpeg','FFmpeg не знайдений у PATH.')
        except Exception as ex: QMessageBox.critical(self,'Експорт',str(ex)); self.status.setText('Помилка експорту')


if __name__ == '__main__':
    app = QApplication(sys.argv); app.setStyle('Fusion'); w=FilmDubUA(); w.show(); sys.exit(app.exec())
