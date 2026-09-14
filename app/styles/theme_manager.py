# -*- coding: utf-8 -*-
# فایل: theme_manager.py
# این فایل به صورت خودکار توسط fix_theme.py ساخته شد

def get_light_theme():
    """استایل تم روشن - بدون استایل drop-down برای حفظ فلش کامبو باکس"""
    return (
        "QWidget{background:#e3e8ef;color:#243144;font-size:13px;} "
        "QMainWindow,QDialog{background:#e3e8ef;} "
        "QLabel{background:transparent;} "
        "QPushButton{background:#ffffff;border:1px solid #d9e1ec;border-radius:4px;padding:6px 16px;} "
        "QPushButton:hover{background:#eef4ff;border-color:#1f6feb;} "
        "QPushButton:pressed{background:#dbe7ff;} "
        "QPushButton:disabled{background:#eef1f5;color:#9aa7b8;} "
        "QPushButton#PrimaryButton{background:#2563eb;color:white;font-weight:bold;} "
        "QPushButton#PrimaryButton:hover{background:#1d4ed8;} "
        "QPushButton#SecondaryButton{background:#64748b;color:white;} "
        "QPushButton#SecondaryButton:hover{background:#475569;} "
        "QPushButton#SuccessButton{background:#16a34a;color:white;font-weight:bold;} "
        "QPushButton#SuccessButton:hover{background:#15803d;} "
        "QPushButton#DangerButton{background:#dc2626;color:white;font-weight:bold;} "
        "QPushButton#DangerButton:hover{background:#b91c1c;} "
        "QPushButton#PurpleButton{background:#9333ea;color:white;font-weight:bold;} "
        "QPushButton#PurpleButton:hover{background:#7e22ce;} "
        "QLineEdit,QTextEdit,QPlainTextEdit,QDateEdit,QComboBox,QSpinBox{background:#fdfeff;border:1.5px solid #b9c6d6;border-radius:4px;padding:5px 8px;min-height:30px;color:#243144;} "
        "QLineEdit:focus,QTextEdit:focus,QDateEdit:focus,QComboBox:focus{border-color:#1f6feb;} "
        "QComboBox QAbstractItemView{background:#ffffff;color:#243144;border:1px solid #d9e1ec;selection-background-color:#1f6feb;selection-color:#ffffff;} "
        "QTableWidget,QTableView{background:#ffffff;alternate-background-color:#f2f6fb;border:1px solid #d9e1ec;gridline-color:#e3eaf3;color:#243144;} "
        "QTableWidget::item:selected,QTableView::item:selected{background:#1f6feb;color:#fff;} "
        "QHeaderView::section{background:#eef2f7;border:none;padding:6px;font-weight:bold;color:#243144;} "
        "QMenuBar{background:#ffffff;border-bottom:1px solid #d9e1ec;color:#243144;} "
        "QMenuBar::item:selected{background:#eef4ff;} "
        "QMenu{background:#ffffff;border:1px solid #d9e1ec;color:#243144;} "
        "QMenu::item:selected{background:#1f6feb;color:#fff;} "
        "QTabWidget::pane{border:1px solid #d9e1ec;background:#ffffff;} "
        
        
        "QGroupBox{border:1px solid #d9e1ec;border-radius:4px;margin-top:10px;background:#ffffff;color:#243144;} "
        "QGroupBox::title{subcontrol-origin:margin;padding:0 8px;color:#1f6feb;font-weight:bold;} "
        "QScrollBar:vertical{background:#eef2f7;width:10px;border-radius:5px;} "
        "QScrollBar::handle:vertical{background:#c3cfdd;border-radius:5px;min-height:30px;} "
        "QScrollBar::handle:vertical:hover{background:#1f6feb;} "
        "QFrame#Card{background:#ffffff;border:1px solid #d9e1ec;border-radius:8px;padding:12px;} "
        "QLabel#Title{font-size:18px;font-weight:bold;color:#1e293b;} "
        "QLabel#Muted{color:#64748b;font-size:12px;} "
        "QLabel#Alert{color:#f59e0b;font-weight:bold;} "
        "QLabel#WarningLabel{color:#f59e0b;font-weight:bold;padding:8px;} "
        "QLabel#AvgPriceLabel{background:#fbbf24;color:#46505f;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#AvgPriceValue{background:#22c55e;color:#ffffff;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#IssuePctLabel{background:#fbbf24;color:#46505f;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#IssueCalcValue{background:#22c55e;color:#ffffff;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#VatAmountLabel{color:#9333ea;font-size:14px;font-weight:bold;min-width:180px;} "
        "QLabel#FinalTotalLabel{background:#22c55e;color:#ffffff;padding:8px 16px;font-weight:bold;font-size:15px;border-radius:4px;} "
        "QLabel#SuccessLabel{color:#10b981;font-size:18px;font-weight:bold;} "
        "QLineEdit#IssuePctEdit{background:#e8edf4;color:#243144;border:1px solid #8b5cf6;padding:4px;font-size:14px;} "
        "QLineEdit#ExtraCostsEdit{background:#e8edf4;color:#243144;border:1px solid #8b5cf6;padding:4px;} "
        "QListWidget{background:#ffffff;border:1px solid #d9e1ec;border-radius:4px;color:#243144;} "
        "QListWidget::item:selected{background:#1f6feb;color:#ffffff;} "
        "QTextBrowser{background:transparent;border:none;color:#243144;} "
        "QTextBrowser#PreviewBrowser{background:#ffffff;color:#000000;}"
    )


