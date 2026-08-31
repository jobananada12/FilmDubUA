import sys, re, subprocess, tempfile
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QFileDialog,QTextEdit,QComboBox,QSlider,QMessageBox,QSplitter,QListWidget,QDoubleSpinBox,QGroupBox
from PySide6.QtMultimedia import QAudioOutput,QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

class ClipTimeline(QWidget):
    changed=Signal(); selected=Signal(int)
    def __init__(self):
        super().__init__(); self.setMinimumHeight(190); self.clips=[]; self.duration=60000; self.current=0; self.drag=None; self.selected_index=-1
    def set_duration(self,ms): self.duration=max(1,ms); self.update()
    def set_current(self,ms): self.current=ms; self.update()
    def set_clips(self,c): self.clips=c; self.update()
    def x_for(self,ms):
        l,r=55,self.width()-20; return l+(r-l)*ms/self.duration
    def ms_for(self,x):
        l,r=55,self.width()-20; return max(0,min(self.duration,int((x-l)/max(1,r-l)*self.duration)))
    def paintEvent(self,e):
        p=QPainter(self); p.fillRect(self.rect(),QColor('#15171b')); l=55; w=max(1,self.width()-75); p.setPen(QPen(QColor('#777'),1))
        for i in range(11):
            x=l+w*i/10; p.drawLine(int(x),25,int(x),155); p.drawText(int(x)-18,18,f'{self.duration*i/10/1000:.1f}s')
        for i,c in enumerate(self.clips):
            x1,x2=self.x_for(c['start']),self.x_for(c['end']); rect=QRectF(x1,55,max(20,x2-x1),70); sel=i==self.selected_index
            p.setBrush(QBrush(QColor('#3b82f6') if sel else QColor('#2563eb'))); p.setPen(QPen(QColor('#93c5fd') if sel else QColor('#60a5fa'),2)); p.drawRoundedRect(rect,6,6); p.setPen(Qt.white); p.drawText(rect.adjusted(8,5,-8,-5),Qt.AlignVCenter,c['text'].replace('\n',' ')[:42]); p.setPen(QPen(QColor('#dbeafe'),4)); p.drawLine(int(x1),57,int(x1),123); p.drawLine(int(x2),57,int(x2),123)
        px=self.x_for(self.current); p.setPen(QPen(QColor('#ef4444'),2)); p.drawLine(int(px),20,int(px),165); p.setBrush(QBrush(QColor('#ef4444'))); p.drawEllipse(int(px)-5,15,10,10)
    def mousePressEvent(self,e):
        if e.button()!=Qt.LeftButton:return
        x=e.position().x()
        for i,c in enumerate(self.clips):
            x1,x2=self.x_for(c['start']),self.x_for(c['end'])
            if abs(x-x1)<12:self.drag=('start',i); self.selected_index=i; self.selected.emit(i); return
            if abs(x-x2)<12:self.drag=('end',i); self.selected_index=i; self.selected.emit(i); return
            if x1<=x<=x2 and 55<=e.position().y()<=130:self.selected_index=i; self.selected.emit(i); return
        self.current=self.ms_for(x); self.changed.emit(); self.update()
    def mouseMoveEvent(self,e):
        if not self.drag:return
        kind,i=self.drag; v=self.ms_for(e.position().x()); c=self.clips[i]
        if kind=='start':c['start']=min(v,c['end']-100)
        else:c['end']=max(v,c['start']+100)
        self.changed.emit(); self.update()
    def mouseReleaseEvent(self,e):self.drag=None

