# -*- coding: utf-8 -*-
"""plate_widget.py - ویجت پلاک ایرانی + توابع کمکی (نمایش صحیح RTL)"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt5.QtGui import QFont

FA = '۰۱۲۳۴۵۶۷۸۹'

def to_fa(s):
    return ''.join(FA[int(c)] if c.isdigit() else c for c in str(s or ''))

def format_plate(two, letter, three, iran):
    """رشتهٔ ذخیره/نمایش: در متن RTL دقیقاً مثل پلاک واقعی چیده می‌شود"""
    return 'ایران {} | {} {} {}'.format(to_fa(iran), to_fa(three), (letter or '').strip(), to_fa(two))

def parse_plate(text):
    """تجزیه هر دو قالب (قدیم و جدید) -> (two, letter, three, iran)"""
    text = (text or '').strip()
    if not text:
        return '', '', '', ''
    two = letter = three = iran = ''
    if text.startswith('ایران'):
        rest = text[len('ایران'):].strip()
        if '|' in rest:
            iran, main = [x.strip() for x in rest.split('|', 1)]
        else:
            parts_all = rest.split()
            iran = parts_all[0] if parts_all else ''
            main = ' '.join(parts_all[1:])
        parts = main.split()
        if len(parts) >= 3:
            three, letter, two = parts[0], parts[1], parts[2]
    else:
        main = text
        if '| ایران' in text:
            main, _, iran = text.partition('| ایران')
            iran = iran.strip()
        elif 'ایران' in text:
            main, _, iran = text.partition('ایران')
            iran = iran.strip()
        parts = main.split()
        if len(parts) >= 3:
            a, letter, b = parts[0], parts[1], parts[2]
            if len(a) <= 2 and len(b) >= 3:
                two, three = a, b
            else:
                three, two = a, b
    return two, letter, three, iran

STYLE = ("QFrame#IranPlate { background:#ffffff; border:3px solid #111; border-radius:8px; } "
         "QLabel { color:#111; background:transparent; } "
         "QLabel#PlateBlue { background:#1d4ed8; color:#fff; border-radius:4px; }")

class PlateWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('IranPlate')
        self.setStyleSheet(STYLE)
        self.setMinimumHeight(64)
        self.setLayoutDirection(Qt.RightToLeft)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        big = QFont('Tahoma', 16, QFont.Bold)
        self.iran_lbl = QLabel('ایران\n--')
        self.iran_lbl.setObjectName('PlateBlue')
        self.iran_lbl.setAlignment(Qt.AlignCenter)
        self.three_lbl = QLabel('---'); self.three_lbl.setFont(big)
        self.letter_lbl = QLabel('-'); self.letter_lbl.setFont(big)
        self.two_lbl = QLabel('--'); self.two_lbl.setFont(big)
        lay.addWidget(self.iran_lbl)
        lay.addWidget(self.three_lbl)
        lay.addWidget(self.letter_lbl)
        lay.addWidget(self.two_lbl)
        lay.addStretch()

    def set_plate(self, two, letter, three, iran):
        self.two_lbl.setText(to_fa(two) or '--')
        self.letter_lbl.setText((letter or '-').strip())
        self.three_lbl.setText(to_fa(three) or '---')
        self.iran_lbl.setText('ایران\n' + (to_fa(iran) or '--'))
