# -*- coding: utf-8 -*-
"""
auto_complete.py - تکمیل خودکار با ذخیره‌سازی عبارتی/خطی در JSON
=====================================================
• F2 / Ctrl+Space / دکمه ✕ : پاپ‌آپ مستقل لیست عبارات (قابل انتخاب)
• حین تایپ: پیشنهاد خودکار با QCompleter
• ذخیره‌سازی: QLineEdit ← کل متن یک عبارت | QTextEdit ← هر خط یک عبارت
• منوی راست‌کلیک استاندارد + گزینه مدیریت
• دیالوگ مدیریت: دبل‌کلیک یا «درج در فیلد» برای انتخاب عبارت
"""

import json
import os

from PyQt5.QtCore import Qt, QObject, QEvent, QTimer, QPoint, QStringListModel
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QKeySequence, QTextCursor
from PyQt5.QtWidgets import (
    QCompleter, QLineEdit, QTextEdit, QDialog, QVBoxLayout,
    QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel,
    QApplication, QMessageBox, QShortcut, QAbstractSpinBox, QComboBox,
    QAbstractItemView,
)


def _default_path():
    here = os.path.dirname(os.path.abspath(__file__))   # .../app/core
    root = os.path.dirname(os.path.dirname(here))       # پوشه پروژه
    return os.path.join(root, 'data', 'autocomplete.json')


DEFAULT_PATH = _default_path()

_MAX_PHRASE_LEN = 200


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

    def add_many(self, field, texts):
        vals = self.get(field)
        changed = False
        for text in texts:
            text = (text or '').strip()
            if not text:
                continue
            if text in vals:
                vals.remove(text)
            vals.insert(0, text)
            changed = True
        if changed:
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

    def suggestions(self, field, prefix, limit=20):
        prefix = (prefix or '').strip().lower()
        vals = self.get(field)
        if not prefix:
            return vals[:limit]
        return [v for v in vals if v.lower().startswith(prefix)][:limit]


def field_key(widget):
    name = (widget.objectName() or '').strip()
    if name and name != 'qt_spinbox_lineedit':
        return name
    if isinstance(widget, QLineEdit):
        ph = widget.placeholderText().strip()
        if ph:
            return ph
    return 'field'


def _is_password(widget):
    try:
        return widget.echoMode() in (
            QLineEdit.Password, QLineEdit.NoEcho, QLineEdit.PasswordEchoOnEdit
        )
    except Exception:
        return False


class _SuggestionPopup(QListWidget):
    """پاپ‌آپ مستقل لیست پیشنهادها."""

    def __init__(self):
        super().__init__()
        self.on_close_cb = None

    def closeEvent(self, event):
        try:
            if self.on_close_cb:
                self.on_close_cb()
        except Exception:
            pass
        super().closeEvent(event)


