# -*- coding: utf-8 -*-
def apply_style(app, theme=None):
    from PyQt5.QtGui import QFont
    try:
        from app.styles.theme_manager import apply_theme, load_theme
    except Exception:
        from theme_manager import apply_theme, load_theme
    f = QFont('Vazirmatn', 10)
    f.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(f)
    apply_theme(app, theme or load_theme())
