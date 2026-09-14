# -*- coding: utf-8 -*-
# BackupManagerDialog - پشتیبان‌گیری و بازیابی کامل فایل دیتابیس
import os
import shutil
import sqlite3
from datetime import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QFrame,
)


class BackupManagerDialog(QDialog):
    def __init__(self, db, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('💾 پشتیبان‌گیری و بازیابی')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(900, 620)
        self._build_ui()
        self._refresh()

    def _db_path(self):
        for attr in ('db_path', 'path', 'database_path', 'db_file'):
            v = getattr(self.db, attr, None)
            if v:
                return str(v)
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cand = os.path.join(base, 'data')
        dbs = []
        if os.path.isdir(cand):
            for fn in os.listdir(cand):
                if fn.lower().endswith(('.db', '.sqlite', '.sqlite3')):
                    dbs.append(os.path.join(cand, fn))
        if dbs:
            return sorted(dbs, key=os.path.getmtime)[-1]
        return None

    def _backups_dir(self):
        src = self._db_path()
        d = os.path.join(os.path.dirname(src), 'backups') if src else os.path.join(os.getcwd(), 'backups')
        os.makedirs(d, exist_ok=True)
        return d

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        info = QFrame(); info.setObjectName('Card')
        il = QVBoxLayout(info)
        t = QLabel('پشتیبان‌گیری کامل از کل فایل دیتابیس')
        t.setObjectName('Title'); t.setAlignment(Qt.AlignCenter)
        il.addWidget(t)
        s = QLabel('هر نسخه شامل همهٔ جدول‌ها و ستون‌های جدید است (جابجایی، انبارگردانی، جعبه، افتتاحیه و ...)')
        s.setObjectName('Muted'); s.setAlignment(Qt.AlignCenter)
        il.addWidget(s)
        self.db_info_lbl = QLabel('-')
        self.db_info_lbl.setObjectName('Muted'); self.db_info_lbl.setAlignment(Qt.AlignCenter)
        il.addWidget(self.db_info_lbl)
        root.addWidget(info)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(['نام نسخه', 'تاریخ', 'حجم (MB)', 'تعداد جدول'])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(self.tbl)

        btn_row = QHBoxLayout()
        b = QPushButton('🆕 پشتیبان‌گیری کامل همین حالا')
        b.setObjectName('PrimaryButton'); b.setMinimumHeight(48)
        b.clicked.connect(self._do_backup)
        btn_row.addWidget(b)
        b = QPushButton('🔄 بازیابی نسخه انتخاب‌شده')
        b.setObjectName('SecondaryButton'); b.setMinimumHeight(48)
        b.clicked.connect(self._do_restore)
        btn_row.addWidget(b)
        b = QPushButton('✅ بررسی سلامت')
        b.setObjectName('SecondaryButton'); b.setMinimumHeight(48)
        b.clicked.connect(self._do_verify)
        btn_row.addWidget(b)
        b = QPushButton('🗑 حذف نسخه')
        b.setObjectName('SecondaryButton'); b.setMinimumHeight(48)
        b.clicked.connect(self._do_delete)
        btn_row.addWidget(b)
        b = QPushButton('بستن')
        b.setObjectName('SecondaryButton'); b.setMinimumHeight(48)
        b.clicked.connect(self.accept)
        btn_row.addWidget(b)
        root.addLayout(btn_row)

    def _table_count(self, path):
        try:
            c = sqlite3.connect(path)
            n = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            c.close()
            return n
        except Exception:
            return -1

    def _refresh(self):
        src = self._db_path()
        if src and os.path.exists(src):
            self.db_info_lbl.setText('دیتابیس فعال: {} | حجم: {:.1f} MB | جدول‌ها: {}'.format(
                os.path.basename(src), os.path.getsize(src) / 1048576.0, self._table_count(src)))
        d = self._backups_dir()
        rows = []
        for fn in sorted(os.listdir(d), reverse=True):
            p = os.path.join(d, fn)
            if fn.lower().endswith('.db') and os.path.isfile(p):
                rows.append((fn, p))
        self.tbl.setRowCount(len(rows))
        for i, (fn, p) in enumerate(rows):
            mt = datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')
            vals = [fn, mt, '{:.1f}'.format(os.path.getsize(p) / 1048576.0), str(self._table_count(p))]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, col, it)
        self.tbl.resizeColumnsToContents()

    def _selected_path(self):
        r = self.tbl.currentRow()
        if r < 0:
            return None
        return os.path.join(self._backups_dir(), self.tbl.item(r, 0).text())

    def _do_backup(self):
        src = self._db_path()
        if not src or not os.path.exists(src):
            QMessageBox.critical(self, 'خطا', 'فایل دیتابیس پیدا نشد.')
            return
        try:
            c = sqlite3.connect(src)
            c.execute('PRAGMA wal_checkpoint(TRUNCATE);')
            c.close()
        except Exception:
            pass
        dst = os.path.join(self._backups_dir(), 'backup_{}.db'.format(datetime.now().strftime('%Y%m%d-%H%M%S')))
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'پشتیبان‌گیری ناموفق:\n{}'.format(e))
            return
        QMessageBox.information(self, 'موفق', 'پشتیبان کامل ساخته شد:\n{}'.format(dst))
        self._refresh()

    def _do_verify(self):
        p = self._selected_path()
        if not p:
            QMessageBox.warning(self, 'توجه', 'ابتدا یک نسخه را انتخاب کنید.')
            return
        try:
            c = sqlite3.connect(p)
            res = c.execute('PRAGMA integrity_check;').fetchone()[0]
            n = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            c.close()
            if res == 'ok':
                QMessageBox.information(self, 'سلامت نسخه', 'نسخه سالم است ✔\nتعداد جدول‌ها: {}'.format(n))
            else:
                QMessageBox.warning(self, 'سلامت نسخه', 'نسخه مشکل دارد:\n{}'.format(res))
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'بررسی سلامت ناموفق:\n{}'.format(e))

    def _do_delete(self):
        p = self._selected_path()
        if not p:
            QMessageBox.warning(self, 'توجه', 'ابتدا یک نسخه را انتخاب کنید.')
            return
        if QMessageBox.question(self, 'حذف نسخه', 'نسخه حذف شود؟\n{}'.format(os.path.basename(p)),
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            os.remove(p)
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))

    def _do_restore(self):
        p = self._selected_path()
        src = self._db_path()
        if not p or not src:
            QMessageBox.warning(self, 'توجه', 'ابتدا یک نسخه را انتخاب کنید.')
            return
        try:
            c = sqlite3.connect(p)
            res = c.execute('PRAGMA integrity_check;').fetchone()[0]
            c.close()
            if res != 'ok':
                QMessageBox.critical(self, 'خطا', 'نسخهٔ انتخابی سالم نیست؛ بازیابی انجام نشد.')
                return
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'نسخه قابل خواندن نیست:\n{}'.format(e))
            return
        if QMessageBox.warning(self, 'هشدار بازیابی',
                               'با بازیابی، همهٔ داده‌های فعلی با نسخهٔ انتخابی جایگزین می‌شوند.\n\n'
                               'نسخه: {}\n\nادامه می‌دهید؟'.format(os.path.basename(p)),
                               QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        pre = None
        try:
            c = sqlite3.connect(src)
            c.execute('PRAGMA wal_checkpoint(TRUNCATE);')
            c.close()
            pre = src + '.pre_restore_' + datetime.now().strftime('%Y%m%d-%H%M%S')
            shutil.copy2(src, pre)
        except Exception:
            pre = None
        try:
            shutil.copy2(p, src)
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'بازیابی ناموفق:\n{}'.format(e))
            return
        msg = 'بازیابی با موفقیت انجام شد.\nلطفاً برنامه را ببندید و دوباره اجرا کنید.'
        if pre:
            msg += '\n\n(نسخهٔ احتیاطی قبل از بازیابی: {})'.format(os.path.basename(pre))
        QMessageBox.information(self, 'موفق', msg)
        self._refresh()
