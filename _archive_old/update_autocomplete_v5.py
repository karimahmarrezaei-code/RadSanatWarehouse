# -*- coding: utf-8 -*-
"""
update_autocomplete_v5.py - رفع قطعی F2 (نسخه ۳)
==================================================

مشکل نسخه ۲: eventFilter روی خود فرم، رویدادهای فرزندان (فیلدهای متنی) را
نمی‌گیرد — برای همین F2 کار نمی‌کرد.

راه‌حل نسخه ۴:
  ۱) QShortcut برای F2 — میانبر استاندارد Qt که در سطح فرم، هر جا فوکوس
     باشد کار می‌کند (مطمئن‌ترین راه)
  ۲) فیلتر روی QApplication — پشتیبان: هر F2 در کل برنامه گرفته می‌شود
  ۳) گزارش نصب در کنسول: تعداد فیلدهای نصب‌شده را چاپ می‌کند
     تا ببینیم نصب واقعاً انجام شده یا نه
  ۴) دکمه ✕ کنار هر فیلد (به‌جای تکیه فقط به F2)

اجرا (از پوشه F:\\warehouse_app — برنامه بسته باشد):
    py -X utf8 .\\update_autocomplete_v5.py

بعدش:
    py -X utf8 .\\main.py
"""
import os
import re
import shutil
from datetime import datetime

SKIP = {'venv', '.venv', '__pycache__', 'node_modules', '.git',
        'test_docimg', 'test_issue_percent', 'migration', 'backup_before_update',
        'junk', '_junk', 'Junk', '_junk_junk', 'backup_14050518'}

FORM_FILES = ['receipt_manager_window.py', 'issue_manager_window.py']


def log(*a):
    print(' '.join(str(x) for x in a))


def hr():
    print('-' * 66)


def find_file(name):
    for base, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in SKIP]
        if name in files:
            path = os.path.join(base, name)
            rel = path.replace('\\', '/')
            if '.bak' not in rel and 'backup' not in rel.lower():
                return path
    return None


def compile_ok(path):
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        return True, ''
    except Exception as e:
        return False, str(e).split('\n')[0][:150]