class FilmDubUA(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('FilmDubUA — Mini CapCut для озвучки'); self.resize(1280,850); self.video_path=''; self.clips=[]; self.selected_index=-1
        self.player=QMediaPlayer(); self.audio=QAudioOutput(); self.player.setAudioOutput(self.audio); self.video=QVideoWidget(); self.player.setVideoOutput(self.video); self.timeline=ClipTimeline(); self.timeline.selected.connect(self.select_clip); self.timeline.changed.connect(self.timeline_changed); self.build_ui(); self.player.positionChanged.connect(self.position_changed); self.player.durationChanged.connect(self.duration_changed)
    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root); bar=QHBoxLayout()
        for text,fn in [('🎬 Відкрити відео',self.open_video),('+ Репліка',self.add_clip),('📝 Імпорт SRT',self.import_srt),('Видалити',self.delete_clip),('🎙 Експорт MP4',self.export)]:
            b=QPushButton(text); b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(); self.file_label=QLabel('Відео не вибрано'); bar.addWidget(self.file_label); main.addLayout(bar)
        split=QSplitter(Qt.Horizontal); left=QWidget(); ll=QVBoxLayout(left); ll.addWidget(QLabel('Відео')); ll.addWidget(self.video,1); controls=QHBoxLayout(); self.play=QPushButton('▶ Play'); self.play.clicked.connect(self.toggle_play); self.seek=QSlider(Qt.Horizontal); self.seek.sliderMoved.connect(self.seek_to); self.time_label=QLabel('00:00 / 00:00'); controls.addWidget(self.play); controls.addWidget(self.seek,1); controls.addWidget(self.time_label); ll.addLayout(controls); split.addWidget(left)
        right=QWidget(); rl=QVBoxLayout(right); rl.addWidget(QLabel('Репліки')); self.list=QListWidget(); self.list.currentRowChanged.connect(self.select_clip); rl.addWidget(self.list,1); rl.addWidget(QLabel('Текст')); self.text=QTextEdit(); self.text.setMaximumHeight(120); rl.addWidget(self.text); times=QHBoxLayout(); self.start=QDoubleSpinBox(); self.start.setSuffix(' с'); self.start.setDecimals(2); self.start.setRange(0,99999); self.end=QDoubleSpinBox(); self.end.setSuffix(' с'); self.end.setDecimals(2); self.end.setRange(0,99999); times.addWidget(QLabel('Початок')); times.addWidget(self.start); times.addWidget(QLabel('Кінець')); times.addWidget(self.end); rl.addLayout(times); a=QPushButton('Застосувати зміни'); a.clicked.connect(self.apply_clip); rl.addWidget(a)
        g=QGroupBox('Мікшер'); gl=QVBoxLayout(g); gl.addWidget(QLabel('Оригінальний звук')); self.orig=QSlider(Qt.Horizontal); self.orig.setRange(0,100); self.orig.setValue(25); gl.addWidget(self.orig); gl.addWidget(QLabel('Гучність озвучки')); self.dub=QSlider(Qt.Horizontal); self.dub.setRange(50,200); self.dub.setValue(100); gl.addWidget(self.dub); rl.addWidget(g); rl.addWidget(QLabel('Голос Windows')); self.voice=QComboBox(); self.load_voices(); rl.addWidget(self.voice); split.addWidget(right); split.setSizes([850,380]); main.addWidget(split,1); main.addWidget(QLabel('ТАЙМЛАЙН — перетягуй краї репліки мишкою')); main.addWidget(self.timeline); self.status=QLabel('Готово'); main.addWidget(self.status)
    def load_voices(self):
        try:
            import pyttsx3; e=pyttsx3.init(); vs=e.getProperty('voices')
            for v in vs:self.voice.addItem(getattr(v,'name','Windows Voice'),v.id)
            e.stop()
        except Exception:self.voice.addItem('Системний голос')
    def open_video(self):
        p,_=QFileDialog.getOpenFileName(self,'Вибери відео','','Video (*.mp4 *.mkv *.mov *.avi)')
        if p:self.video_path=p; self.file_label.setText(Path(p).name); self.player.setSource(QUrl.fromLocalFile(p)); self.status.setText('Відео завантажено')
    def toggle_play(self):
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.pause(); self.play.setText('▶ Play')
        else:self.player.play(); self.play.setText('⏸ Pause')
    def seek_to(self,v):self.player.setPosition(v)
    def position_changed(self,p):self.seek.setValue(p); self.timeline.set_current(p); self.time_label.setText(f'{self.fmt(p)} / {self.fmt(self.player.duration())}')
    def duration_changed(self,d):self.seek.setRange(0,max(1,d)); self.timeline.set_duration(d)
    def fmt(self,ms):s=max(0,ms)//1000; return f'{s//60:02d}:{s%60:02d}'
    def add_clip(self):
        s=self.player.position(); e=min(self.player.duration() or s+5000,s+3000); self.clips.append({'start':s,'end':max(s+500,e),'text':'Нова репліка'}); self.refresh_list(); self.select_clip(len(self.clips)-1)
    def delete_clip(self):
        if 0<=self.selected_index<len(self.clips):del self.clips[self.selected_index]; self.selected_index=-1; self.refresh_list()
    def refresh_list(self):
        self.list.blockSignals(True); self.list.clear()
        for c in self.clips:self.list.addItem(f"{c['start']/1000:.2f}s — {c['end']/1000:.2f}s   {c['text'][:45]}")
        self.list.blockSignals(False); self.timeline.set_clips(self.clips)
    def select_clip(self,i):
        if not 0<=i<len(self.clips):return
        self.selected_index=i; c=self.clips[i]; self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False); self.text.setPlainText(c['text']); self.start.setValue(c['start']/1000); self.end.setValue(c['end']/1000); self.timeline.selected_index=i; self.timeline.update()
    def timeline_changed(self):self.refresh_list()
    def apply_clip(self):
        if not 0<=self.selected_index<len(self.clips):return
        c=self.clips[self.selected_index]; c['start']=int(self.start.value()*1000); c['end']=max(c['start']+100,int(self.end.value()*1000)); c['text']=self.text.toPlainText().strip() or 'Нова репліка'; self.refresh_list(); self.select_clip(self.selected_index)
    def parse_time(self,s):
        h,m,sec=s.replace(',','.').split(':'); return int((int(h)*3600+int(m)*60+float(sec))*1000)
    def import_srt(self):
        p,_=QFileDialog.getOpenFileName(self,'Імпорт субтитрів','','SubRip (*.srt);;Усі файли (*.*)')
        if not p:return
        try:
            raw=Path(p).read_text(encoding='utf-8-sig')
            blocks=re.split(r'\n\s*\n',raw.strip())
            imported=[]
            for block in blocks:
                lines=block.splitlines()
                if len(lines)<3:continue
                timing=next((x for x in lines if '-->' in x),None)
                if not timing:continue
                a,b=[x.strip() for x in timing.split('-->')[:2]]
                text=' '.join(x.strip() for x in lines[lines.index(timing)+1:] if x.strip())
                text=re.sub(r'<[^>]+>','',text)
                if text:imported.append({'start':self.parse_time(a),'end':self.parse_time(b),'text':text})
            self.clips=imported; self.selected_index=-1; self.refresh_list()
            if imported:self.select_clip(0)
            self.status.setText(f'Імпортовано реплік: {len(imported)}')
        except Exception as ex:QMessageBox.critical(self,'SRT',f'Не вдалося прочитати SRT: {ex}')
    def export(self):
        if not self.video_path:return QMessageBox.warning(self,'FilmDubUA','Спочатку відкрий відео.')
        if not self.clips:return QMessageBox.warning(self,'FilmDubUA','Додай репліки або імпортуй SRT.')
        out,_=QFileDialog.getSaveFileName(self,'Зберегти','filmdubua_output.mp4','MP4 (*.mp4)')
        if not out:return
        try:
            import pyttsx3
            self.status.setText('Створюю озвучку та мікс...'); QApplication.processEvents()
            with tempfile.TemporaryDirectory() as td:
                files=[]
                for i,c in enumerate(self.clips):
                    wav=str(Path(td)/f'voice_{i}.wav'); e=pyttsx3.init(); e.setProperty('rate',165)
                    if self.voice.currentData():e.setProperty('voice',self.voice.currentData())
                    e.save_to_file(c['text'],wav); e.runAndWait(); e.stop(); files.append(wav)
                ins=['-i',self.video_path]; fs=[]
                for i,(c,wav) in enumerate(zip(self.clips,files)):
                    ins+=['-i',wav]; d=int(c['start']); fs.append(f'[{i+1}:a]adelay={d}|{d}[a{i}]')
                labels=''.join(f'[a{i}]' for i in range(len(files))); fs.append(f'{labels}amix=inputs={len(files)}:duration=longest:dropout_transition=0[voice]')
                fs.append(f'[0:a]volume={self.orig.value()/100}[original]'); fs.append(f'[voice]volume={self.dub.value()/100}[dubbed]'); fs.append('[original][dubbed]amix=inputs=2:duration=longest:dropout_transition=0[mix]')
                cmd=['ffmpeg','-y']+ins+['-filter_complex',';'.join(fs),'-map','0:v:0','-map','[mix]','-c:v','copy','-c:a','aac','-shortest',out]; subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            self.status.setText('ГОТОВО — MP4 створено'); QMessageBox.information(self,'FilmDubUA','Готово! Відео збережено.')
        except FileNotFoundError:QMessageBox.critical(self,'FFmpeg','FFmpeg не знайдений у PATH.')
        except Exception as ex:QMessageBox.critical(self,'Експорт',str(ex)); self.status.setText('Помилка експорту')

if __name__=='__main__':
    app=QApplication(sys.argv); app.setStyle('Fusion'); w=FilmDubUA(); w.show(); sys.exit(app.exec())
