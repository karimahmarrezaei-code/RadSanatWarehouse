# -*- coding: utf-8 -*-
"""PermissionManagerWindow - مدیریت سطوح دسترسی با چک‌باکس (به تفکیک ماژول)"""
from typing import Dict
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton,
    QGroupBox, QCheckBox, QScrollArea, QWidget, QMessageBox,
)
from app.core.database import DatabaseManager
from app.core.jalali import now_iso


class PermissionManagerWindow(QDialog):
    def __init__(self, db: DatabaseManager, user_data=None) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('🔐 مدیریت سطوح دسترسی (چک‌باکس)')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(950, 620)
        self._checks: Dict[int, QCheckBox] = {}
        self._current_role_id = None
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel('نقش‌ها:'))
        self.role_list = QListWidget()
        self.role_list.currentRowChanged.connect(self._on_role_changed)
        left.addWidget(self.role_list)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel('دسترسی‌ها (تیک بزنید / بردارید):'))
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.perm_container = QWidget()
        self.perm_layout = QVBoxLayout(self.perm_container)
        self.scroll.setWidget(self.perm_container)
        right.addWidget(self.scroll, 1)

        btn_row = QHBoxLayout()
        save_btn = QPushButton('💾 ذخیره دسترسی‌ها')
        save_btn.clicked.connect(self._save)
        btn_row.addStretch(); btn_row.addWidget(save_btn)
        right.addLayout(btn_row)
        root.addLayout(right, 3)

    def _load(self):
        with self.db.connect() as conn:
            self.roles = [dict(r) for r in conn.execute("SELECT id, code, name FROM roles ORDER BY name").fetchall()]
            self.perms = [dict(r) for r in conn.execute(
                "SELECT id, code, name, module_name FROM permissions ORDER BY module_name, name").fetchall()]
        self.role_list.clear()
        for r in self.roles:
            self.role_list.addItem(f"{r['name']} ({r['code']})")
        self._build_checks()

    def _build_checks(self):
        while self.perm_layout.count():
            it = self.perm_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self._checks = {}
        modules = {}
        for p in self.perms:
            modules.setdefault(p['module_name'] or 'عمومی', []).append(p)
        for mod, plist in modules.items():
            gb = QGroupBox(mod)
            vl = QVBoxLayout(gb)
            for p in plist:
                cb = QCheckBox(f"{p['name']}  ({p['code']})")
                self._checks[p['id']] = cb
                vl.addWidget(cb)
            self.perm_layout.addWidget(gb)
        self.perm_layout.addStretch()

    def _on_role_changed(self, row):
        if row < 0 or row >= len(self.roles): return
        self._current_role_id = self.roles[row]['id']
        with self.db.connect() as conn:
            granted = {r['permission_id'] for r in conn.execute(
                "SELECT permission_id FROM role_permissions WHERE role_id = ?",
                (self._current_role_id,)).fetchall()}
        for pid, cb in self._checks.items():
            cb.setChecked(pid in granted)

    def _save(self):
        if not self._current_role_id:
            QMessageBox.warning(self, 'ذخیره', 'ابتدا یک نقش انتخاب کنید.')
            return
        checked = [pid for pid, cb in self._checks.items() if cb.isChecked()]
        with self.db.connect() as conn:
            conn.execute("DELETE FROM role_permissions WHERE role_id = ?", (self._current_role_id,))
            for pid in checked:
                conn.execute("INSERT INTO role_permissions (role_id, permission_id, granted_at) VALUES (?,?,?)",
                             (self._current_role_id, pid, now_iso()))
            conn.commit()
        QMessageBox.information(self, 'ذخیره', 'دسترسی‌های نقش با موفقیت ذخیره شد.')