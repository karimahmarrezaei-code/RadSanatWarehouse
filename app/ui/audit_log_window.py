# -*- coding: utf-8 -*-
"""AuditLogWindow - گزارش فعالیت کاربران | فیلتر: فقط کاربر + تاریخ"""
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QDateEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel,
)
from app.core.database import DatabaseManager


class AuditLogWindow(QDialog):
    def __init__(self, db: DatabaseManager, user_data=None) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data or {}
        self.setWindowTitle('📜 گزارش فعالیت کاربران (حسابرسی)')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1050, 620)
        self._build_ui()
        self._load_users()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel('کاربر:'))
        self.user_combo = QComboBox(); self.user_combo.setMinimumWidth(180)
        bar.addWidget(self.user_combo)
        bar.addWidget(QLabel('از تاریخ:'))
        self.from_edit = QDateEdit(QDate.currentDate().addDays(-7))
        self.from_edit.setCalendarPopup(True); self.from_edit.setDisplayFormat('yyyy-MM-dd')
        bar.addWidget(self.from_edit)
        bar.addWidget(QLabel('تا تاریخ:'))
        self.to_edit = QDateEdit(QDate.currentDate())
        self.to_edit.setCalendarPopup(True); self.to_edit.setDisplayFormat('yyyy-MM-dd')
        bar.addWidget(self.to_edit)
        refresh = QPushButton('🔄 نمایش'); refresh.clicked.connect(self.refresh)
        bar.addWidget(refresh); bar.addStretch()
        root.addLayout(bar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['زمان', 'کاربر', 'عمل', 'بخش', 'شناسه', 'جزئیات'])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

    def _load_users(self):
        with self.db.connect() as conn:
            rows = conn.execute("SELECT id, full_name FROM users ORDER BY full_name").fetchall()
        self.user_combo.clear()
        self.user_combo.addItem('همه کاربران', None)
        for r in rows:
            self.user_combo.addItem(r['full_name'], r['id'])

    def refresh(self):
        uid = self.user_combo.currentData()
        d_from = self.from_edit.date().toString('yyyy-MM-dd')
        d_to = self.to_edit.date().toString('yyyy-MM-dd')
        filters = ["substr(al.created_at,1,10) BETWEEN ? AND ?"]
        params = [d_from, d_to]
        if uid:
            filters.append("al.user_id = ?"); params.append(uid)
        with self.db.connect() as conn:
            rows = conn.execute(f"""
                SELECT al.created_at, COALESCE(u.full_name,'سیستم'), al.action_name, al.entity_name,
                       COALESCE(al.entity_id,'-'), COALESCE(al.new_values_json,'')
                FROM audit_logs al LEFT JOIN users u ON u.id = al.user_id
                WHERE {' AND '.join(filters)}
                ORDER BY al.id DESC""", params).fetchall()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for col, v in enumerate([r[0], r[1], r[2], r[3], str(r[4]), (r[5] or '')[:120]]):
                cell = QTableWidgetItem(str(v)); cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, cell)
        self.table.resizeColumnsToContents()