class CompleterFilter(QObject):
    def __init__(self, widget, store, field=None, parent=None):
        super().__init__(parent)

        self.widget = widget
        self.store = store
        self.field = field or field_key(widget)
        self._applying = False

        self.completer = QCompleter(self)
        self.completer.setWidget(widget)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchStartsWith)
        self.completer.setMaxVisibleItems(10)

        try:
            self.completer.popup().setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass

        self.completer.activated[str].connect(self._insert_completion)

        widget.installEventFilter(self)
        widget.textChanged.connect(self._on_text_changed)
        self._setup_context_menu()

    # ------------------------------------------------------------------
    # تشخیص متن و محدوده تکمیل
    # ------------------------------------------------------------------

    def _text_and_pos(self):
        if isinstance(self.widget, QLineEdit):
            return self.widget.text(), self.widget.cursorPosition()
        cursor = self.widget.textCursor()
        return self.widget.toPlainText(), cursor.position()

    def _current_prefix(self):
        text, pos = self._text_and_pos()
        before = text[:pos]

        if isinstance(self.widget, QLineEdit):
            return before.strip()

        sep = max(before.rfind('\n'), before.rfind('\u2029'))
        return before[sep + 1:].strip()

    def _completion_range(self):
        text, pos = self._text_and_pos()

        if isinstance(self.widget, QLineEdit):
            return text, 0, pos

        before = text[:pos]
        sep = max(before.rfind('\n'), before.rfind('\u2029'))
        start = sep + 1
        while start < pos and text[start].isspace():
            start += 1
        return text, start, pos

    # ------------------------------------------------------------------
    # پیشنهاد حین تایپ (QCompleter)
    # ------------------------------------------------------------------

    def _on_text_changed(self):
        if self._applying:
            return
        QTimer.singleShot(0, self._update)

    def _update(self):
        if self._applying:
            return
        try:
            if not self.widget.hasFocus():
                return
        except Exception:
            return

        prefix = self._current_prefix()
        if not prefix:
            try:
                self.completer.popup().hide()
            except Exception:
                pass
            return

        items = self.store.suggestions(self.field, prefix, limit=20)
        self._show_completer_popup(items, prefix)

    def _show_completer_popup(self, items, prefix):
        try:
            popup = self.completer.popup()
        except Exception:
            popup = None

        if not items:
            if popup is not None:
                popup.hide()
            return False

        old_model = self.completer.model()
        model = QStringListModel(items, self.completer)
        self.completer.setModel(model)
        self.completer.setCompletionPrefix(prefix)

        if old_model is not None and old_model is not model:
            try:
                old_model.setParent(None)
                old_model.deleteLater()
            except Exception:
                pass

        try:
            if popup is not None:
                popup.setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass

        try:
            self.completer.complete()
        except Exception:
            pass

        popup = self.completer.popup()
        if popup is not None and model.rowCount() > 0:
            popup.setCurrentIndex(model.index(0, 0))
            popup.raise_()
        return True

    # ------------------------------------------------------------------
    # نمایش لیست با F2 / ✕ (پاپ‌آپ مستقل و تضمینی)
    # ------------------------------------------------------------------

    def show_suggestions(self):
        prefix = self._current_prefix()
        items = self.store.suggestions(self.field, prefix, limit=20)
        if not items:
            items = self.store.suggestions(self.field, '', limit=20)
        if not items:
            try:
                QMessageBox.information(
                    self.widget, 'پیشنهادها',
                    'برای این فیلد هنوز عبارتی ذخیره نشده است.'
                )
            except Exception:
                pass
            return False

        self._show_list_popup(items)
        return True

    def _show_list_popup(self, items):
        popup = _SuggestionPopup()
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setLayoutDirection(Qt.RightToLeft)
        popup.setStyleSheet(
            'QListWidget { background:#1e293b; color:#e2e8f0; border:1px solid #8b5cf6; '
            'font-size:13px; } QListWidget::item { padding:5px; } '
            'QListWidget::item:selected { background:#8b5cf6; color:#ffffff; }'
        )

        for it in items:
            popup.addItem(QListWidgetItem(it))
        if popup.count():
            popup.setCurrentRow(0)

        def _refocus():
            try:
                self.widget.setFocus()
            except Exception:
                pass

        popup.on_close_cb = _refocus

        def _use(text):
            try:
                popup.on_close_cb = None
                popup.close()
            except Exception:
                pass
            self._insert_completion(text)
            _refocus()

        popup.itemClicked.connect(lambda it: _use(it.text()))
        popup.itemActivated.connect(lambda it: _use(it.text()))

        # موقعیت ثابت و قابل اتکا: زیرِ خودِ فیلد
        top_left = self.widget.mapToGlobal(QPoint(0, self.widget.height()))
        width = max(self.widget.width(), 250)

        row_h = 30
        popup.setFixedWidth(width)
        popup.setFixedHeight(min(len(items), 10) * row_h + 8)
        popup.move(top_left)
        popup.show()
        popup.raise_()

    # ------------------------------------------------------------------
    # ذخیره‌سازی عبارتی / خطی
    # ------------------------------------------------------------------

    def save_now(self):
        try:
            if isinstance(self.widget, QLineEdit):
                text = self.widget.text().strip()
                if text and len(text) <= _MAX_PHRASE_LEN:
                    self.store.add(self.field, text)
            else:
                lines = [ln.strip() for ln in self.widget.toPlainText().split('\n')]
                lines = [ln for ln in lines if ln and len(ln) <= _MAX_PHRASE_LEN]
                if lines:
                    self.store.add_many(self.field, list(reversed(lines)))
        except Exception:
            pass

    def open_manager(self):
        self.save_now()
        dlg = ManageDialog(self.store, self.field, self.widget, filter_obj=self)
        dlg.exec_()

    def insert_phrase(self, phrase):
        """درج عبارت انتخاب‌شده از دیالوگ مدیریت در فیلد."""
        try:
            self.widget.setFocus()
            if isinstance(self.widget, QLineEdit):
                self.widget.setText(phrase)
            else:
                cursor = self.widget.textCursor()
                cursor.insertText(phrase)
                self.widget.setTextCursor(cursor)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # منوی راست‌کلیک
    # ------------------------------------------------------------------

    def _setup_context_menu(self):
        try:
            self.widget.setContextMenuPolicy(Qt.CustomContextMenu)
            self.widget.customContextMenuRequested.connect(self._show_context_menu)
        except Exception:
            pass

    def _show_context_menu(self, pos):
        try:
            menu = self.widget.createStandardContextMenu()
            menu.addSeparator()
            act1 = menu.addAction('نمایش پیشنهادها (F2)')
            act1.triggered.connect(lambda _=False: self.show_suggestions())
            act2 = menu.addAction('مدیریت پیشنهادها')
            act2.triggered.connect(lambda _=False: self.open_manager())
            menu.exec_(self.widget.mapToGlobal(pos))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # درج پیشنهاد انتخاب‌شده
    # ------------------------------------------------------------------

    def _insert_completion(self, completion):
        if not completion:
            return
        self._applying = True
        try:
            text, start, end = self._completion_range()
            if isinstance(self.widget, QLineEdit):
                new_text = text[:start] + completion + text[end:]
                self.widget.setText(new_text)
                self.widget.setCursorPosition(len(completion))
            else:
                cursor = self.widget.textCursor()
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                cursor.insertText(completion)
                self.widget.setTextCursor(cursor)
        finally:
            self._applying = False
            try:
                self.completer.popup().hide()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Event Filter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        t = event.type()

        if t == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            if key == Qt.Key_F2:
                self.show_suggestions()
                return True

            if key == Qt.Key_Space and (modifiers & Qt.ControlModifier):
                self.show_suggestions()
                return True

            popup = self.completer.popup()
            if popup is not None and popup.isVisible():
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                    completion = self.completer.currentCompletion()
                    if completion:
                        self._insert_completion(completion)
                        return True
                    popup.hide()
                    return False
                if key == Qt.Key_Escape:
                    popup.hide()
                    return True

        elif t == QEvent.FocusOut:
            QTimer.singleShot(0, self.save_now)

        return super().eventFilter(obj, event)


