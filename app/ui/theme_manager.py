# -*- coding: utf-8 -*-
# فایل: theme_manager.py

def get_light_theme():
    """استایل تم روشن - با رنگ‌بندی دکمه‌ها و کامبو باکس خاکستری"""
    return (
        "QWidget{background:#e3e8ef;color:#243144;font-size:13px;} "
        "QMainWindow,QDialog{background:#e3e8ef;} "
        "QLabel{background:transparent;} "
        
        # دکمه‌های پیش‌فرض (خاکستری روشن)
        "QPushButton{background:#f1f5f9;border:1px solid #cbd5e1;border-radius:4px;padding:6px 16px;color:#243144;} "
        "QPushButton:hover{background:#e2e8f0;border-color:#64748b;} "
        "QPushButton:pressed{background:#cbd5e1;} "
        "QPushButton:disabled{background:#f8fafc;color:#64748b;} "
        
        # دکمه اصلی (آبی)
        "QPushButton#PrimaryButton{background:#2563eb;color:white;font-weight:bold;} "
        "QPushButton#PrimaryButton:hover{background:#1d4ed8;} "
        
        # دکمه ثانویه (خاکستری تیره)
        "QPushButton#SecondaryButton{background:#64748b;color:white;} "
        "QPushButton#SecondaryButton:hover{background:#475569;} "
        
        # دکمه موفقیت (سبز)
        "QPushButton#SuccessButton{background:#16a34a;color:white;font-weight:bold;} "
        "QPushButton#SuccessButton:hover{background:#15803d;} "
        
        # دکمه خطر (قرمز)
        "QPushButton#DangerButton{background:#dc2626;color:white;font-weight:bold;} "
        "QPushButton#DangerButton:hover{background:#b91c1c;} "
        
        # دکمه بنفش
        "QPushButton#PurpleButton{background:#9333ea;color:white;font-weight:bold;} "
        "QPushButton#PurpleButton:hover{background:#7e22ce;} "
        
        # فیلدهای ورودی و کامبو باکس (خاکستری روشن)
        "QLineEdit,QTextEdit,QPlainTextEdit,QDateEdit,QSpinBox{background:#f8fafc;border:1.5px solid #cbd5e1;border-radius:4px;padding:5px 8px;min-height:30px;color:#243144;} "
        "QComboBox{background:#f1f5f9;border:1.5px solid #cbd5e1;border-radius:4px;padding:5px 8px;min-height:30px;color:#243144;} "
        "QLineEdit:focus,QTextEdit:focus,QDateEdit:focus,QComboBox:focus{border-color:#2563eb;} "
        "QComboBox QAbstractItemView{background:#f1f5f9;color:#243144;border:1px solid #cbd5e1;selection-background-color:#2563eb;selection-color:#ffffff;} "
        
        # جدول
        "QTableWidget,QTableView{background:#ffffff;alternate-background-color:#f8fafc;border:1px solid #cbd5e1;gridline-color:#e2e8f0;color:#243144;} "
        "QTableWidget::item:selected,QTableView::item:selected{background:#2563eb;color:#fff;} "
        "QHeaderView::section{background:#f1f5f9;border:none;padding:6px;font-weight:bold;color:#243144;} "
        
        # منو
        "QMenuBar{background:#ffffff;border-bottom:1px solid #cbd5e1;color:#243144;} "
        "QMenuBar::item:selected{background:#e2e8f0;} "
        "QMenu{background:#ffffff;border:1px solid #cbd5e1;color:#243144;} "
        "QMenu::item:selected{background:#2563eb;color:#fff;} "
        
        # تب
        "QTabWidget::pane{border:1px solid #cbd5e1;background:#ffffff;} "
    "QTabBar::tab{padding:10px 28px;min-width:150px;background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;color:#243144;font-size:13px;font-weight:bold;} "
    "QTabBar::tab:selected{background:#2563eb;border-color:#1d4ed8;color:#ffffff;} QTabBar::tab:hover:!selected{background:#e2e8f0;color:#243144;} "
        
        
        
        # گروه
        "QGroupBox{border:1px solid #cbd5e1;border-radius:4px;margin-top:10px;background:#ffffff;color:#243144;} "
        "QGroupBox::title{subcontrol-origin:margin;padding:0 8px;color:#2563eb;font-weight:bold;} "
        
        # اسکرول
        "QScrollBar:vertical{background:#f1f5f9;width:10px;border-radius:5px;} "
        "QScrollBar::handle:vertical{background:#cbd5e1;border-radius:5px;min-height:30px;} "
        "QScrollBar::handle:vertical:hover{background:#64748b;} "
        
        # کارت
        "QFrame#Card{background:#ffffff;border:1px solid #cbd5e1;border-radius:8px;padding:12px;} "
        
        # لیبل‌ها
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
        
        # فیلدهای خاص
        "QLineEdit#IssuePctEdit{background:#f1f5f9;color:#243144;border:1px solid #8b5cf6;padding:4px;font-size:14px;} "
        "QLineEdit#ExtraCostsEdit{background:#f1f5f9;color:#243144;border:1px solid #8b5cf6;padding:4px;} "
        
        # لیست
        "QListWidget{background:#ffffff;border:1px solid #cbd5e1;border-radius:4px;color:#243144;} "
        "QListWidget::item:selected{background:#2563eb;color:#ffffff;} "
        
        # مرورگر متن
        "QTextBrowser{background:transparent;border:none;color:#243144;} "
        "QTextBrowser#PreviewBrowser{background:#ffffff;color:#000000;}"


        # استایل خاص برای فرم About
        "QDialog#AboutDialog{background:#0d2a50;} "
        "QDialog#AboutDialog QLabel{color:#ffffff;} "
        "QDialog#AboutDialog QLabel#AboutTitle{color:#ffffff;font-size:20px;font-weight:bold;} "
        "QDialog#AboutDialog QLabel#AboutCompany{color:#f59e0b;font-size:17px;font-weight:bold;} "
        "QDialog#AboutDialog QLabel#AboutVersion{color:#60a5fa;font-size:12px;} "
        "QDialog#AboutDialog QLabel#AboutBody{color:#cbd5e1;font-size:13px;}"
    )



