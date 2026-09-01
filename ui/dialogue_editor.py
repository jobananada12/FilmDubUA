from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit, QSpinBox, QPushButton, QLabel, QComboBox
from core.dialogue import Dialogue, DialogueTrack
from core.tts import windows_voices, synthesize_ukrainian, TEMP_ROOT, VOICE_PROFILES
from core.dubbing import mix_dialogue, mix_dialogues

class DialogueEditor(QWidget):
    """Dialogue editor with Ukrainian neural TTS and per-character voice profiles."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.track=DialogueTrack(); self.list=QListWidget()
        self.character=QLineEdit('Персонаж 1'); self.text=QLineEdit()
        self.start=QSpinBox(); self.start.setRange(0,24*60*60*1000); self.start.setSuffix(' ms')
        self.end=QSpinBox(); self.end.setRange(0,24*60*60*1000); self.end.setValue(3000); self.end.setSuffix(' ms')
        self.voice=QComboBox(); self.profile=QComboBox()
        for key,data in VOICE_PROFILES.items(): self.profile.addItem(f"🎙 {data['label']}",key)
        self.rate=QSpinBox(); self.rate.setRange(80,300); self.rate.setValue(170); self.rate.setSuffix(' сл/хв')
        add=QPushButton('➕ Додати репліку'); remove=QPushButton('🗑 Видалити'); generate=QPushButton('🔊 Згенерувати українську озвучку'); mix=QPushButton('🎬 Зібрати дубльовану репліку'); mix_all=QPushButton('🎞️ Зібрати весь дубляж')
        generate.clicked.connect(self.generate_voice); mix.clicked.connect(self.mix_current_dialogue); mix_all.clicked.connect(self.mix_all_dialogues); add.clicked.connect(self.add_dialogue); remove.clicked.connect(self.remove_dialogue)
        for w in (self.character,self.text,self.start,self.end): w.editingFinished.connect(self.apply_current)
        self.profile.currentIndexChanged.connect(self.apply_profile)
        self.list.currentRowChanged.connect(self.load_current)
        self.voice.addItem('🇺🇦 Український Piper — локальний', 'piper-uk')
        try:
            for voice_id,name,languages in windows_voices(): self.voice.addItem(f'Windows: {name}',voice_id)
        except Exception: pass
        controls=QHBoxLayout(); controls.addWidget(QLabel('Персонаж')); controls.addWidget(self.character); controls.addWidget(QLabel('Текст')); controls.addWidget(self.text,1); controls.addWidget(QLabel('Початок')); controls.addWidget(self.start); controls.addWidget(QLabel('Кінець')); controls.addWidget(self.end); controls.addWidget(add); controls.addWidget(remove)
        voice_row=QHBoxLayout(); voice_row.addWidget(QLabel('Голос персонажа')); voice_row.addWidget(self.profile); voice_row.addWidget(QLabel('Швидкість')); voice_row.addWidget(self.rate); voice_row.addWidget(generate); voice_row.addWidget(mix); voice_row.addWidget(mix_all)
        layout=QVBoxLayout(self); layout.addLayout(controls); layout.addLayout(voice_row); layout.addWidget(self.list)

    def refresh(self):
        self.list.clear()
        for d in self.track.items:
            ready=' 🔊' if getattr(d,'audio_path','') and Path(d.audio_path).exists() else ''
            label=VOICE_PROFILES.get(getattr(d,'voice_profile','neutral'),VOICE_PROFILES['neutral'])['label']
            self.list.addItem(f'[{d.start_ms/1000:.2f}s–{d.end_ms/1000:.2f}s] {d.character} [{label}]: {d.text}{ready}')

    def add_dialogue(self):
        self.track.add(Dialogue(self.start.value(),self.end.value(),self.character.text(),self.text.text(),voice_profile=self.profile.currentData() or 'neutral')); self.refresh(); self.list.setCurrentRow(len(self.track.items)-1)
    def remove_dialogue(self): self.track.remove(self.list.currentRow()); self.refresh()
    def load_current(self,row):
        if 0<=row<len(self.track.items):
            d=self.track.items[row]; self.character.setText(d.character); self.text.setText(d.text); self.start.setValue(d.start_ms); self.end.setValue(d.end_ms)
            idx=self.profile.findData(getattr(d,'voice_profile','neutral')); self.profile.setCurrentIndex(max(0,idx))
    def apply_profile(self):
        row=self.list.currentRow()
        if 0<=row<len(self.track.items): self.track.items[row].voice_profile=self.profile.currentData() or 'neutral'; self.refresh(); self.list.setCurrentRow(row)
    def apply_current(self):
        row=self.list.currentRow()
        if row<0:return
        self.track.update(row,character=self.character.text(),text=self.text.text(),start_ms=self.start.value(),end_ms=self.end.value()); self.refresh(); self.list.setCurrentRow(row)

    def generate_voice(self):
        row=self.list.currentRow()
        if row<0:return self.status_message('Спочатку виберіть репліку')
        d=self.track.items[row]
        if not d.text.strip():return self.status_message('У репліці немає тексту')
        if d.end_ms<=d.start_ms:return self.status_message('Кінець репліки має бути після початку')
        try:
            out_dir=TEMP_ROOT/'tts'; out_dir.mkdir(parents=True,exist_ok=True); out=out_dir/f'dialogue_{row+1:03d}_{d.voice_profile}.wav'
            synthesize_ukrainian(d.text,str(out),rate=self.rate.value(),volume=d.volume,profile=d.voice_profile)
            d.audio_path=str(out); self.refresh(); self.list.setCurrentRow(row); self.status_message(f'✅ Голос {VOICE_PROFILES.get(d.voice_profile,VOICE_PROFILES["neutral"])["label"]} створено: {out}')
        except Exception as exc:self.status_message(f'❌ TTS: {exc}')

    def _selected_clip(self):
        main=self.window(); clips=getattr(main,'montage_clips',[]); widget=getattr(main,'montage_list',None); row=widget.currentRow() if widget else -1
        if not(0<=row<len(clips)):self.status_message('Спочатку виберіть кліп на монтажній доріжці');return None
        return main,clips[row],row
    def mix_current_dialogue(self):
        row=self.list.currentRow()
        if row<0:return self.status_message('Спочатку виберіть репліку')
        d=self.track.items[row]
        if not getattr(d,'audio_path','') or not Path(d.audio_path).exists():return self.status_message('Спочатку згенеруйте озвучку цієї репліки')
        selected=self._selected_clip()
        if not selected:return
        main,clip,selected_row=selected; background_path=getattr(main,'background_path','')
        if not background_path or not Path(background_path).exists():return self.status_message('Спочатку натисніть «Прибрати голоси з вибраного уривка AI»')
        video_path=clip.get('path',''); out_dir=TEMP_ROOT/'dubbed'; out_dir.mkdir(parents=True,exist_ok=True); out=out_dir/f'dubbed_clip_{selected_row+1:03d}_dialogue_{row+1:03d}.mp4'
        try:
            result=mix_dialogue(video_path,background_path,d.audio_path,str(out),max(0,int(d.start_ms)),d.volume); self.status_message(f'✅ Готова репліка: {result}'); main.player.open(result); main.status.setText(f'🎬 Українську репліку накладено на кліп {selected_row+1}')
        except Exception as exc:self.status_message(f'❌ Дубляж: {exc}')
    def mix_all_dialogues(self):
        selected=self._selected_clip()
        if not selected:return
        main,clip,selected_row=selected; background_path=getattr(main,'background_path','')
        if not background_path or not Path(background_path).exists():return self.status_message('Спочатку натисніть «Прибрати голоси з вибраного уривка AI»')
        ready=[d for d in self.track.items if getattr(d,'audio_path','') and Path(d.audio_path).exists()]
        if not ready:return self.status_message('Спочатку згенеруйте українську озвучку хоча б для однієї репліки')
        out_dir=TEMP_ROOT/'dubbed'; out_dir.mkdir(parents=True,exist_ok=True); out=out_dir/f'dubbed_clip_{selected_row+1:03d}_FULL.mp4'
        try:
            result=mix_dialogues(clip.get('path',''),background_path,ready,str(out)); self.status_message(f'✅ Весь дубляж зібрано: {result}'); main.player.open(result); main.status.setText(f'🎞️ Весь дубляж зібрано для кліпу {selected_row+1}: {len(ready)} реплік')
        except Exception as exc:self.status_message(f'❌ Весь дубляж: {exc}')
    def status_message(self,text):
        parent=self.window()
        if hasattr(parent,'status'):parent.status.setText(text)