# ============================================================
# محتوای کامل نسخه ۳ auto_complete.py
# ============================================================
AUTO_COMPLETE_SOURCE = r'''# -*- coding: utf-8 -*-
"""
auto_complete.py - تکمیل خودکار (Auto-Complete / Suggestion) با ذخیره در JSON
==============================================================================
نسخه ۴:
  • F2 با QShortcut (مطمئن در سطح فرم) + فیلتر روی QApplication (پشتیبان)
  • دکمه ✕ کنار هر فیلد
  • گزارش نصب در کنسول (تعداد فیلدها)
  • ذخیره‌سازی: data/autocomplete.json
"""
import json
import os

from PyQt5.QtCore import Qt, QObject, QEvent, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QCompleter, QLineEdit, QTextEdit, QDialog, QVBoxLayout,
    QHBoxLayout, QListWidget, QPushButton, QLabel, QListWidgetItem,
    QApplication, QMessageBox, QShortcut,
)

def _default_path():
    """مسیر مطلق data/autocomplete.json — مستقل از پوشه اجرا"""
    here = os.path.dirname(os.path.abspath(__file__))   # .../app/core
    root = os.path.dirname(os.path.dirname(here))       # پوشه پروژه
    return os.path.join(root, 'data', 'autocomplete.json')


DEFAULT_PATH = _default_path()


class AutoCompleteStore:
    def __init__(self, path=None, max_per_field=200):
        self.path = path or DEFAULT_PATH
        self.max_per_field = max_per_field
        self._data = {}
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, encoding='utf-8') as f:
                    self._data = json.load(f)
                if not isinstance(self._data, dict):
                    self._data = {}
        except Exception:
            self._data = {}

    def save(self):
        try:
            d = os.path.dirname(self.path)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, field):
        vals = self._data.get(field, [])
        return vals if isinstance(vals, list) else []

    def add(self, field, text):
        text = (text or '').strip()
        if not text:
            return
        vals = self.get(field)
        if text in vals:
            vals.remove(text)
        vals.insert(0, text)
        self._data[field] = vals[:self.max_per_field]
        self.save()

    def remove(self, field, text):
        vals = self.get(field)
        if text in vals:
            vals.remove(text)
            self._data[field] = vals
            self.save()
            return True
        return False

    def clear_field(self, field):
        if field in self._data:
            del self._data[field]
            self.save()

    def suggestions(self, field, prefix, limit=10):
        prefix = (prefix or '').strip().lower()
        vals = self.get(field)
        if not prefix:
            return vals[:limit]
        return [v for v in vals if v.lower().startswith(prefix)][:limit]

    def stats(self):
        total = sum(len(v) for v in self._data.values())
        return '{} فیلد / {} عبارت'.format(len(self._data), total)


def field_key(widget):
    name = (widget.objectName() or '').strip()
    if name and name != 'qt_spinbox_lineedit':
        return name
    if isinstance(widget, QLineEdit):
        ph = widget.placeholderText()
        if ph:
            return ph
    return 'field'


def _is_password(widget):
    """آیا فیلد رمز است؟ (سازگار با نسخه‌های مختلف PyQt5)"""
    try:
        if hasattr(widget, 'isPassword'):
            return bool(widget.isPassword())
        if hasattr(widget, 'echoMode'):
            from PyQt5.QtWidgets import QLineEdit
            return widget.echoMode() == QLineEdit.Password
    except Exception:
        pass
    return False



class CompleterFilter(QObject):
    def __init__(self, widget, store, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.store = store
        self.field = field_key(widget)
        self.completer = QCompleter(self)
        self.completer.setWidget(widget)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchStartsWith)
        self.completer.setMaxVisibleItems(10)
        self.completer.activated.connect(self._insert_completion)
        widget.installEventFilter(self)
        self._setup_context_menu()

    def _current_prefix(self):
        if isinstance(self.widget, QLineEdit):
            return self.widget.text()
        cursor = self.widget.textCursor()
        before = self.widget.toPlainText()[:cursor.position()]
        parts = before.split()
        return parts[-1] if parts else ''

    def _insert_completion(self, completion):
        if isinstance(self.widget, QLineEdit):
            self.widget.setText(completion)
            return
        cursor = self.widget.textCursor()
        pos = cursor.position()
        text = self.widget.toPlainText()
        start = pos
        while start > 0 and not text[start - 1].isspace():
            start -= 1
        cursor.setPosition(start)
        cursor.setPosition(pos, cursor.KeepAnchor)
        cursor.insertText(completion)
        self.widget.setTextCursor(cursor)

    def _update(self):
        prefix = self._current_prefix()
        if not prefix:
            self.completer.popup().hide()
            return
        items = self.store.suggestions(self.field, prefix)
        if not items:
            self.completer.popup().hide()
            return
        from PyQt5.QtCore import QStringListModel
        self.completer.setModel(QStringListModel(items, self.completer))
        self.completer.complete()

    def _save_on_focus_out(self):
        try:
            if isinstance(self.widget, QLineEdit):
                self.store.add(self.field, self.widget.text())
            else:
                self.store.add(self.field, self.widget.toPlainText())
        except Exception:
            pass

    def open_manager(self):
        # ابتدا متن فعلی فیلد را ذخیره کن تا در مدیر دیده شود
        self._save_on_focus_out()
        dlg = ManageDialog(self.store, self.field, self.widget)
        dlg.exec_()

    def save_now(self):
        self._save_on_focus_out()

    def _setup_context_menu(self):
        """منوی راست‌کلیک: مدیریت پیشنهادها"""
        try:
            self.widget.setContextMenuPolicy(Qt.CustomContextMenu)
            self.widget.customContextMenuRequested.connect(self._show_context_menu)
        except Exception:
            pass

    def _show_context_menu(self, pos):
        try:
            from PyQt5.QtWidgets import QMenu
            menu = QMenu(self.widget)
            act = menu.addAction('مدیریت پیشنهادها (F2)')
            act.triggered.connect(lambda _=False: self.open_manager())
            menu.exec_(self.widget.mapToGlobal(pos))
        except Exception:
            pass

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.KeyPress:
            if event.key() == Qt.Key_F2:
                self.open_manager()
                return True
            if event.key() == Qt.Key_Space and (event.modifiers() & Qt.ControlModifier):
                self.open_manager()
                return True
            if self.completer.popup().isVisible():
                key = event.key()
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                    completion = self.completer.currentCompletion()
                    if completion:
                        self._insert_completion(completion)
                    self.completer.popup().hide()
                    return True
                if key == Qt.Key_Escape:
                    self.completer.popup().hide()
                    return True
        elif t == QEvent.KeyRelease:
            if event.key() not in (Qt.Key_Return, Qt.Key_Enter):
                QTimer.singleShot(0, self._update)
        elif t == QEvent.FocusOut:
            QTimer.singleShot(0, self._save_on_focus_out)
        return super().eventFilter(obj, event)


class ManageDialog(QDialog):
    def __init__(self, store, field, parent=None):
        super().__init__(parent)
        self.store = store
        self.field = field
        self.setWindowTitle('پیشنهادهای ذخیره‌شده: ' + field)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(420, 420)
        lay = QVBoxLayout(self)
        title = QLabel('عبارات ذخیره‌شده برای «{}»:'.format(field))
        title.setStyleSheet('font-weight: bold; font-size: 13px;')
        lay.addWidget(title)
        self.list_widget = QListWidget()
        self._reload()
        lay.addWidget(self.list_widget)
        btns = QHBoxLayout()
        self.del_btn = QPushButton('حذف انتخاب‌شده')
        self.del_btn.clicked.connect(self._delete_selected)
        self.del_all_btn = QPushButton('پاک کردن همه')
        self.del_all_btn.clicked.connect(self._clear_all)
        self.close_btn = QPushButton('بستن')
        self.close_btn.clicked.connect(self.accept)
        btns.addWidget(self.del_btn)
        btns.addWidget(self.del_all_btn)
        btns.addStretch()
        btns.addWidget(self.close_btn)
        lay.addLayout(btns)

    def _reload(self):
        self.list_widget.clear()
        for item in self.store.get(self.field):
            it = QListWidgetItem(item)
            self.list_widget.addItem(it)
        if self.list_widget.count() == 0:
            self.list_widget.addItem('(هیچ عبارتی ذخیره نشده)')
            self.list_widget.item(0).setFlags(Qt.NoItemFlags)

    def _delete_selected(self):
        sel = self.list_widget.selectedItems()
        for it in sel:
            self.store.remove(self.field, it.text())
        self._reload()

    def _clear_all(self):
        self.store.clear_field(self.field)
        self._reload()


def _make_x_icon():
    pm = QPixmap(16, 16)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor('#94a3b8'))
    f = QFont()
    f.setPixelSize(13)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, '✕')
    p.end()
    return QIcon(pm)


def _add_side_button_for_textedit(edit, flt):
    try:
        parent = edit.parentWidget()
        if parent is None:
            return
        lay = parent.layout()
        if lay is None:
            return
        btn = QPushButton('✕')
        btn.setFixedWidth(26)
        btn.setToolTip('مدیریت پیشنهادهای این فیلد')
        btn.setStyleSheet('color:#94a3b8; background:transparent; border:none; font-weight:bold;')
        btn.clicked.connect(lambda _=False, f=flt: f.open_manager())
        idx = lay.indexOf(edit)
        if idx >= 0:
            lay.insertWidget(idx + 1, btn)
    except Exception:
        pass


class AppLevelFilter(QObject):
    """نصب روی QApplication — هر F2 در کل برنامه را می‌گیرد (پشتیبان)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = {}  # window -> {'filters_by_widget': {...}, 'store': store}

    def register_window(self, window, filters_by_widget, store):
        self.registry[window] = {
            'filters_by_widget': filters_by_widget,
            'store': store,
        }

    def _handle_f2(self, obj):
        """اگر obj یک فیلد متنی شناخته‌شده است، مدیرش را باز کن"""
        for win, info in self.registry.items():
            flt = info['filters_by_widget'].get(obj)
            if flt is not None:
                flt.open_manager()
                return True
        return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_F2:
            focus = QApplication.focusWidget()
            try:
                print('[auto-complete] APP-F2 | obj =', obj.__class__.__name__,
                      '| focus =', focus.__class__.__name__ if focus else 'None')
            except Exception:
                pass
            # ۱) اگر فوکوس فیلد متنی شناخته‌شده است
            if self._handle_f2(focus):
                return True
            # ۲) اگر خود obj فیلد متنی است
            if self._handle_f2(obj):
                return True
            # ۳) پیام راهنما
            try:
                QMessageBox.information(
                    None, 'پیشنهادها',
                    'ابتدا روی یک فیلد متنی (مثل توضیحات) کلیک کنید،\n'
                    'سپس F2 را بزنید یا دکمه ✕ را فشار دهید.',
                )
            except Exception:
                pass
            return True
        return super().eventFilter(obj, event)


def install_autocomplete(window):
    """
    همه فیلدهای متنی فرم را تزئین می‌کند.
    F2: با QShortcut (سطح فرم) + AppLevelFilter (سطح برنامه).
    """
    try:
        store = AutoCompleteStore()
        filters = []
        filters_by_widget = {}

        for w in window.findChildren(QTextEdit):
            if not w.isReadOnly():
                flt = CompleterFilter(w, store)
                filters.append(flt)
                filters_by_widget[w] = flt
                _add_side_button_for_textedit(w, flt)

        for w in window.findChildren(QLineEdit):
            if not w.isReadOnly() and not _is_password(w):
                flt = CompleterFilter(w, store)
                filters.append(flt)
                filters_by_widget[w] = flt
                w.addAction(_make_x_icon(), QLineEdit.TrailingPosition)
                for action in w.actions():
                    action.triggered.connect(lambda _=False, f=flt: f.open_manager())

        # ذخیره همه هنگام کلیک روی دکمه‌های ثبت/ذخیره
        def save_all():
            for flt in filters:
                try:
                    flt.save_now()
                except Exception:
                    pass

        for btn in window.findChildren(QPushButton):
            txt = (btn.text() or '')
            if any(k in txt for k in ('ثبت', 'ذخیره', 'ایجاد', 'افزودن', 'اضافه', 'ثبت و')):
                try:
                    btn.clicked.connect(lambda _=False, s=save_all: s())
                except Exception:
                    pass

        # ---------- F2: QShortcut با ApplicationShortcut (هر جا فوکوس باشد) ----------
        def _open_manager_for_focus():
            focus = QApplication.focusWidget()
            try:
                print('[auto-complete] F2 pressed | focus =', focus.__class__.__name__ if focus else 'None')
            except Exception:
                pass
            flt = filters_by_widget.get(focus)
            if flt is not None:
                try:
                    print('[auto-complete] opening manager for field:', flt.field)
                except Exception:
                    pass
                flt.open_manager()
                return
            try:
                QMessageBox.information(
                    window, 'پیشنهادها',
                    'ابتدا روی یک فیلد متنی (مثل توضیحات) کلیک کنید،\n'
                    'سپس F2 را بزنید یا دکمه ✕ را فشار دهید.',
                )
            except Exception:
                pass

        shortcut = QShortcut(QKeySequence(Qt.Key_F2), window)
        shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(_open_manager_for_focus)
        window._ac_f2_shortcut = shortcut

        # Ctrl+Space هم میانبر دوم
        sc2 = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Space), window)
        sc2.setContext(Qt.ApplicationShortcut)
        sc2.activated.connect(_open_manager_for_focus)
        window._ac_ctrl_space = sc2

        # ---------- پشتیبان: فیلتر سطح برنامه ----------
        app = QApplication.instance()
        if app is not None:
            app_filter = getattr(app, '_ac_app_filter', None)
            if app_filter is None:
                app_filter = AppLevelFilter()
                app.installEventFilter(app_filter)
                app._ac_app_filter = app_filter
            app_filter.register_window(window, filters_by_widget, store)
            window._ac_app_filter = app_filter

        window._ac_filters = filters
        window._ac_store = store

        try:
            names = []
            for w in filters_by_widget:
                nm = w.objectName() or w.placeholderText() or w.__class__.__name__
                names.append(nm)
            print('[auto-complete] installed on {}: {} QLineEdit + {} QTextEdit | fields = {}'.format(
                window.__class__.__name__,
                sum(1 for w in filters_by_widget if isinstance(w, QLineEdit)),
                sum(1 for w in filters_by_widget if isinstance(w, QTextEdit)),
                names,
            ))
        except Exception:
            print('[auto-complete] installed on', window.__class__.__name__)
        return store
    except Exception as e:
        print('[auto-complete] install error:', repr(e))
        return None
'''


