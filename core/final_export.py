from pathlib import Path
import subprocess


class FinalExportError(RuntimeError):
    pass


def export_final(video: str, audio: str, reaction: str, output: str, subtitles: str = '', reaction_scale: float = .34) -> str:
    """Compose a 9:16 final video with the dubbed/main audio and reaction overlay."""
    main = Path(video).resolve()
    rx = Path(reaction).resolve() if reaction else None
    separate_audio = Path(audio).resolve() if audio else None
    out = Path(output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if not main.exists():
        raise FileNotFoundError(str(main))
    if rx and not rx.exists():
        raise FileNotFoundError(str(rx))
    if separate_audio and not separate_audio.exists():
        raise FileNotFoundError(str(separate_audio))

    base = '[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[base]'
    filters = [base]
    if subtitles:
        sub = str(Path(subtitles).resolve()).replace('\\', '/').replace(':', '\\:')
        filters.append(f"[base]subtitles='{sub}'[subbed]")
        base_label = 'subbed'
    else:
        base_label = 'base'

    if rx:
        size = max(160, min(900, int(1080 * float(reaction_scale))))
        radius = size / 2
        circle = f"if(lte((X-{radius})*(X-{radius})+(Y-{radius})*(Y-{radius}),{radius}*{radius}),255,0)"
        filters.append(
            f"[1:v]scale={size}:{size}:force_original_aspect_ratio=increase,"
            f"crop={size}:{size},format=rgba,"
            f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{circle}'[rx]"
        )
        filters.append(f"[{base_label}][rx]overlay=(W-w)/2:H-h-35:format=auto[v]")
        filter_graph = ';'.join(filters)
        inputs = ['-i', str(main), '-i', str(rx)]
        if separate_audio:
            inputs += ['-i', str(separate_audio)]
            audio_index = '2:a:0'
        else:
            audio_index = '0:a:0?'
        cmd = ['ffmpeg', '-y', *inputs, '-filter_complex', filter_graph,
               '-map', '[v]', '-map', audio_index, '-shortest',
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
               '-movflags', '+faststart', str(out)]
    else:
        filter_graph = ';'.join(filters)
        audio_index = '1:a:0' if separate_audio else '0:a:0?'
        inputs = ['-i', str(main)] + (['-i', str(separate_audio)] if separate_audio else [])
        cmd = ['ffmpeg', '-y', *inputs, '-filter_complex', filter_graph,
               '-map', '[subbed]' if subtitles else '[base]', '-map', audio_index,
               '-shortest', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
               '-movflags', '+faststart', str(out)]

    print('\n' + '=' * 80, flush=True)
    print('FILMDUBUA FINAL EXPORT', flush=True)
    print('FFmpeg command:', ' '.join(cmd), flush=True)
    print('=' * 80, flush=True)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, flush=True)
    print('=' * 80, flush=True)

    if result.returncode:
        raise FinalExportError(result.stderr[-6000:] or 'FFmpeg не зміг зібрати фінальний ролик')
    if not out.exists() or out.stat().st_size == 0:
        raise FinalExportError('FFmpeg завершився без створення фінального MP4')
    return str(out)
