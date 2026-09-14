# -*- coding: utf-8 -*-
"""نقطه ورود اصلی برنامه - نسخه بازنویسی‌شده تمیز (تک‌نسخه‌ای از پچ‌های امن)"""
# WEBENGINE-INIT-FIX: وب‌انجین باید قبل از QApplication مقداردهی شود
try:  # WEBENGINE-INIT-FIX
    from PyQt5.QtCore import Qt, QObject, QEvent, QObject, QEvent as _Qt_AA  # WEBENGINE-INIT-FIX
    from PyQt5.QtWidgets import QApplication as _QApp_AA  # WEBENGINE-INIT-FIX
    _QApp_AA.setAttribute(_Qt_AA.AA_ShareOpenGLContexts, True)  # WEBENGINE-INIT-FIX
    import PyQt5.QtWebEngineWidgets  # noqa  # WEBENGINE-INIT-FIX
except Exception:  # WEBENGINE-INIT-FIX
    pass  # WEBENGINE-INIT-FIX

import sys
import os

# اطمینان از دسترسی به پکیج app حتی هنگام اجرا از مسیر دیگر
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
from PyQt5.QtCore import Qt, QObject, QEvent

os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')  # PREV-FIX

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
                    ss = _re.sub(r'font-size:\s*(\d+)px', lambda m: f'font-size: {max(10, int(int(m.group(1)) * 0.75))}px', ss)
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
        f |= Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
        f &= ~Qt.WindowContextHelpButtonHint
        w.setWindowFlags(f)
        # آزاد کردن قفل ماکسیمم‌سازی
        w.setMaximumSize(16777215, 16777215)
    except Exception:
        pass


def _norm_pallet_dict(d):
    try:
        import re as _re
        c = str(d.get('code', '')); n = str(d.get('name', ''))
        if _re.match(r'^\d+(-\d+)+$', c):
            m = _re.search(r'[A-Za-z]{2,}-\d+', n)
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
                            out.append((d, it[1]) + tuple(it[2:]))
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



