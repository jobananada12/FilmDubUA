from dataclasses import dataclass, asdict
from typing import List

@dataclass
class Dialogue:
    start_ms: int = 0
    end_ms: int = 3000
    character: str = 'Персонаж 1'
    text: str = ''
    voice_id: str = ''
    volume: float = 1.0
    speed: float = 1.0
    pitch: float = 0.0
    reverb: float = 0.0
    pan: float = 0.0

class DialogueTrack:
    def __init__(self):
        self.items: List[Dialogue] = []

    def add(self, dialogue=None):
        item = dialogue or Dialogue()
        self.items.append(item)
        self.items.sort(key=lambda x: x.start_ms)
        return item

    def remove(self, index: int):
        if 0 <= index < len(self.items):
            return self.items.pop(index)

    def update(self, index: int, **changes):
        if 0 <= index < len(self.items):
            d = self.items[index]
            for key, value in changes.items():
                if hasattr(d, key): setattr(d, key, value)
            self.items.sort(key=lambda x: x.start_ms)
            return d

    def to_list(self):
        return [asdict(x) for x in self.items]