def get_dark_theme():
    """استایل تم دارک - با رنگ‌بندی دکمه‌ها"""
    return (
        "QWidget{background:#0f172a;color:#e2e8f0;font-size:13px;} "
        "QMainWindow,QDialog{background:#0f172a;} "
        "QLabel{background:transparent;color:#cbd5e1;} "
        
        # دکمه‌های پیش‌فرض (خاکستری تیره)
        "QPushButton{background:#1e293b;border:1px solid #334155;border-radius:4px;padding:6px 16px;color:#e2e8f0;} "
        "QPushButton:hover{background:#334155;border-color:#475569;} "
        "QPushButton:pressed{background:#475569;} "
        "QPushButton:disabled{background:#0f172a;color:#64748b;} "
        
        # دکمه اصلی (آبی)
        "QPushButton#PrimaryButton{background:#2563eb;color:white;font-weight:bold;} "
        "QPushButton#PrimaryButton:hover{background:#1d4ed8;} "
        
        # دکمه ثانویه (خاکستری)
        "QPushButton#SecondaryButton{background:#475569;color:white;} "
        "QPushButton#SecondaryButton:hover{background:#64748b;} "
        
        # دکمه موفقیت (سبز)
        "QPushButton#SuccessButton{background:#16a34a;color:white;font-weight:bold;} "
        "QPushButton#SuccessButton:hover{background:#15803d;} "
        
        # دکمه خطر (قرمز)
        "QPushButton#DangerButton{background:#dc2626;color:white;font-weight:bold;} "
        "QPushButton#DangerButton:hover{background:#b91c1c;} "
        
        # دکمه بنفش
        "QPushButton#PurpleButton{background:#9333ea;color:white;font-weight:bold;} "
        "QPushButton#PurpleButton:hover{background:#7e22ce;} "
        
        # فیلدهای ورودی و کامبو باکس
        "QLineEdit,QTextEdit,QPlainTextEdit,QDateEdit,QSpinBox{background:#1e293b;border:1.5px solid #334155;border-radius:4px;padding:5px 8px;color:#e2e8f0;min-height:30px;} "
        "QComboBox{background:#1e293b;border:1.5px solid #334155;border-radius:4px;padding:5px 8px;color:#e2e8f0;min-height:30px;} "
        "QLineEdit:focus,QTextEdit:focus,QDateEdit:focus,QComboBox:focus{border-color:#2563eb;} "
        "QComboBox QAbstractItemView{background:#1e293b;color:#e2e8f0;border:1px solid #334155;selection-background-color:#2563eb;selection-color:#ffffff;} "
        
        # جدول
        "QTableWidget,QTableView{background:#1e293b;alternate-background-color:#0f172a;border:1px solid #334155;gridline-color:#334155;color:#e2e8f0;} "
        "QTableWidget::item:selected,QTableView::item:selected{background:#2563eb;color:#fff;} "
        "QHeaderView::section{background:#334155;border:none;padding:6px;font-weight:bold;color:#f1f5f9;} "
        
        # منو
        "QMenuBar{background:#1e293b;border-bottom:1px solid #334155;color:#e2e8f0;} "
        "QMenuBar::item:selected{background:#334155;} "
        "QMenu{background:#1e293b;border:1px solid #334155;color:#e2e8f0;} "
        "QMenu::item:selected{background:#2563eb;color:#fff;} "
        
        # تب
        "QTabWidget::pane{border:1px solid #334155;background:#1e293b;} "
    "QTabBar::tab{padding:10px 28px;min-width:150px;background:#334155;border:1px solid #475569;border-radius:6px;color:#e2e8f0;font-size:13px;font-weight:bold;} "
    "QTabBar::tab:selected{background:#2563eb;border-color:#1d4ed8;color:#ffffff;} QTabBar::tab:hover:!selected{background:#475569;color:#f1f5f9;} "
        
        
        
        # گروه
        "QGroupBox{border:1px solid #334155;border-radius:4px;margin-top:10px;background:#1e293b;color:#e2e8f0;} "
        "QGroupBox::title{subcontrol-origin:margin;padding:0 8px;color:#60a5fa;font-weight:bold;} "
        
        # اسکرول
        "QScrollBar:vertical{background:#0f172a;width:10px;border-radius:5px;} "
        "QScrollBar::handle:vertical{background:#475569;border-radius:5px;min-height:30px;} "
        "QScrollBar::handle:vertical:hover{background:#2563eb;} "
        
        # کارت
        "QFrame#Card{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:12px;} "
        
        # لیبل‌ها
        "QLabel#Title{font-size:18px;font-weight:bold;color:#f1f5f9;} "
        "QLabel#Muted{color:#64748b;font-size:12px;} "
        "QLabel#Alert{color:#f59e0b;font-weight:bold;} "
        "QLabel#WarningLabel{color:#f59e0b;font-weight:bold;padding:8px;} "
        "QLabel#AvgPriceLabel{background:#fbbf24;color:#46505f;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#AvgPriceValue{background:#22c55e;color:#ffffff;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#IssuePctLabel{background:#fbbf24;color:#46505f;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#IssueCalcValue{background:#22c55e;color:#ffffff;padding:6px 14px;font-weight:bold;font-size:14px;border-radius:4px;} "
        "QLabel#VatAmountLabel{color:#a78bfa;font-size:14px;font-weight:bold;min-width:180px;} "
        "QLabel#FinalTotalLabel{background:#22c55e;color:#ffffff;padding:8px 16px;font-weight:bold;font-size:15px;border-radius:4px;} "
        "QLabel#SuccessLabel{color:#10b981;font-size:18px;font-weight:bold;} "
        
        # فیلدهای خاص
        "QLineEdit#IssuePctEdit{background:#334155;color:#e2e8f0;border:1px solid #8b5cf6;padding:4px;font-size:14px;} "
        "QLineEdit#ExtraCostsEdit{background:#334155;color:#e2e8f0;border:1px solid #8b5cf6;padding:4px;} "
        
        # لیست
        "QListWidget{background:#1e293b;border:1px solid #334155;border-radius:4px;color:#e2e8f0;} "
        "QListWidget::item:selected{background:#2563eb;color:#ffffff;} "
        
        # مرورگر متن
        "QTextBrowser{background:transparent;border:none;color:#e2e8f0;} "
        "QTextBrowser#PreviewBrowser{background:#1e293b;color:#e2e8f0;}"


        # استایل خاص برای فرم About در تم دارک
        "QDialog#AboutDialog{background:#0d2a50;} "
        "QDialog#AboutDialog QLabel{color:#ffffff;} "
        "QDialog#AboutDialog QLabel#AboutTitle{color:#ffffff;font-size:20px;font-weight:bold;} "
        "QDialog#AboutDialog QLabel#AboutCompany{color:#f59e0b;font-size:17px;font-weight:bold;} "
        "QDialog#AboutDialog QLabel#AboutVersion{color:#60a5fa;font-size:12px;} "
        "QDialog#AboutDialog QLabel#AboutBody{color:#cbd5e1;font-size:13px;}"
    )
   


def apply_theme(app, theme='dark'):
    try:
        app.app_theme = theme
    except Exception:
        pass
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