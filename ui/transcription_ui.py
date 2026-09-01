from pathlib import Path
import json
import tempfile
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QPushButton
from core.speech_recognition import transcribe_clip
from core.diarization import diarize_audio
from core.dialogue import Dialogue

VOICE_BY_INDEX = ['male', 'female', 'young', 'deep', 'neutral']


def _speaker_for_segment(start_ms, end_ms, turns):
    scores={}
    for turn in turns:
        overlap=max(0,min(end_ms,turn['end_ms'])-max(start_ms,turn['start_ms']))
        if overlap>0: scores[turn['speaker']]=scores.get(turn['speaker'],0)+overlap
    return max(scores,key=scores.get) if scores else None

class TranscriptionWorker(QThread):
    finished = Signal(str, object)
    failed = Signal(str)
    def __init__(self, clip_path): super().__init__(); self.clip_path=clip_path
    def run(self):
        try:
            out_dir=Path(tempfile.mkdtemp(prefix='filmdubua_transcript_'))
            transcript=transcribe_clip(self.clip_path,str(out_dir/'transcript.json'))
            try: turns=diarize_audio(self.clip_path)
            except Exception: turns=[]
            self.finished.emit(transcript,turns)
        except Exception as exc: self.failed.emit(str(exc))


def install_transcription_button(main_window):
    """Add transcription + automatic speaker assignment to the selected clip."""
    buttons=main_window.findChildren(QPushButton)
    anchor=next((b for b in buttons if 'Прибрати голоси' in b.text()),None)
    if anchor is None:return
    parent_layout=anchor.parentWidget().layout()
    button=QPushButton('📝 5. Розпізнати репліки + визначити персонажів AI',anchor.parentWidget())
    parent_layout.insertWidget(parent_layout.indexOf(anchor)+1,button)
    worker={'value':None}

    def failed(error): main_window.status.setText(f'❌ Розпізнавання: {error}')

    def done(path,turns):
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8')); segments=data.get('segments',[])
            track=main_window.dialogue_editor.track; track.items.clear(); speaker_map={}
            for seg in segments:
                start=int(float(seg.get('start',0))*1000); end=int(float(seg.get('end',start/1000))*1000); text=str(seg.get('text','')).strip()
                if not text: continue
                speaker=_speaker_for_segment(start,end,turns) or 'SPEAKER_00'
                if speaker not in speaker_map: speaker_map[speaker]=len(speaker_map)
                idx=speaker_map[speaker]%len(VOICE_BY_INDEX); profile=VOICE_BY_INDEX[idx]
                track.add(Dialogue(start,end,f'Персонаж {speaker_map[speaker]+1}',text,voice_profile=profile))
            main_window.dialogue_editor.refresh()
            if turns:
                main_window.status.setText(f'✅ Розпізнано {len(track.items)} реплік. AI визначив {len(speaker_map)} різних голосів.')
            else:
                main_window.status.setText(f'✅ Розпізнано {len(track.items)} реплік. Діаризація недоступна — використано профілі голосів по черзі.')
        except Exception as exc: failed(str(exc))

    def start():
        row=main_window.montage_list.currentRow(); clips=main_window.montage_clips
        if not (0<=row<len(clips)): main_window.status.setText('Спочатку виберіть кліп на монтажній доріжці'); return
        clip=clips[row].get('path','')
        if not Path(clip).exists(): main_window.status.setText('Файл вибраного кліпу не знайдено'); return
        if worker['value'] is not None and worker['value'].isRunning(): return
        main_window.status.setText('⏳ AI розпізнає репліки та визначає персонажів...')
        w=TranscriptionWorker(clip); worker['value']=w; w.finished.connect(done); w.failed.connect(failed); w.start()

    button.clicked.connect(start); main_window._transcription_button=button; main_window._transcription_worker_holder=worker
