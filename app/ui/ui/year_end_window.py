# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox)
from app.core.jalali import today_iso_date, jalali_date_display_from_iso

class YearEndWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.setWindowTitle('بستن سال مالی / شروع سال جدید')
        self.resize(800, 500); self.setLayoutDirection(Qt.RightToLeft)
        self._ensure(); self._build(); self.refresh()

    def _ensure(self):
        with self.db.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS fiscal_years(id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, status TEXT DEFAULT 'OPEN', opened_at TEXT, closed_at TEXT, opening_inventory_value INTEGER DEFAULT 0, opening_treasury_value INTEGER DEFAULT 0)")
            if not conn.execute("SELECT id FROM fiscal_years LIMIT 1").fetchone():
                conn.execute("INSERT INTO fiscal_years(year, status, opened_at) VALUES(1405,'OPEN',?)", (today_iso_date(),))
            conn.commit()

    def _build(self):
        root = QVBoxLayout(self)
        note = QLabel('با بستن سال مالی، ماندهٔ فعلی انبار و خزانه به‌عنوان «مانده اول دوره» سال جدید ثبت می‌شود و سال قبل بسته می‌گردد.')
        note.setStyleSheet('color:#f59e0b;font-weight:bold;padding:8px;')
        note.setWordWrap(True)
        root.addWidget(note)
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(['سال', 'وضعیت', 'تاریخ باز شدن', 'تاریخ بستن', 'مانده اول دوره (انبار+خزانه)'])
        self.tbl.verticalHeader().setVisible(False)
        root.addWidget(self.tbl)
        bar = QHBoxLayout()
        btn = QPushButton('🔒 بستن سال جاری و شروع سال جدید')
        btn.setObjectName('PrimaryButton'); btn.setMinimumHeight(45)
        btn.clicked.connect(self._close_open)
        bar.addStretch(); bar.addWidget(btn)
        root.addLayout(bar)

    def _values(self):
        with self.db.connect() as conn:
            cost = {r['pid']: (r['avg'] or 0) for r in conn.execute("""
                SELECT pid, SUM(val)/SUM(q) AS avg FROM (
                    SELECT oii.pallet_id AS pid, oii.qty*oii.unit_price AS val, oii.qty AS q FROM opening_inventory_items oii
                    UNION ALL SELECT ri.pallet_id, ri.qty*ri.unit_price, ri.qty FROM warehouse_receipt_items ri WHERE ri.unit_price>0 AND ri.qty>0
                ) GROUP BY pid""").fetchall()}
            inv = sum((r['quantity'] or 0) * cost.get(r['pallet_id'], 0)
                      for r in conn.execute("SELECT pallet_id, quantity FROM inventory_levels WHERE quantity>0"))
            tr = conn.execute("SELECT COALESCE(SUM(current_balance),0) FROM treasury_accounts WHERE is_active=1").fetchone()[0]
        return int(inv), int(tr)

    def refresh(self):
        with self.db.connect() as conn:
            rows = conn.execute("SELECT year, status, opened_at, closed_at, opening_inventory_value, opening_treasury_value FROM fiscal_years ORDER BY year").fetchall()
        self.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [str(r['year']), 'باز' if r['status'] == 'OPEN' else 'بسته',
                    jalali_date_display_from_iso(r['opened_at']) if r['opened_at'] else '-',
                    jalali_date_display_from_iso(r['closed_at']) if r['closed_at'] else '-',
                    f"{int(r['opening_inventory_value'] or 0) + int(r['opening_treasury_value'] or 0):,}"]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, c, it)
        self.tbl.resizeColumnsToContents()

    def _close_open(self):
        with self.db.connect() as conn:
            cur = conn.execute("SELECT year FROM fiscal_years WHERE status='OPEN' ORDER BY year DESC LIMIT 1").fetchone()
        if not cur:
            QMessageBox.warning(self, 'سال مالی', 'سال بازی یافت نشد.'); return
        cur_year = int(cur['year']); new_year = cur_year + 1
        ans = QMessageBox.question(self, 'بستن سال مالی',
            f'آیا از بستن سال {cur_year} و شروع سال {new_year} مطمئن هستید؟\nمانده فعلی انبار و خزانه به‌عنوان مانده اول دوره ثبت می‌شود.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        inv, tr = self._values()
        with self.db.connect() as conn:
            conn.execute("UPDATE fiscal_years SET status='CLOSED', closed_at=? WHERE year=?", (today_iso_date(), cur_year))
            conn.execute("INSERT INTO fiscal_years(year, status, opened_at, opening_inventory_value, opening_treasury_value) VALUES(?,?,?,?,?)",
                         (new_year, 'OPEN', today_iso_date(), inv, tr))
            conn.commit()
        QMessageBox.information(self, 'سال مالی', f'سال {cur_year} بسته و سال {new_year} با مانده اول دوره ثبت شد.')
        self.refresh()
