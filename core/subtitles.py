from dataclasses import dataclass
from pathlib import Path

@dataclass
class Subtitle:
    start_ms: int
    end_ms: int
    text: str
    character: str = ''


def format_srt_time(ms: int) -> str:
    ms=max(0,int(ms)); h,rem=divmod(ms,3600000); m,rem=divmod(rem,60000); s,ms=divmod(rem,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def write_srt(items, path: str):
    lines=[]
    for i,item in enumerate(items,1):
        lines += [str(i), f'{format_srt_time(item.start_ms)} --> {format_srt_time(item.end_ms)}', item.text, '']
    Path(path).write_text('\n'.join(lines), encoding='utf-8')
