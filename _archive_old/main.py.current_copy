# -*- coding: utf-8 -*-
"""
نقطه ورود اصلی سیستم انبارداری راد صنعت.

این فایل نسخه تمیز و اصلاح‌شده است:
- بلوک قدیمی screen_fit به‌طور کامل حذف شده است.
- تنظیمات High-DPI قبل از ایمپورت‌های Qt انجام می‌شود.
- پچ‌های پایین فایل (wh-patch، combo-refresh، trace monkeypatch) حفظ شده‌اند.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PySide2.QtCore import Qt
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QApplication, QDialog, QMessageBox

Qt.AA_EnableHighDpiScaling = True
Qt.AA_UseHighDpiPixmaps = True

from app.core.database import DatabaseManager
from app.styles.app_style import apply_style

DB_PATH = os.path.join(BASE_DIR, 'data', 'app.db')


def main():
    from app.views.login_window import LoginWindow
    from app.views.main_window import MainWindow

    app = QApplication(sys.argv)

    icon_path = os.path.join(BASE_DIR, 'rad_sanat_novin.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    apply_style(app)
    app.setLayoutDirection(Qt.RightToLeft)

    db = DatabaseManager(DB_PATH)
    db.initialize()

    login_dlg = LoginWindow(db)
    if login_dlg.exec_() != QDialog.Accepted:
        sys.exit(0)

    user_data = login_dlg.get_user_data()
    if not user_data:
        QMessageBox.critical(None, 'خطا', 'خطا در دریافت اطلاعات کاربر.')
        sys.exit(1)

    window = MainWindow(db, user_data)

    user_name = user_data.get('full_name', user_data.get('username', ''))
    window.setWindowTitle(f'سیستم انبارداری - {user_name}')
    window.show()

    from app.core import license_manager as _lm
    if not _lm.ensure_license(app):
        sys.exit(0)

    sys.exit(app.exec_())


try:
    import issue_wh_patch as _whp  # noqa: F401
    pass  # WH-PATCH-DISABLED
except Exception as _wh_exc:
    print('[wh-patch] skip:', _wh_exc)

try:
    import combo_refresh_patch as _crp
    _crp.apply()
except Exception as _cr_exc:
    print('[combo-refresh] skip:', _cr_exc)


# Trace monkeypatch: افزودن traceback به پیام‌های QMessageBox
def _make_messagebox_with_traceback(_orig_static):
    def _wrapped(*args, **kwargs):
        import traceback
        traceback.print_exc()
        return _orig_static(*args, **kwargs)
    return _wrapped

try:
    QMessageBox.critical = staticmethod(_make_messagebox_with_traceback(QMessageBox.critical))
    QMessageBox.warning = staticmethod(_make_messagebox_with_traceback(QMessageBox.warning))
    QMessageBox.information = staticmethod(_make_messagebox_with_traceback(QMessageBox.information))
except Exception:
    pass


# ------------------------- preview branch -------------------------

if __name__ == '__main__':
    if '--preview' in sys.argv:
        argv = sys.argv[sys.argv.index('--preview') + 1:]
        _path = argv[0] if argv else ''
        _title = argv[1] if len(argv) > 1 else 'پیش‌نمایش'
        try:
            from app.views.web_engine_preview_dialog import WebEnginePreviewDialog
            with open(_path, 'r', encoding='utf-8', errors='replace') as _f:
                _html = _f.read()
            _d = WebEnginePreviewDialog(_html, _title)
            _d.exec_()
        except Exception:
            pass
        sys.exit(0)

    main()
