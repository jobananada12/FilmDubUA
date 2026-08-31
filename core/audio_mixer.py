from pathlib import Path
import subprocess

class AudioMixerError(RuntimeError):
    pass

def mix_audio(background: str, dialogue_files: list[tuple[str,int]], output_wav: str, background_volume: float=.25, dialogue_volume: float=1.0) -> str:
    """Mix background audio with timed dialogue WAV files using FFmpeg.
    dialogue_files contains (wav_path, start_ms).
    """
    if not Path(background).exists(): raise FileNotFoundError(background)
    if not dialogue_files: raise ValueError('Немає реплік для мікшування')
    out=Path(output_wav).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    cmd=['ffmpeg','-y','-i',background]
    for wav,_ in dialogue_files: cmd += ['-i',wav]
    filters=[f'[0:a]volume={background_volume}[bg]']
    labels=['[bg]']
    for i,(_,start) in enumerate(dialogue_files,1):
        delay=max(0,int(start)); filters.append(f'[{i}:a]volume={dialogue_volume},adelay={delay}:all=1[d{i}]'); labels.append(f'[d{i}]')
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0[mix]')
    cmd += ['-filter_complex',';'.join(filters),'-map','[mix]','-c:a','pcm_s16le',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: raise AudioMixerError(r.stderr[-3000:])
    return str(out)