class _WheelForward(QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() != QEvent.Wheel:
                return False
            w = obj
            if not isinstance(w, QWidget) or isinstance(w, QScrollArea):
                return False
            # اگر خود کنترل اسکرول داخلی دارد (مثل جداول پرینت یا ادیتور بزرگ)، مداخله نکن
            try:
                v = w.verticalScrollBar() if hasattr(w, 'verticalScrollBar') else None
                if v is not None and v.minimum() != v.maximum():
                    return False
            except Exception:
                pass

            p = w.parentWidget()
            while p is not None and not isinstance(p, QScrollArea):
                p = p.parentWidget()
            if p is None:
                return False
            
            sb = p.verticalScrollBar()
            if sb and sb.isVisible():
                delta = ev.angleDelta().y()
                step = sb.singleStep() or 30
                if delta < 0:
                    sb.setValue(sb.value() + step)
                elif delta > 0:
                    sb.setValue(sb.value() - step)
                return True
        except Exception:
            pass
        return False

_wheel_forwarder = _WheelForward()


# --- LAPTOP & COMBOBOX SCROLL FIX ---
class _SmartGlobalFilter(QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Wheel:
                # الف) بی‌حس کردن چرخ موس روی کمبوباکس در حالت بسته
                if isinstance(obj, QComboBox):
                    v = obj.view()
                    if v is None or not v.isVisible():
                        ev.ignore()
                        return True
        except Exception:
            pass
        return False

_smart_global_filter = _SmartGlobalFilter()

def _auto_fit_tab_scroll(tab_widget):
    """تجهیز خودکار تب‌های بلند به اسکرول‌بار نرم"""
    try:
        scr = QApplication.desktop().availableGeometry()
        for idx in range(tab_widget.count()):
            w = tab_widget.widget(idx)
            if w is not None and not isinstance(w, QScrollArea) and not getattr(w, '_wrapped_sa', False):
                if w.sizeHint().height() > (scr.height() - 120):
                    sa = _mk_sa(w)
                    sa._wrapped_sa = True
                    tab_widget.removeTab(idx)
                    tab_widget.insertTab(idx, sa, tab_widget.tabText(idx))
    except Exception:
        pass
# ------------------------------------


# --- COMBOBOX WHEEL GUARD ---
class _ComboWheelGuard(QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Wheel and isinstance(obj, QComboBox):
                v = obj.view()
                # اگر لیست بازشو بسته است، رویداد چرخ را خنثی کن
                if v is None or not v.isVisible():
                    ev.ignore()
                    return True
        except Exception:
            pass
        return False

_combo_wheel_guard = _ComboWheelGuard()

def _protect_combos(parent_widget):
    try:
        for cb in parent_widget.findChildren(QComboBox):
            if not getattr(cb, '_wheel_guarded', False):
                cb._wheel_guarded = True
                cb.installEventFilter(_combo_wheel_guard)
    except Exception:
        pass
# ----------------------------

def _safe_fit(w):
    _protect_combos(w)
    # گارد امن برای جلوگیری از تغییر سایز پنجره‌های حساس
    cls_name = w.__class__.__name__
    if 'Login' in cls_name or 'Preview' in cls_name or getattr(w, '_no_compact', False):
        return
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView as _QWV
        if w.findChildren(_QWV):
            return
        from PyQt5.QtWidgets import QDialog as _QD, QTextBrowser as _QTB
        if isinstance(w, _QD) and w.findChildren(_QTB):
            return
    except Exception:
        pass
    try:
        if not w.isWindow() or getattr(w, '_safe_wrapped', False):
            return
        scr = QApplication.desktop().availableGeometry()
        need = 0
        try:
            lay = w.layout()
            if lay is not None:
                need = lay.totalMinimumSize().height()
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
                if tb is getattr(w, 'lines_table', None) or tb is getattr(w, 'items_table', None):
                    tb.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
                    tb.setColumnWidth(1, 430)
            except Exception:
                pass
    except Exception:
        pass


# ------------------------------------------------------------------
# SAFEPATCH-V2: فقط یک نسخه امن از show/exec_ (بدون تکرار و بدون بازگشت)
# ------------------------------------------------------------------
def _is_skip_window(w):
    """پنجره‌های حساس که نباید دستکاری شوند (Login/Preview/_no_compact)"""
    cls_name = w.__class__.__name__
    return ('Login' in cls_name) or ('Preview' in cls_name) or getattr(w, '_no_compact', False)


# ذخیره‌ی امن متدهای اصلی؛ فقط اگر از قبل ذخیره نشده باشند (جلوگیری از بازگشت)
if not hasattr(QWidget, '_orig_show'):
    QWidget._orig_show = QWidget.show
if not hasattr(QDialog, '_orig_exec_'):
    QDialog._orig_exec_ = QDialog.exec_

_orig_show = QWidget._orig_show
_orig_exec = QDialog._orig_exec_


def _safe_show(self):
    """نمایش امن پنجره: پنجره‌های حساس مستقیماً با show اصلی نمایش داده می‌شوند."""
    try:
        if _is_skip_window(self):
            return _orig_show(self)
        if self.isWindow() and not getattr(self, '_safe_done', False):
            self._safe_done = True
            scr = QApplication.desktop().availableGeometry()
            w_size = min(self.width(), scr.width())
            h_size = min(self.height(), scr.height())
            if (w_size, h_size) != (self.width(), self.height()):
                self.resize(w_size, h_size)
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
                    try:  # ONE-STOCK
                        from app.core.stock_service import free_stock_map as _fsm  # ONE-STOCK
                        _m7 = _fsm(self.db)  # ONE-STOCK
                        for _d6 in (getattr(self, 'pallet_stock', None), getattr(ps, 'pallet_stock', None)):  # ONE-STOCK
                            if isinstance(_d6, dict):  # ONE-STOCK
                                _d6.clear(); _d6.update(_m7)  # ONE-STOCK
                    except Exception:  # ONE-STOCK
                        pass  # ONE-STOCK
                    if callable(getattr(self, '_refresh_pallet_combos', None)):
                        self._refresh_pallet_combos()
            except Exception:
                pass
            for tw in self.findChildren(QTabWidget):
                tw.currentChanged.connect(lambda _i, _w=self: _safe_fit(_w))
    except Exception:
        pass
    return _orig_show(self)


def _safe_exec(self):
    """اجرای امن دیالوگ: مستقیماً exec_ اصلی (بدون عبور از _safe_show تا بازگشت رخ ندهد)"""
    return _orig_exec(self)


QWidget.show = _safe_show
QDialog.exec_ = _safe_exec

# ------------------------------------------------------------------

from app.core.database import DatabaseManager
from app.styles.app_style import apply_style

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'app.db')


def main():
    from app.ui.login_window import LoginWindow
    from app.ui.main_window import MainWindow
    app = QApplication(sys.argv)
    try:
        app.installEventFilter(_smart_global_filter)
    except Exception:
        pass
    try:
        app.installEventFilter(_wheel_forwarder)
    except Exception:
        pass
    _ico = ''
    try:
        import glob as _gb
        _b0 = os.path.dirname(os.path.abspath(__file__))
        _c0 = _gb.glob(os.path.join(_b0, '*.ico')) + _gb.glob(os.path.join(_b0, '_internal', '*.ico'))
        if _c0:
            _ico = _c0[0]
    except Exception:
        pass
    if _ico and os.path.exists(_ico):
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
    try:
        if _ico:
            login_dlg.setWindowIcon(QIcon(_ico))
    except Exception:
        pass
    # Login پنجره حساس است؛ نمایش مستقیم با show اصلی (بدون پچ)
    try:
        QWidget._orig_show(login_dlg)
    except Exception:
        pass
    if login_dlg.exec_() != QDialog.Accepted:
        sys.exit(0)
    user_data = login_dlg.get_user_data()
    if not user_data:
        QMessageBox.critical(None, 'خطا', 'خطا در دریافت اطلاعات کاربر.')
        sys.exit(1)
    window = MainWindow(db, user_data)
    try:
        if _ico:
            window.setWindowIcon(QIcon(_ico))
    except Exception:
        pass
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
    if '--preview' in sys.argv:  # ARGV-FIX
        _html = ''  # ARGV-FIX
        _title = 'پیش‌نمایش سند'  # ARGV-FIX
        _args = sys.argv[sys.argv.index('--preview') + 1:]  # ARGV-FIX
        for _a in _args:  # ARGV-FIX
            try:  # ARGV-FIX
                if not _html and os.path.exists(_a) and _a.lower().endswith(('.html', '.htm', '.txt')):  # ARGV-FIX
                    with open(_a, encoding='utf-8', errors='replace') as _f:  # ARGV-FIX
                        _html = _f.read()  # ARGV-FIX
                elif not _html and '<' in _a and '>' in _a:  # ARGV-FIX
                    _html = _a  # ARGV-FIX
                elif '<' not in _a and not _a.lower().endswith(('.html', '.htm', '.txt')) and len(_a) < 200:  # ARGV-FIX
                    _title = _a  # ARGV-FIX
            except Exception:  # ARGV-FIX
                pass  # ARGV-FIX
        if not _html:  # ARGV-FIX
            for _a in _args:  # ARGV-FIX
                try:  # ARGV-FIX
                    if os.path.exists(_a):  # ARGV-FIX
                        with open(_a, encoding='utf-8', errors='replace') as _f:  # ARGV-FIX
                            _html = _f.read()  # ARGV-FIX
                            break  # ARGV-FIX
                except Exception:  # ARGV-FIX
                    pass  # ARGV-FIX
        _app = QApplication(sys.argv)  # ARGV-FIX
        try:  # ARGV-FIX
            from app.ui.theme_manager import apply_theme as _at  # ARGV-FIX
            _at(_app)  # ARGV-FIX
        except Exception:  # ARGV-FIX
            pass  # ARGV-FIX
        # اولویت با نسخه WebEngine محلی است؛ در نبود آن، نسخه جایگزین استفاده می‌شود
        _HtmlPreviewDialog = None
        try:
            from webengine_preview import HtmlPreviewDialog as _HtmlPreviewDialog  # LOCAL-FAVOR
        except Exception:
            try:
                from app.ui.webengine_preview import HtmlPreviewDialog as _HtmlPreviewDialog  # LOCAL-FAVOR
            except Exception:
                pass
        if _HtmlPreviewDialog is None:
            try:
                from app.ui.html_preview_dialog import HtmlPreviewDialog as _HtmlPreviewDialog  # FALLBACK
            except Exception:
                try:
                    from html_preview_dialog import HtmlPreviewDialog as _HtmlPreviewDialog  # FALLBACK
                except Exception:
                    _HtmlPreviewDialog = None
        if _HtmlPreviewDialog is None:
            print('[preview] no preview dialog module available')
            sys.exit(1)
        _d = _HtmlPreviewDialog(_html, _title)  # ARGV-FIX
        _d.exec_()  # ARGV-FIX
        sys.exit(0)  # ARGV-FIX
    main()
