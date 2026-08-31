"""FFmpeg helpers for assembling Ukrainian dubbed montage clips."""
from pathlib import Path
import subprocess

class DubbingError(RuntimeError):
    pass

def _check_files(*paths):
    for value in paths:
        p=Path(value).resolve()
        if not p.exists(): raise DubbingError(f"Файл не знайдено: {p}")

def mix_dialogue(video_path, background_path, voice_path, output_path, start_ms=0, volume=1.0):
    video=Path(video_path).resolve(); background=Path(background_path).resolve(); voice=Path(voice_path).resolve(); output=Path(output_path).resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    _check_files(video,background,voice)
    delay=max(0,int(start_ms)); voice_volume=max(0.0,float(volume))
    cmd=["ffmpeg","-y","-i",str(video),"-i",str(background),"-i",str(voice),"-filter_complex",f"[1:a]volume=1.0[bg];[2:a]volume={voice_volume*1.5:.3f},adelay={delay}|{delay}[voice];[bg][voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=1[mix]","-map","0:v:0","-map","[mix]","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(output)]
    proc=subprocess.run(cmd,capture_output=True,text=True)
    if proc.returncode!=0: raise DubbingError(proc.stderr[-5000:] or "FFmpeg не зміг зібрати дубльовану репліку")
    if not output.exists() or output.stat().st_size==0: raise DubbingError("FFmpeg не створив дубльований кліп")
    return str(output)

def mix_dialogues(video_path, background_path, dialogues, output_path):
    video=Path(video_path).resolve(); background=Path(background_path).resolve(); output=Path(output_path).resolve(); output.parent.mkdir(parents=True,exist_ok=True); _check_files(video,background)
    ready=[d for d in dialogues if getattr(d,'audio_path','') and Path(d.audio_path).exists()]
    if not ready: raise DubbingError('Немає згенерованих WAV-реплік для цього кліпу')
    cmd=['ffmpeg','-y','-i',str(video),' -i'.strip(),str(background)]
    for d in ready: cmd += ['-i',str(Path(d.audio_path).resolve())]
    filters=['[1:a]volume=1.0[bg]']; mix_inputs=['[bg]']
    for index,d in enumerate(ready,start=2):
        label=f'v{index}'; delay=max(0,int(d.start_ms)); volume=max(0.0,float(getattr(d,'volume',1.0)))*1.5
        filters.append(f'[{index}:a]volume={volume:.3f},adelay={delay}|{delay}[{label}]'); mix_inputs.append(f'[{label}]')
    filters.append(''.join(mix_inputs)+f'amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0:normalize=1[mix]')
    cmd += ['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[mix]','-c:v','copy','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(output)]
    proc=subprocess.run(cmd,capture_output=True,text=True)
    if proc.returncode!=0: raise DubbingError(proc.stderr[-6000:] or 'FFmpeg не зміг зібрати весь дубляж')
    if not output.exists() or output.stat().st_size==0: raise DubbingError('FFmpeg не створив фінальний дубльований кліп')
    return str(output)
