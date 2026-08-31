from pathlib import Path
import subprocess


class FinalExportError(RuntimeError):
    pass


def export_final(video: str, audio: str, reaction: str, output: str, subtitles: str = '', reaction_scale: float = .34) -> str:
    """Compose a 9:16 final video: main clip fills the top panel, user video is padded on bottom."""
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

    # 1080x1920 canvas split into two 1080x960 panels.
    # Main film fills the entire top panel; its sides may be cropped.
    # User video keeps its aspect ratio and gets black padding when smaller.
    filters = [
        "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960:(iw-1080)/2:(ih-960)/2[top]"
    ]

    if subtitles:
        sub = str(Path(subtitles).resolve()).replace('\\', '/').replace(':', '\\:')
        filters.append(f"[top]subtitles='{sub}'[topsub]")
        top_label = 'topsub'
    else:
        top_label = 'top'

    if rx:
        filters.append(
            "[1:v]scale=1080:960:force_original_aspect_ratio=decrease,"
            "pad=1080:960:(ow-iw)/2:(oh-ih)/2:color=black[bottom]"
        )
        filters.append(f"[{top_label}][bottom]vstack=inputs=2[v]")
        filter_graph = ';'.join(filters)
        inputs = ['-i', str(main), '-i', str(rx)]
        if separate_audio:
            inputs += ['-i', str(separate_audio)]
            audio_index = '2:a:0'
        else:
            audio_index = '0:a:0?'
    else:
        filters.append("color=c=black:s=1080x960:d=86400[bottom]")
        filters.append(f"[{top_label}][bottom]vstack=inputs=2[v]")
        filter_graph = ';'.join(filters)
        inputs = ['-i', str(main)]
        if separate_audio:
            inputs += ['-i', str(separate_audio)]
            audio_index = '1:a:0'
        else:
            audio_index = '0:a:0?'

    cmd = ['ffmpeg', '-y', *inputs, '-filter_complex', filter_graph,
           '-map', '[v]', '-map', audio_index, '-shortest',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
           '-movflags', '+faststart', str(out)]

    print('\n' + '=' * 80, flush=True)
    print('FILMDUBUA FINAL EXPORT', flush=True)
    print('Layout: MAIN TOP FILLS 1080x960 + USER VIDEO BOTTOM 1080x960 WITH BLACK PADDING', flush=True)
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
