# -*- coding: utf-8 -*-
"""رنگ هوشمند بر اساس تم فعال"""
def is_dark() -> bool:
    try:
        from PyQt5.QtWidgets import QApplication
        return getattr(QApplication.instance(), 'app_theme', 'dark') == 'dark'
    except Exception:
        return False
def txt() -> str:
    return '#e2e8f0' if is_dark() else '#243144'
