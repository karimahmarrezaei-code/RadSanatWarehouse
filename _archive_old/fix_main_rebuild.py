# -*- coding: utf-8 -*-
"""بازنویسی تمیز main.py - اجرا: python fix_main_rebuild.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

CONTENT = '''# -*- coding: utf-8 -*-
"""نقطه ورود اصلی برنامه - نسخه بازنویسی‌شده تمیز"""
import sys
import os

def _auto_scale():
    try:
        _base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        _p = os.path.join(_base, 'scale.txt')
        if os.path.exists(_p):
            _v = open(_p, encoding='utf-8').read().strip()
            if _v:
                return float(_v)
        return 1.0
    except Exception:
        return 1.0

_AUTO_FACTOR = _auto_scale()

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QMainWindow,
                             QScrollArea, QVBoxLayout, QWidget, QTabWidget,
                             QTableWidget, QHeaderView, QComboBox)
from PyQt5.QtCore import Qt

COMPACT_QSS = """
QWidget { font-size: 11px; }
QLabel { font-size: 11px; }
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit { font-size: 11px; padding: 1px; max-height: 26px; }
QPushButton { font-size: 11px; padding: 4px 10px; max-height: 28px; }
QTableWidget, QTableView { font-size: 11px; }
QTabBar::tab { padding: 3px 10px; font-size: 11px; max-height: 24px; }
QGroupBox { font-size: 11px; }
QFrame#Card { padding: 6px; }
"""

def _compact_window(w):
    try:
        if QApplication.desktop().availableGeometry().height() >= 900:
            return
        if getattr(w, '_compact_done', False):
            return
        w._compact_done = True
        import re as _re
        from PyQt5.QtWidgets import QLayout
        for c in w.findChildren(QWidget):
            try:
                f = c.font()
                if f.pointSize() > 8:
                    f.setPointSize(max(8, f.pointSize() - 1)); c.setFont(f)
                if c.minimumHeight() == c.maximumHeight() and c.minimumHeight() > 52:
                    c.setFixedHeight(int(c.minimumHeight() * 0.68))
                ss = c.styleSheet()
                if ss and 'font-size' in ss:
                    ss = _re.sub(r'font-size:\\s*(\\d+)px', lambda m: f'font-size: {max(10, int(int(m.group(1)) * 0.75))}px', ss)
                    c.setStyleSheet(ss)
            except Exception:
                pass
        for lay in w.findChildren(QLayout):
            try:
                m = lay.contentsMargins()
                lay.setContentsMargins(int(m.left() * 0.45), int(m.top() * 0.45), int(m.right() * 0.45), int(m.bottom() * 0.45))
                if lay.spacing() > 4:
                    lay.setSpacing(int(lay.spacing() * 0.5))
            except Exception:
                pass
    except Exception:
        pass

def _safe_flags(w):
    try:
        f = w.windowFlags()
        f |= Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        f &= ~Qt.WindowContextHelpButtonHint
        if f != w.windowFlags():
            w.setWindowFlags(f)
        if w.minimumSize() == w.maximumSize():
            w.setMaximumSize(16777215, 16777215)
    except Exception:
        pass

def _norm_pallet_dict(d):
    try:
        import re as _re
        c = str(d.get('code', '')); n = str(d.get('name', ''))
        if _re.match(r'^\\d+(-\\d+)+$', c):
            m = _re.search(r'[A-Za-z]{2,}-\\d+', n)
            if m:
                d['code'] = m.group(0); d['name'] = n.replace(m.group(0), '').strip(' |-,')
    except Exception:
        pass

def _reserved_map(db):
    res = {}
    try:
        with db.connect() as cn:
            cn.row_factory = None
            for pid, q in cn.execute("SELECT oli.pallet_id, SUM(oli.qty) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE ol.load_status='OPEN' AND ol.is_active=1 GROUP BY oli.pallet_id").fetchall():
                res[pid] = int(q or 0)
    except Exception:
        pass
    return res

def _attach_pallet_guards(w):
    try:
        if getattr(w, '_pg_done', False):
            return
        w._pg_done = True
        if callable(getattr(w, '_load_pallets', None)):
            o = w._load_pallets
            def lp(*a, **k):
                o(*a, **k)
                try:
                    for it in getattr(w, 'pallets', []):
                        if isinstance(it, dict):
                            _norm_pallet_dict(it)
                        elif isinstance(it, tuple) and it and isinstance(it[0], dict):
                            _norm_pallet_dict(it[0])
                except Exception:
                    pass
            w._load_pallets = lp
        if callable(getattr(w, '_pallet_options', None)):
            o2 = w._pallet_options
            def po(*a, **k):
                res = o2(*a, **k)
                try:
                    rsv = _reserved_map(w.db)
                    out = []
                    for it in res:
                        if isinstance(it, tuple) and it and isinstance(it[0], dict):
                            d = it[0]; _norm_pallet_dict(d)
                            out.append((d, (it[1] or 0) - rsv.get(d.get('id'), 0)) + tuple(it[2:]))
                        else:
                            out.append(it)
                    ps = getattr(w, 'pallet_stock', None)
                    if isinstance(ps, dict):
                        for kk in list(ps.keys()):
                            ps[kk] = (ps[kk] or 0) - rsv.get(kk, 0)
                    return out
                except Exception:
                    return res
            w._pallet_options = po
    except Exception:
        pass

def _mk_sa(wgt):
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(wgt)
    sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    sa.setStyleSheet('QScrollBar:vertical{width:16px;background:#2a2f3a;}'
                     'QScrollBar::handle:vertical{min-height:48px;background:#7f8896;border-radius:8px;margin:3px;}'
                     'QScrollBar::handle:vertical:hover{background:#a8b0bc;}'
                     'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}')
    return sa

def _safe_fit(w):
    try:
        if not w.isWindow() or getattr(w, '_safe_wrapped', False):
            return
        scr = QApplication.desktop().availableGeometry()
        need = 0
        try:
            lay = w.layout()
            if lay is not None:
                need = lay.totalMinimumSize().height()
            if isinstance(w, QMainWindow) and w.centralWidget() is not None and w.centralWidget().layout() is not None:
                need = max(need, w.centralWidget().layout().totalMinimumSize().height())
        except Exception:
            need = 0
        if max(w.sizeHint().height(), need) > scr.height():
            w._safe_wrapped = True
            if isinstance(w, QMainWindow) and w.centralWidget() is not None:
                cw = w.takeCentralWidget()
                sa = _mk_sa(cw); w.setCentralWidget(sa)
            elif w.layout() is not None:
                lay = w.layout()
                inner = QWidget(); inner.setLayout(lay)
                sa = _mk_sa(inner)
                outer = QVBoxLayout(w); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(sa)
        for tb in w.findChildren(QTableWidget):
            try:
                if isinstance(tb.cellWidget(0, 1), QComboBox) or tb is getattr(w, 'lines_table', None) or tb is getattr(w, 'items_table', None):
                    tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
                    tb.setColumnWidth(1, 430)
            except Exception:
                pass
    except Exception:
        pass

_orig_show = QWidget.show
def _safe_show(self):
    try:
        if self.isWindow() and not getattr(self, '_safe_done', False):
            self._safe_done = True
            scr = QApplication.desktop().availableGeometry()
            w = min(self.width(), scr.width()); h = min(self.height(), scr.height())
            if (w, h) != (self.width(), self.height()):
                self.resize(w, h)
            _safe_flags(self)
            _compact_window(self)
            _attach_pallet_guards(self)
            _safe_fit(self)
            try:
                lt = getattr(self, 'lines_table', None)
                if lt is not None and lt.rowCount() == 0 and callable(getattr(self, 'add_line_row', None)):
                    self.add_line_row()
            except Exception:
                pass
            try:
                ps = getattr(self, 'pallet_service', None)
                if ps is not None and callable(getattr(ps, 'reload', None)):
                    ps.reload()
                    if callable(getattr(self, '_refresh_pallet_combos', None)):
                        self._refresh_pallet_combos()
            except Exception:
                pass
            for tw in self.findChildren(QTabWidget):
                tw.currentChanged.connect(lambda _i, _w=self: _safe_fit(_w))
    except Exception:
        pass
    return _orig_show(self)
QWidget.show = _safe_show

_orig_exec = QDialog.exec_
def _safe_exec(self):
    try:
        _safe_show(self)
    except Exception:
        pass
    return _orig_exec(self)
QDialog.exec_ = _safe_exec

from app.core.database import DatabaseManager
from app.styles.app_style import apply_style

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'app.db')

def main():
    from app.ui.login_window import LoginWindow
    from app.ui.main_window import MainWindow
    app = QApplication(sys.argv)
    _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rad_sanat_novin.ico')
    if os.path.exists(_ico):
        app.setWindowIcon(QIcon(_ico))
    try:
        import importlib.util as _ilu
        _b = os.path.dirname(os.path.abspath(__file__))
        cand = [os.path.join(_b, 'app', 'styles', 'theme_manager.py'), os.path.join(_b, 'theme_manager.py')]
        if getattr(sys, 'frozen', False):
            _e = os.path.dirname(sys.executable)
            cand += [os.path.join(_e, 'theme_manager.py'), os.path.join(_e, '_internal', 'app', 'styles', 'theme_manager.py')]
        for p in cand:
            if not os.path.exists(p):
                continue
            try:
                spec = _ilu.spec_from_file_location('theme_manager_force', p)
                mod = _ilu.module_from_spec(spec); spec.loader.exec_module(mod)
                if hasattr(mod, 'apply_theme') and hasattr(mod, 'load_theme'):
                    sys.modules['theme_manager'] = mod
                    sys.modules['app.styles.theme_manager'] = mod
                    break
            except Exception:
                continue
        apply_style(app)
    except Exception as e:
        print('[style] skip:', e)
        try:
            import traceback
            open('STYLE_ERROR.txt', 'w', encoding='utf-8').write(traceback.format_exc())
        except Exception:
            pass
    try:
        import ctypes
        if ctypes.windll.user32.GetSystemMetrics(1) < 900:
            app.setStyleSheet(app.styleSheet() + COMPACT_QSS)
    except Exception:
        pass
    app.setStyleSheet(app.styleSheet() + ' QTableWidget QComboBox { font-size: 12px; } ')
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
    from app.ui import issue_wh_patch as _whp
except Exception as _wh_exc:
    print('[wh-patch] skip:', _wh_exc)

try:
    from app.ui import combo_refresh_patch as _crp
    _crp.apply()
except Exception as _cr_exc:
    print('[combo-refresh] skip:', _cr_exc)

try:
    from PyQt5.QtWidgets import QMessageBox as _QMB
    import traceback as _tb
    for _m in ('critical', 'warning', 'information'):
        _orig = getattr(_QMB, _m)
        def _make(o):
            def _wrap(*a, **k):
                _tb.print_exc()
                return o(*a, **k)
            return _wrap
        setattr(_QMB, _m, staticmethod(_make(_orig)))
except Exception:
    pass

if __name__ == '__main__':
    if '--preview' in sys.argv:
        _i = sys.argv.index('--preview')
        _path = sys.argv[_i + 1] if _i + 1 < len(sys.argv) else ''
        _title = sys.argv[_i + 2] if _i + 2 < len(sys.argv) else ''
        try:
            from app.ui.webengine_preview import WebEnginePreviewDialog
            _html = open(_path, encoding='utf-8', errors='replace').read()
            _d = WebEnginePreviewDialog(_html, _title)
            _d.exec_()
        except Exception:
            pass
        sys.exit(0)
    main()
'''

mp = os.path.join(ROOT, 'main.py')
open(mp, 'w', encoding='utf-8').write(CONTENT)
py_compile.compile(mp, doraise=True)
print('1) main.py بازنویسی تمیز شد ✔')

db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
good = os.path.join(ROOT, 'theme_manager.py')
if os.path.exists(good):
    for tgt in (os.path.join(DST, 'theme_manager.py'),
                os.path.join(DST, '_internal', 'theme_manager.py'),
                os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db_dist)
    print('2) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
input('Enter...')