# ============================================================
# بلوک نصب جدید
# ============================================================
INSTALL_BLOCK = '''        try:
            from app.core.auto_complete import install_autocomplete
            install_autocomplete(self)
        except Exception as _ac_err:
            print('[auto-complete] install error:', _ac_err)
'''


def replace_install_block(content):
    """بلوک نصب قبلی را با نسخه جدید جایگزین می‌کند (خط‌به‌خط، حفظ indent، CRLF-safe)"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    replaced = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if (stripped == 'try:' and i + 3 < n
                and 'from app.core.auto_complete import install_autocomplete' in lines[i + 1]
                and 'install_autocomplete(self)' in lines[i + 2]
                and lines[i + 3].strip().startswith('except Exception')):
            ind = line[:len(line) - len(line.lstrip())]
            j = i + 4
            if j < n and (lines[j].strip() in ('pass',) or lines[j].strip().startswith('print(')):
                j += 1
            new_lines.append(ind + 'try:')
            new_lines.append(ind + '    from app.core.auto_complete import install_autocomplete')
            new_lines.append(ind + '    install_autocomplete(self)')
            new_lines.append(ind + 'except Exception as _ac_err:')
            new_lines.append(ind + "    print('[auto-complete] install error:', _ac_err)")
            i = j
            replaced += 1
            continue
        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines), replaced


def add_install_block(content):
    """اگر نصب نباشد، به انتهای __init__ اضافه می‌کند (روش امن)"""
    lines = content.split('\n')
    init_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^\s*def __init__\(', line):
            init_idx = i
            break
    if init_idx is None:
        return content, 0
    init_indent = len(lines[init_idx]) - len(lines[init_idx].lstrip())
    end_idx = len(lines)
    for i in range(init_idx + 1, len(lines)):
        line = lines[i]
        if re.match(r'^\s*def ', line) or re.match(r'^(class |if __name__|@)', line):
            indent = len(line) - len(line.lstrip())
            if indent <= init_indent:
                end_idx = i
                break
    insert_after = None
    for i in range(end_idx - 1, init_idx, -1):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith('#') or stripped.endswith(':') or stripped.endswith('\\'):
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent > init_indent:
            insert_after = i
            break
    if insert_after is None:
        insert_after = end_idx - 1
    block_lines = INSTALL_BLOCK.rstrip('\n').split('\n')
    new_lines = lines[:insert_after + 1] + block_lines + lines[insert_after + 1:]
    return '\n'.join(new_lines), 1


def update_core():
    target = os.path.join('app', 'core', 'auto_complete.py')
    if os.path.exists(target):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = target + '.v4_' + stamp + '.bak'
        shutil.copy2(target, bak)
        log('   🔄 نسخه قبلی بکاپ شد: ' + os.path.basename(bak))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8') as f:
        f.write(AUTO_COMPLETE_SOURCE)
    ok, err = compile_ok(target)
    log('   ✅ auto_complete.py نسخه ۵ — سینتکس: ' + ('سالم' if ok else '❌ ' + str(err)[:100]))
    return ok


def patch_form(path):
    with open(path, encoding='utf-8') as f:
        content = f.read()

    if 'install_autocomplete(self)' in content:
        content, n = replace_install_block(content)
        if n:
            log('   • بلوک نصب به‌روز شد: ' + path)
        else:
            log('   ℹ️ نصب موجود است: ' + path)
            return
    else:
        content, n = add_install_block(content)
        if n:
            log('   • بلوک نصب اضافه شد: ' + path)
        else:
            log('   ⚠️ __init__ پیدا نشد: ' + path)
            return

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = path + '.acv3_' + stamp + '.bak'
    shutil.copy2(path, bak)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    ok, err = compile_ok(path)
    if ok:
        log('   ✅ ' + path + ' — سینتکس سالم')
    else:
        shutil.copy2(bak, path)
        os.remove(bak)
        log('   ❌ ' + path + ' — خطا داد؛ به حالت قبل برگشتم: ' + str(err)[:120])


def main():
    log('=== به‌روزرسانی auto-complete (نسخه ۵: F2 قطعی (ApplicationShortcut) + راست‌کلیک + Ctrl+Space) ===')
    log('⚠️  برنامه باید بسته باشد!')
    hr()

    log('گام ۱: به‌روزرسانی app/core/auto_complete.py')
    update_core()
    log()

    log('گام ۲: به‌روزرسانی بلوک نصب در فرم‌ها')
    for name in FORM_FILES:
        path = find_file(name)
        if path:
            log('  فایل: ' + path)
            patch_form(path)
        else:
            log('  ⚠️ پیدا نشد: ' + name)
    log()

    hr()
    log('تمام! حالا برنامه را اجرا کن:  py -X utf8 .\\main.py')
    log('در کنسول باید ببینی:  [auto-complete] installed on ... : ... QLineEdit + ... QTextEdit, F2 ready')
    log('سپس روی یک فیلد متنی کلیک کن و F2 را بزن.')


if __name__ == '__main__':
    main()
