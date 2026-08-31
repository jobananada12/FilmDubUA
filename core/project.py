from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

@dataclass
class DialogueClip:
    start_ms: int
    end_ms: int
    text: str = ""
    character: str = "Персонаж 1"
    voice_id: str = ""
    volume: float = 1.0
    speed: float = 1.0
    pitch: float = 0.0
    reverb: float = 0.0
    pan: float = 0.0

@dataclass
class ReactionTrack:
    path: str = ""
    x: float = 0.5
    y: float = 0.78
    width: float = 0.42
    height: float = 0.30
    circular: bool = False
    volume: float = 1.0
    enabled: bool = True

@dataclass
class Project:
    video_path: str = ""
    clips: list = field(default_factory=list)
    reaction: ReactionTrack = field(default_factory=ReactionTrack)
    original_volume: float = 0.25
    dubbing_volume: float = 1.0
    aspect_ratio: str = "9:16"

    def to_dict(self):
        return {
            "video_path": self.video_path,
            "clips": [asdict(c) for c in self.clips],
            "reaction": asdict(self.reaction),
            "original_volume": self.original_volume,
            "dubbing_volume": self.dubbing_volume,
            "aspect_ratio": self.aspect_ratio,
        }

    def save(self, path):
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path):
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        p=cls(video_path=d.get("video_path", ""), original_volume=d.get("original_volume", .25), dubbing_volume=d.get("dubbing_volume",1.0), aspect_ratio=d.get("aspect_ratio","9:16"))
        p.clips=[DialogueClip(**c) for c in d.get("clips",[])]
        p.reaction=ReactionTrack(**d.get("reaction",{}))
        return p