def get_dark_theme():
    """استایل تم دارک - بدون استایل drop-down برای حفظ فلش کامبو باکس"""
    return (
        "QWidget{background:#0f172a;color:#e2e8f0;font-size:13px;} "
        "QMainWindow,QDialog{background:#0f172a;} "
        "QLabel{background:transparent;color:#cbd5e1;} "
        "QPushButton{background:#1e293b;border:1px solid #334155;border-radius:4px;padding:6px 16px;color:#e2e8f0;} "
        "QPushButton:hover{background:#334155;border-color:#60a5fa;} "
        "QPushButton:pressed{background:#475569;} "
        "QPushButton:disabled{background:#1e293b;color:#64748b;} "
        "QPushButton#PrimaryButton{background:#2563eb;color:white;font-weight:bold;} "
        "QPushButton#PrimaryButton:hover{background:#1d4ed8;} "
        "QPushButton#SecondaryButton{background:#475569;color:white;} "
        "QPushButton#SecondaryButton:hover{background:#64748b;} "
        "QPushButton#SuccessButton{background:#16a34a;color:white;font-weight:bold;} "
        "QPushButton#SuccessButton:hover{background:#15803d;} "
        "QPushButton#DangerButton{background:#dc2626;color:white;font-weight:bold;} "
        "QPushButton#DangerButton:hover{background:#b91c1c;} "
        "QPushButton#PurpleButton{background:#9333ea;color:white;font-weight:bold;} "
        "QPushButton#PurpleButton:hover{background:#7e22ce;} "
        "QLineEdit,QTextEdit,QPlainTextEdit,QDateEdit,QComboBox,QSpinBox{background:#1e293b;border:1.5px solid #334155;border-radius:4px;padding:5px 8px;color:#f1f5f9;min-height:30px;} "
        "QLineEdit:focus,QTextEdit:focus,QDateEdit:focus,QComboBox:focus{border-color:#1f6feb;} "
        "QComboBox QAbstractItemView{background:#1e293b;color:#e2e8f0;border:1px solid #334155;selection-background-color:#1f6feb;selection-color:#ffffff;} "
        "QTableWidget,QTableView{background:#1e293b;alternate-background-color:#0f172a;border:1px solid #334155;gridline-color:#334155;color:#e2e8f0;} "
        "QTableWidget::item:selected,QTableView::item:selected{background:#1f6feb;color:#fff;} "
        "QHeaderView::section{background:#334155;border:none;padding:6px;font-weight:bold;color:#f1f5f9;} "
        "QMenuBar{background:#1e293b;border-bottom:1px solid #334155;color:#e2e8f0;} "
        "QMenuBar::item:selected{background:#334155;} "
        "QMenu{background:#1e293b;border:1px solid #334155;color:#e2e8f0;} "
        "QMenu::item:selected{background:#1f6feb;color:#fff;} "
        "QTabWidget::pane{border:1px solid #334155;background:#1e293b;} "
    "QTabBar::tab{padding:10px 28px;min-width:150px;background:#334155;border:1px solid #475569;border-radius:6px;color:#e2e8f0;font-size:13px;font-weight:bold;} "
    "QTabBar::tab:selected{background:#2563eb;border-color:#1d4ed8;color:#ffffff;} QTabBar::tab:hover:!selected{background:#475569;color:#f1f5f9;} "
        
        
        "QGroupBox{border:1px solid #334155;border-radius:4px;margin-top:10px;background:#1e293b;color:#e2e8f0;} "
        "QGroupBox::title{subcontrol-origin:margin;padding:0 8px;color:#60a5fa;font-weight:bold;} "
        "QScrollBar:vertical{background:#0f172a;width:10px;border-radius:5px;} "
        "QScrollBar::handle:vertical{background:#475569;border-radius:5px;min-height:30px;} "
        "QScrollBar::handle:vertical:hover{background:#1f6feb;} "
        "QFrame#Card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px;} "
        "QLabel#Title{font-size:18px;font-weight:bold;color:#f1f5f9;} "
        "QLabel#Muted{color:#94a3b8;font-size:12px;} "
        "QLabel#Alert{color:#f59e0b;font-weight:bold;} "
        "QLabel#WarningLabel{color:#f59e0b;font-weight:bold;padding:8px;} "
        "QLabel#AvgPriceLabel{background:#fbbf24;color:#46505f;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#AvgPriceValue{background:#22c55e;color:#ffffff;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#IssuePctLabel{background:#fbbf24;color:#46505f;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#IssueCalcValue{background:#22c55e;color:#ffffff;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#VatAmountLabel{color:#a78bfa;font-size:14px;font-weight:bold;min-width:180px;} "
        "QLabel#FinalTotalLabel{background:#22c55e;color:#ffffff;padding:8px 16px;font-weight:bold;font-size:15px;border-radius:4px;} "
        "QLabel#SuccessLabel{color:#10b981;font-size:18px;font-weight:bold;} "
        "QLineEdit#IssuePctEdit{background:#334155;color:#e2e8f0;border:1px solid #8b5cf6;padding:4px;font-size:14px;} "
        "QLineEdit#ExtraCostsEdit{background:#334155;color:#e2e8f0;border:1px solid #8b5cf6;padding:4px;} "
        "QListWidget{background:#1e293b;border:1px solid #334155;border-radius:4px;color:#e2e8f0;} "
        "QListWidget::item:selected{background:#1f6feb;color:#ffffff;} "
        "QTextBrowser{background:transparent;border:none;color:#e2e8f0;} "
        "QTextBrowser#PreviewBrowser{background:#1e293b;color:#e2e8f0;}"
    )


def apply_theme(app, theme="light"):
    """اعمال تم روی برنامه"""
    if not getattr(app, '_tab_fix', None):
        from PyQt5.QtCore import QObject, QEvent, Qt

        class _TabSizeFix(QObject):
            def eventFilter(self, o, e):
                if o.__class__.__name__ == 'QTabBar' and e.type() in (QEvent.Polish, QEvent.Show, QEvent.Resize):
                    o.setExpanding(False)
                    o.setElideMode(Qt.ElideNone)
                return False

        app._tab_fix = _TabSizeFix(app)
        app.installEventFilter(app._tab_fix)
    if theme == "dark":
        app.setStyleSheet(get_dark_theme())
    else:
        app.setStyleSheet(get_light_theme())

import json as _json
import os as _os
def _settings_path():
    return _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), 'data', 'settings.json')
def load_theme():
    try:
        with open(_settings_path(), encoding='utf-8') as f:
            return _json.load(f).get('theme', 'dark')
    except Exception:
        return 'dark'
def save_theme(theme):
    try:
        p = _settings_path(); d = {}
        if _os.path.exists(p):
            with open(p, encoding='utf-8') as f: d = _json.load(f)
        d['theme'] = theme
        with open(p, 'w', encoding='utf-8') as f: _json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
