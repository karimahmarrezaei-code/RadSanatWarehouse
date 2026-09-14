# -*- coding: utf-8 -*-
"""
فرم مدیریت کاربران (نسخهٔ تمیز - فقط کاربران، دسترسی‌ها در فرم جداگانه)
"""
import hashlib
from typing import Any, Dict, List
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout,
    QLineEdit, QComboBox, QMessageBox, QWidget, QCheckBox, QFrame,
    QAbstractItemView,
)
from app.core.database import DatabaseManager


try:
    from app.core.security import hash_password   # همان هشِ ورود سیستم
except Exception:
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()


class UserManagerWindow(QDialog):
    users_changed = pyqtSignal()

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any]) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.roles: List[Dict] = []

        self.setWindowTitle('مدیریت کاربران')
        self.resize(900, 600)
        self.setLayoutDirection(Qt.RightToLeft)

        self._load_roles()
        self._build_ui()
        self._load_users()

    def _load_roles(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                try:
                    rows = conn.execute("SELECT id, code, name, description FROM roles WHERE is_active=1 OR is_active IS NULL ORDER BY id").fetchall()
                except Exception:
                    rows = conn.execute("SELECT id, code, name, description FROM roles ORDER BY id").fetchall()
                self.roles = [{'id': r[0], 'code': r[1], 'name': r[2], 'description': r[3] or ''} for r in rows]
        except Exception:
            self.roles = []

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QFrame(); header.setObjectName('Card'); hl = QVBoxLayout(header)
        title = QLabel('👥 مدیریت کاربران'); title.setObjectName('Title'); hl.addWidget(title)
        subtitle = QLabel('تعریف کاربران، تعیین نقش و فعال/غیرفعال کردن'); subtitle.setObjectName('Muted'); hl.addWidget(subtitle)
        note = QLabel('💡 برای تنظیم دسترسی‌های هر نقش، از منوی «مدیریت کاربران → سطوح دسترسی (چک‌باکس)» استفاده کنید.')

        hl.addWidget(note)
        root.addWidget(header)

        self.users_table = QTableWidget(0, 7)
        self.users_table.setHorizontalHeaderLabels(['شناسه', 'نام کاربری', 'نام کامل', 'موبایل', 'نقش', 'وضعیت', 'آخرین ورود'])
        self.users_table.setColumnHidden(0, True)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setAlternatingRowColors(True)
        root.addWidget(self.users_table)

        btn_layout = QHBoxLayout()
        new_btn = QPushButton('👤 کاربر جدید'); new_btn.setMinimumHeight(40); new_btn.clicked.connect(self._new_user)
        edit_btn = QPushButton('✏️ ویرایش'); edit_btn.setMinimumHeight(40); edit_btn.clicked.connect(self._edit_user)
        toggle_btn = QPushButton('⚡ تغییر وضعیت'); toggle_btn.setMinimumHeight(40); toggle_btn.clicked.connect(self._toggle_user)
        close_btn = QPushButton('بستن'); close_btn.setMinimumHeight(40); close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(new_btn); btn_layout.addWidget(edit_btn); btn_layout.addWidget(toggle_btn)
        btn_layout.addStretch(); btn_layout.addWidget(close_btn)
        root.addLayout(btn_layout)

    def _load_users(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("""
                    SELECT u.id, u.username, u.full_name, u.mobile, u.role_id, u.is_active, u.last_login_at,
                           r.name as role_name
                    FROM users u LEFT JOIN roles r ON r.id = u.role_id ORDER BY u.id
                """).fetchall()
            self.users_table.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                role_name = r[7] or '-'
                status = 'فعال' if r[5] else 'غیرفعال'
                vals = [str(r[0]), r[1], r[2] or '-', r[3] or '-', role_name, status, r[6] or '-']
                for col, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if col == 5:
                        item.setForeground(Qt.green if r[5] else Qt.red)
                    self.users_table.setItem(idx, col, item)
            self.users_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بارگذاری کاربران:\n{e}')

    def _get_selected_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'توجه', 'ابتدا یک کاربر انتخاب کنید.')
            return None
        return int(self.users_table.item(row, 0).text())

    def _new_user(self):
        dlg = UserEditDialog(self, self.roles, None)
        if dlg.exec_() == QDialog.Accepted:
            self._load_users(); self.users_changed.emit()

    def _edit_user(self):
        uid = self._get_selected_user()
        if not uid: return
        dlg = UserEditDialog(self, self.roles, uid)
        if dlg.exec_() == QDialog.Accepted:
            self._load_users(); self.users_changed.emit()

    def _toggle_user(self):
        uid = self._get_selected_user()
        if not uid: return
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute("SELECT username, is_active FROM users WHERE id=?", (uid,)).fetchone()
                if not row: return
                new_status = 0 if row[1] else 1
                status_text = 'غیرفعال' if row[1] else 'فعال'
                reply = QMessageBox.question(
                    self, 'تأیید',
                    f'آیا از {status_text} کردن کاربر «{row[0]}» اطمینان دارید؟',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes: return
                conn.execute("UPDATE users SET is_active=?, updated_at=datetime('now') WHERE id=?", (new_status, uid))
                conn.commit()
            self._load_users(); self.users_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا: {e}')


class UserEditDialog(QDialog):
    def __init__(self, parent, roles, user_id=None):
        super().__init__(parent)
        self.db = parent.db
        self.roles = roles
        self.user_id = user_id
        self.setWindowTitle('ویرایش کاربر' if user_id else 'کاربر جدید')
        self.resize(500, 400)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        if user_id:
            self._load_user()

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setSpacing(12)
        form = QGroupBox('اطلاعات کاربر'); fl = QFormLayout(form)
        self.username_edit = QLineEdit(); self.username_edit.setPlaceholderText('نام کاربری')
        self.password_edit = QLineEdit(); self.password_edit.setEchoMode(QLineEdit.Password); self.password_edit.setPlaceholderText('رمز عبور (برای تغییر وارد کنید)')
        self.fullname_edit = QLineEdit(); self.fullname_edit.setPlaceholderText('نام و نام خانوادگی')
        self.mobile_edit = QLineEdit(); self.mobile_edit.setPlaceholderText('شماره موبایل')
        self.email_edit = QLineEdit(); self.email_edit.setPlaceholderText('ایمیل')
        self.role_combo = QComboBox()
        for role in self.roles:
            self.role_combo.addItem(f"{role['code']} - {role['name']}", role['id'])
        self.active_check = QCheckBox('کاربر فعال است'); self.active_check.setChecked(True)
        fl.addRow('نام کاربری:', self.username_edit)
        fl.addRow('رمز عبور:', self.password_edit)
        fl.addRow('نام کامل:', self.fullname_edit)
        fl.addRow('موبایل:', self.mobile_edit)
        fl.addRow('ایمیل:', self.email_edit)
        fl.addRow('نقش:', self.role_combo)
        fl.addRow('وضعیت:', self.active_check)
        layout.addWidget(form)

        bl = QHBoxLayout()
        save_btn = QPushButton('💾 ذخیره'); save_btn.setMinimumHeight(40); save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton('انصراف'); cancel_btn.setMinimumHeight(40); cancel_btn.clicked.connect(self.reject)
        bl.addWidget(save_btn); bl.addWidget(cancel_btn)
        layout.addLayout(bl)

    def _load_user(self):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT username, full_name, mobile, email, role_id, is_active FROM users WHERE id=?",
                    (self.user_id,)
                ).fetchone()
                if row:
                    self.username_edit.setText(row[0] or ''); self.username_edit.setEnabled(False)
                    self.fullname_edit.setText(row[1] or ''); self.mobile_edit.setText(row[2] or '')
                    self.email_edit.setText(row[3] or ''); self.active_check.setChecked(bool(row[5]))
                    role_id = row[4]
                    for i in range(self.role_combo.count()):
                        if self.role_combo.itemData(i) == role_id:
                            self.role_combo.setCurrentIndex(i); break
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بارگذاری: {e}')

    def _save(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        full_name = self.fullname_edit.text().strip()
        mobile = self.mobile_edit.text().strip()
        email = self.email_edit.text().strip()
        role_id = self.role_combo.currentData()
        is_active = 1 if self.active_check.isChecked() else 0

        if not username:
            QMessageBox.warning(self, 'خطا', 'نام کاربری الزامی است.'); return
        if not self.user_id and not password:
            QMessageBox.warning(self, 'خطا', 'رمز عبور برای کاربر جدید الزامی است.'); return

        try:
            with self.db.connect() as conn:
                if self.user_id:
                    if password:
                        pwd_hash = hash_password(password)
                        conn.execute(
                            "UPDATE users SET full_name=?, mobile=?, email=?, role_id=?, is_active=?, password_hash=?, updated_at=datetime('now') WHERE id=?",
                            (full_name, mobile, email, role_id, is_active, pwd_hash, self.user_id))
                    else:
                        conn.execute(
                            "UPDATE users SET full_name=?, mobile=?, email=?, role_id=?, is_active=?, updated_at=datetime('now') WHERE id=?",
                            (full_name, mobile, email, role_id, is_active, self.user_id))
                else:
                    pwd_hash = hash_password(password)
                    conn.execute(
                        "INSERT INTO users (username, password_hash, full_name, mobile, email, role_id, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
                        (username, pwd_hash, full_name, mobile, email, role_id, is_active))
                conn.commit()
            QMessageBox.information(self, 'موفق', 'کاربر با موفقیت ذخیره شد.')
            self.accept()
        except Exception as e:
            if 'UNIQUE' in str(e):
                QMessageBox.warning(self, 'خطا', 'این نام کاربری قبلاً ثبت شده است.')
            else:
                QMessageBox.critical(self, 'خطا', f'خطا: {e}')