from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import QWidget

class VerticalCanvas(QWidget):
    """9:16 preview canvas. Film is the main layer; reaction is a lower layer."""
    changed = Signal()
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 520)
        self.video_label = '🎬 ВІДЕО'
        self.reaction_label = '👤 МОЄ ВІДЕО'
        self.show_reaction = True
        self.reaction_x, self.reaction_y = .5, .78
        self.reaction_w, self.reaction_h = .42, .30

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#0b0d10'))
        h = min(self.height()-20, int((self.width()-20)*16/9))
        w = int(h*9/16)
        x, y = (self.width()-w)//2, (self.height()-h)//2
        p.setBrush(QBrush(QColor('#22262d'))); p.setPen(Qt.NoPen)
        p.drawRect(x,y,w,h)
        p.setPen(QPen(QColor('#666'),1)); p.drawText(x+10,y+24,self.video_label)
        # reaction preview occupies the lower portion of the 9:16 canvas
        if self.show_reaction:
            rw, rh = int(w*self.reaction_w), int(h*self.reaction_h)
            rx = int(x+w*self.reaction_x-rw/2); ry = int(y+h*self.reaction_y-rh/2)
            p.setBrush(QBrush(QColor('#343a44'))); p.setPen(QPen(QColor('#8aa4c8'),2))
            p.drawRoundedRect(rx,ry,rw,rh,12,12)
            p.setPen(QColor('#ddd')); p.drawText(rx+10,ry+24,self.reaction_label)
        p.setPen(QPen(QColor('#aaa'),1)); p.drawText(x+8,y+h+18,'9:16  •  TikTok / Reels / Shorts')