class ManageDialog(QDialog):
    def __init__(self, store, field, parent=None, filter_obj=None):
        super().__init__(parent)
        self.store = store
        self.field = field
        self.filter_obj = filter_obj
        self.setWindowTitle('پیشنهادهای ذخیره‌شده: ' + field)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(460, 420)

        lay = QVBoxLayout(self)
        title = QLabel('عبارات ذخیره‌شده برای «{}»: (دبل‌کلیک = درج در فیلد)'.format(field))
        title.setStyleSheet('font-weight: bold; font-size: 13px;')
        lay.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self._insert_selected)
        self._reload()
        lay.addWidget(self.list_widget)

        btns = QHBoxLayout()
        self.insert_btn = QPushButton('درج در فیلد')
        self.insert_btn.clicked.connect(lambda _=False: self._insert_selected())
        self.del_btn = QPushButton('حذف انتخاب‌شده')
        self.del_btn.clicked.connect(self._delete_selected)
        self.del_all_btn = QPushButton('پاک کردن همه')
        self.del_all_btn.clicked.connect(self._clear_all)
        self.close_btn = QPushButton('بستن')
        self.close_btn.clicked.connect(self.accept)

        btns.addWidget(self.insert_btn)
        btns.addWidget(self.del_btn)
        btns.addWidget(self.del_all_btn)
        btns.addStretch()
        btns.addWidget(self.close_btn)
        lay.addLayout(btns)

        if self.filter_obj is None:
            self.insert_btn.hide()

    def _reload(self):
        self.list_widget.clear()
        for item in self.store.get(self.field):
            self.list_widget.addItem(QListWidgetItem(item))
        if self.list_widget.count() == 0:
            self.list_widget.addItem('(هیچ عبارتی ذخیره نشده)')
            self.list_widget.item(0).setFlags(Qt.NoItemFlags)

    def _insert_selected(self, item=None):
        it = item or self.list_widget.currentItem()
        if not it or not self.filter_obj:
            return
        text = it.text()
        if not text or text.startswith('(هیچ'):
            return
        self.accept()
        self.filter_obj.insert_phrase(text)

    def _delete_selected(self):
        for it in self.list_widget.selectedItems():
            self.store.remove(self.field, it.text())
        self._reload()

    def _clear_all(self):
        reply = QMessageBox.question(
            self, 'تایید', 'همه عبارات ذخیره‌شده این فیلد حذف شوند؟',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
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
    """دکمه ✕ داخلِ کادرِ QTextEdit (گوشه بالا-چپ) → نمایش لیست قابل انتخاب."""
    try:
        if edit.property('_ac_side_button_added'):
            return
        btn = QPushButton('✕', edit)          # فرزندِ خودِ تکست‌ادیت → داخل کادر
        btn.setFixedSize(22, 22)
        btn.setFocusPolicy(Qt.NoFocus)        # فوکوسِ فیلد را ندزدد
        btn.setToolTip('نمایش پیشنهادها (F2)')
        btn.setStyleSheet(
            'QPushButton { color:#94a3b8; background:rgba(148,163,184,40); '
            'border:none; border-radius:4px; font-weight:bold; }'
            'QPushButton:hover { background:rgba(148,163,184,90); color:#ffffff; }'
        )
        btn.clicked.connect(lambda _=False, f=flt: f.show_suggestions())
        btn.move(4, 4)
        btn.raise_()
        edit.setProperty('_ac_side_button_added', True)
    except Exception:
        pass


def _find_filter_for_widget(widget, filters_by_widget):
    if widget is None:
        return None
    flt = filters_by_widget.get(widget)
    if flt is not None:
        return flt
    for w, flt in filters_by_widget.items():
        try:
            if hasattr(w, 'viewport') and w.viewport() is widget:
                return flt
            if w.isAncestorOf(widget):
                return flt
        except Exception:
            pass
    return None


def attach_autocomplete(store, widget, field=None, add_button=True):
    """نصب تکمیل خودکار روی یک فیلد خاص + دکمه ✕."""
    flt = CompleterFilter(widget, store, field=field)
    if add_button:
        if isinstance(widget, QLineEdit):
            if not widget.property('_ac_action_added'):
                action = widget.addAction(_make_x_icon(), QLineEdit.TrailingPosition)
                action.setToolTip('مدیریت پیشنهادها')
                action.triggered.connect(lambda _=False, f=flt: f.open_manager())
                widget.setProperty('_ac_action_added', True)
        elif isinstance(widget, QTextEdit):
            _add_side_button_for_textedit(widget, flt)
    return flt


def install_window_shortcuts(window, filters_by_widget):
    """F2 / Ctrl+Space در سطح فرم برای فیلدهای ثبت‌شده."""
    if getattr(window, '_ac_shortcuts_installed', False):
        return

    def _show_for_focus():
        focus = QApplication.focusWidget()
        flt = _find_filter_for_widget(focus, filters_by_widget)
        if flt is not None:
            flt.show_suggestions()
            return
        if isinstance(focus, (QLineEdit, QTextEdit)):
            return
        try:
            QMessageBox.information(
                window, 'پیشنهادها',
                'ابتدا داخل یکی از فیلدهای متنی (مبدأ، مقصد، مسئول انبار،\n'
                'تحویل‌گیرنده یا توضیحات) کلیک کنید، سپس F2 را بزنید.'
            )
        except Exception:
            pass

    shortcut = QShortcut(QKeySequence(Qt.Key_F2), window)
    shortcut.setContext(Qt.WidgetWithChildrenShortcut)
    shortcut.activated.connect(_show_for_focus)
    window._ac_f2_shortcut = shortcut

    sc2 = QShortcut(QKeySequence(Qt.CTRL | Qt.Key_Space), window)
    sc2.setContext(Qt.WidgetWithChildrenShortcut)
    sc2.activated.connect(_show_for_focus)
    window._ac_ctrl_space = sc2

    window._ac_shortcuts_installed = True


def install_autocomplete(window):
    """نصب خودکار روی همه فیلدهای متنی (برای فرم‌های ساده / سازگاری قدیمی)."""
    if getattr(window, '_ac_installed', False):
        return getattr(window, '_ac_store', None)

    try:
        store = AutoCompleteStore()
        filters = []
        filters_by_widget = {}

        for w in window.findChildren(QTextEdit):
            if w.isReadOnly():
                continue
            flt = attach_autocomplete(store, w)
            filters.append(flt)
            filters_by_widget[w] = flt

        for w in window.findChildren(QLineEdit):
            if w.isReadOnly() or _is_password(w):
                continue
            if (w.objectName() or '') == 'qt_spinbox_lineedit':
                continue
            parent = w.parentWidget()
            if isinstance(parent, (QAbstractSpinBox, QComboBox)):
                continue
            flt = attach_autocomplete(store, w)
            filters.append(flt)
            filters_by_widget[w] = flt

        def save_all():
            for flt in filters:
                try:
                    flt.save_now()
                except Exception:
                    pass

        for btn in window.findChildren(QPushButton):
            txt = (btn.text() or '')
            if any(k in txt for k in ('ثبت', 'ذخیره', 'ایجاد', 'افزودن', 'اضافه')):
                try:
                    btn.clicked.connect(lambda _=False, s=save_all: s())
                except Exception:
                    pass

        install_window_shortcuts(window, filters_by_widget)

        window._ac_filters = filters
        window._ac_store = store
        window._ac_installed = True
        return store
    except Exception as e:
        print('[auto-complete] install error:', repr(e))
        return None