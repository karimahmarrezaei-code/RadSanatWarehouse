"""
گزارش سن بدهی‌ها و مطالبات (Aging Report)
نمایش مانده باز هر شخص به تفکیک بازه زمانی:
- جاری (0-30 روز)
- 31-60 روز
- 61-90 روز
- 91-180 روز
- بیش از 180 روز (بحرانی)
"""

import webbrowser
import tempfile
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QDateEdit, QPushButton,
    QComboBox, QHeaderView, QMessageBox, QFrame, QTextBrowser,
    QTabWidget, QWidget, QAbstractItemView, QFileDialog
)
from app.core.jalali import jalali_date_display_from_iso


# ===================================================================
# کارت Aging
# ===================================================================
class AgingCard(QFrame):
    def __init__(self, title: str, value: str = "0 ریال",
                 color: str = "#2563eb", warning: bool = False) -> None:
        super().__init__()
        self.setObjectName('Card')
        border_style = "dashed" if warning else "solid"
        self.setStyleSheet(
            f"QFrame#Card {{ border: 3px {border_style} {color}; "
            f"border-radius: 8px; padding: 12px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; color: #555;")
        title_lbl.setAlignment(Qt.AlignCenter)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {color};"
        )
        self.value_lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_lbl)
        layout.addWidget(self.value_lbl)


# ===================================================================
# فرم اصلی گزارش Aging
# ===================================================================
class AgingReportWindow(QDialog):
    # بازه‌های استاندارد Aging (به روز)
    AGING_BUCKETS = [
        (0, 30, 'جاری (0-30)'),
        (31, 60, '31-60 روز'),
        (61, 90, '61-90 روز'),
        (91, 180, '91-180 روز'),
        (181, 99999, 'بیش از 180 روز ️'),
    ]

    def __init__(self, db, user_data) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.setWindowTitle('گزارش سن بدهی‌ها و مطالبات')
        self.resize(1500, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._run_report()

    def _money(self, value: int) -> str:
        if value < 0:
            return f"({abs(value):,}) ریال"
        return f"{value:,} ریال"

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # ============================================================
        # فیلتر
        # ============================================================
        filter_group = QGroupBox("فیلتر گزارش سِن بدهی‌ها")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("نوع گزارش:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItem("مطالبات (پول طلب ما از مشتری)", "RECEIVABLE")
        self.report_type_combo.addItem("بدهی‌ها (پول بدهی ما به تأمین‌کننده)", "PAYABLE")
        self.report_type_combo.addItem("هر دو (جامع)", "BOTH")
        filter_layout.addWidget(self.report_type_combo)

        filter_layout.addWidget(QLabel("باز تاریخ سررسید:"))
        self.cut_date_edit = QDateEdit(QDate.currentDate())
        self.cut_date_edit.setCalendarPopup(True)
        self.cut_date_edit.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.cut_date_edit)

        apply_btn = QPushButton("محاسبه سن بدهی")
        apply_btn.setObjectName('PrimaryButton')
        apply_btn.clicked.connect(self._run_report)
        filter_layout.addWidget(apply_btn)

        filter_layout.addStretch()
        root.addWidget(filter_group)

        # ============================================================
        # کارت‌های خلاصه
        # ============================================================
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        self.card_total = AgingCard("جمع کل مانده باز", "0 ریال", "#2563eb")
        self.card_current = AgingCard("جاری (0-30)", "0 ریال", "#16a34a")
        self.card_31_60 = AgingCard("31-60 روز", "0 ریال", "#0891b2")
        self.card_61_90 = AgingCard("61-90 روز", "0 ریال", "#ea580c")
        self.card_91_180 = AgingCard("91-180 روز", "0 ریال", "#dc2626", warning=True)
        self.card_over_180 = AgingCard("بیش از 180 روز ⚠️", "0 ریال", "#7c2d12", warning=True)
        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_current)
        cards_layout.addWidget(self.card_31_60)
        cards_layout.addWidget(self.card_61_90)
        cards_layout.addWidget(self.card_91_180)
        cards_layout.addWidget(self.card_over_180)
        root.addLayout(cards_layout)

        # ============================================================
        # تب‌ها
        # ============================================================
        self.tabs = QTabWidget()

        # --- تب ۱: جدول اشخاص ---
        persons_tab = QWidget()
        persons_layout = QVBoxLayout(persons_tab)

        self.persons_table = QTableWidget()
        self.persons_table.setColumnCount(8)
        self.persons_table.setHorizontalHeaderLabels([
            "شناسه", "نام شخص", "نقش", "جاری (0-30)",
            "31-60 روز", "61-90 روز", "91-180 روز", "بیش از 180 روز"
        ])
        self.persons_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.persons_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.persons_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.persons_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.persons_table.verticalHeader().setVisible(False)
        self.persons_table.itemSelectionChanged.connect(self._on_person_selected)
        persons_layout.addWidget(self.persons_table)

        self.persons_info_lbl = QLabel("لیست اشخاص با مانده باز به تفکیک سن")
        self.persons_info_lbl.setStyleSheet("color: #555; font-size: 12px; padding: 5px;")
        persons_layout.addWidget(self.persons_info_lbl)

        self.tabs.addTab(persons_tab, "👥 جدول اشخاص")

        # --- تب ۲: ریز اسناد شخص انتخاب‌شده ---
        docs_tab = QWidget()
        docs_layout = QVBoxLayout(docs_tab)

        self.docs_table = QTableWidget()
        self.docs_table.setColumnCount(9)
        self.docs_table.setHorizontalHeaderLabels(
            ['ردیف', 'شماره سند', 'تاریخ سند', 'تاریخ سررسید', 'مبلغ کل', 'تسویه‌شده', 'مانده باز', 'روز', 'نوع سند'])
        self.docs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.docs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.docs_table.verticalHeader().setVisible(False)
        docs_layout.addWidget(self.docs_table)

        self.docs_info_lbl = QLabel("یک شخص را از تب قبلی انتخاب کنید تا ریز اسناد باز او نمایش داده شود.")
        self.docs_info_lbl.setStyleSheet(
            'color:#e2e8f0; font-size:14px; font-weight:bold; padding:6px;'
            'background:#1e293b; border:1px solid #334155; border-radius:6px;')
        docs_layout.insertWidget(0, self.docs_info_lbl)

        self.tabs.addTab(docs_tab, "📄 ریز اسناد شخص")

        # --- تب ۳: نمودار ---
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)

        self.chart_view = QTextBrowser()
        self.chart_view.setOpenExternalLinks(False)
        self.chart_view.setMinimumHeight(300)
        chart_layout.addWidget(self.chart_view)

        self.tabs.addTab(chart_tab, "📊 نمودار")

        # --- تب ۴: هشدارها ---
        alerts_tab = QWidget()
        alerts_layout = QVBoxLayout(alerts_tab)

        self.alerts_text = QTextBrowser()
        self.alerts_text.setOpenExternalLinks(False)
        self.alerts_text.setMinimumHeight(300)
        alerts_layout.addWidget(self.alerts_text)

        self.tabs.addTab(alerts_tab, "️ هشدارهای مهم")

        root.addWidget(self.tabs, stretch=1)

        # ============================================================
        # دکمه‌های پایین
        # ============================================================
        bottom_row = QHBoxLayout()
        self.status_lbl = QLabel("آماده")
        self.status_lbl.setStyleSheet("color: #555;")
        bottom_row.addWidget(self.status_lbl)
        bottom_row.addStretch()

        print_btn = QPushButton("️ چاپ گزارش")
        print_btn.setObjectName('SecondaryButton')
        print_btn.clicked.connect(self._print_report)
        bottom_row.addWidget(print_btn)

        export_btn = QPushButton("💾 خروجی HTML")
        export_btn.setObjectName('SecondaryButton')
        export_btn.clicked.connect(self._export_html)
        bottom_row.addWidget(export_btn)

        close_btn = QPushButton("بستن")
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        root.addLayout(bottom_row)

    def _get_bucket(self, days: int) -> int:
        """برمی‌گرداند این سند در کدام بازه قرار می‌گیرد (index)"""
        for idx, (min_d, max_d, _) in enumerate(self.AGING_BUCKETS):
            if min_d <= days <= max_d:
                return idx
        return len(self.AGING_BUCKETS) - 1

    def _run_report(self):
        """محاسبه و نمایش Aging"""
        cut_date = self.cut_date_edit.date()
        cut_date_iso = cut_date.toString('yyyy-MM-dd')
        report_type = self.report_type_combo.currentData()  # RECEIVABLE, PAYABLE, BOTH

        try:
            cut_dt = datetime.strptime(cut_date_iso, '%Y-%m-%d')
        except Exception:
            QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است.")
            return

        with self.db.connect() as conn:
            # کوئری اصلی: اسناد باز (OPEN یا PARTIAL) با direction مشخص
            direction_clause = ""
            if report_type != 'BOTH':
                direction_clause = " AND fd.direction = ?"

            query = f'''
                SELECT 
                    fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                    COALESCE(fd.settled_amount, 0) as settled_amount,
                    COALESCE((SELECT SUM(pe.amount) FROM payment_entries pe
                              WHERE pe.financial_document_id = fd.id
                                AND pe.status = 'PENDING'), 0) as pending_amount,
                    (SELECT MAX(pe.due_date) FROM payment_entries pe
                     WHERE pe.financial_document_id = fd.id
                       AND pe.status = 'PENDING') as due_date,
                    fd.direction, fd.operation_type,
                    p.id as person_id,
                    p.first_name, p.last_name
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.status IN ('OPEN', 'PARTIAL')
                  AND fd.status != 'CANCELLED'
                  AND fd.total_amount > COALESCE(fd.settled_amount, 0)
                  {direction_clause}
                ORDER BY fd.finance_date ASC
            '''
            params = []
            if report_type != 'BOTH':
                params.append(report_type)

            rows = conn.execute(query, params).fetchall()

        # گروه‌بندی بر اساس شخص
        persons_data: Dict[int, Dict] = {}
        bucket_totals = [0] * len(self.AGING_BUCKETS)
        grand_total = 0
        alerts = []

        for r in rows:
            person_id = r['person_id']
            if not person_id:
                continue

            finance_date_iso = r['finance_date']
            if not finance_date_iso:
                continue

            try:
                finance_dt = datetime.strptime(finance_date_iso, '%Y-%m-%d')
            except Exception:
                continue

            due_date_iso = r['due_date'] or finance_date_iso
            try:
                due_dt = datetime.strptime(due_date_iso, '%Y-%m-%d')
            except Exception:
                due_dt = finance_dt
            days_old = (cut_dt - due_dt).days
            if days_old < 0:
                days_old = 0

            pending = int(r['pending_amount'] or 0)
            remaining = int(r['total_amount'] or 0) - int(r['settled_amount'] or 0) - pending
            if remaining <= 0:
                continue

            bucket_idx = self._get_bucket(days_old)
            grand_total += remaining
            bucket_totals[bucket_idx] += remaining

            full_name = f"{r['first_name'] or ''} {r['last_name'] or ''}".strip()
            if not full_name:
                full_name = 'نامشخص'

            persons_data[person_id] = {
                'name': full_name,
                'role': '-',  # ستون role در جدول persons وجود ندارد
                'buckets': [0] * len(self.AGING_BUCKETS),
                'total': 0,
                'docs': [],
            }

            persons_data[person_id]['buckets'][bucket_idx] += remaining
            persons_data[person_id]['total'] += remaining
            persons_data[person_id]['docs'].append({
                'id': r['id'],
                'finance_no': r['finance_no'],
                'finance_date': finance_date_iso,
                'total_amount': int(r['total_amount'] or 0),
                'settled_amount': int(r['settled_amount'] or 0),
                'remaining': remaining,
                'days_old': days_old,
                'operation_type': r['operation_type'],
            })

            # هشدار برای بدهی‌های خیلی قدیمی
            if days_old > 180:
                alerts.append({
                    'person': full_name,
                    'doc': r['finance_no'],
                    'amount': remaining,
                    'days': days_old,
                })

        # ===== به‌روزرسانی کارت‌ها =====
        self.card_total.value_lbl.setText(f"{grand_total:,} ریال")
        for idx, (min_d, max_d, label) in enumerate(self.AGING_BUCKETS):
            card = [self.card_current, self.card_31_60, self.card_61_90,
                    self.card_91_180, self.card_over_180][idx]
            card.value_lbl.setText(f"{bucket_totals[idx]:,} ریال")

        # ===== جدول اشخاص =====
        sorted_persons = sorted(
            persons_data.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )

        self.persons_table.setRowCount(len(sorted_persons))
        for i, (person_id, data) in enumerate(sorted_persons):
            self.persons_table.setItem(i, 0, QTableWidgetItem(str(person_id)))
            self.persons_table.setItem(i, 1, QTableWidgetItem(data['name']))
            self.persons_table.setItem(i, 2, QTableWidgetItem(data['role']))
            for j in range(len(self.AGING_BUCKETS)):
                item = QTableWidgetItem(f"{data['buckets'][j]:,}")
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.persons_table.setItem(i, 3 + j, item)

        self.persons_info_lbl.setText(
            f"تعداد اشخاص با مانده باز: {len(sorted_persons)} | "
            f"جمع کل: {grand_total:,} ریال"
        )

        # ===== نمودار =====
        self._build_chart(bucket_totals, persons_data)

        # ===== هشدارها =====
        self._build_alerts(alerts, bucket_totals, grand_total)

        # پاک کردن جدول اسناد
        self.docs_table.setRowCount(0)
        self.docs_info_lbl.setText("یک شخص را انتخاب کنید.")

        self.status_lbl.setText(
            f"جمع مانده باز: {grand_total:,} ریال | "
            f"بحرانی (>180 روز): {bucket_totals[-1]:,} ریال"
        )

    def _on_person_selected(self):
        """نمایش ریز اسناد شخص انتخاب‌شده"""
        selected = self.persons_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        person_id_str = self.persons_table.item(row, 0).text()
        person_name = self.persons_table.item(row, 1).text()

        try:
            person_id = int(person_id_str)
        except ValueError:
            return

        # پیدا کردن داده این شخص
        with self.db.connect() as conn:
            query = '''
                SELECT 
                    fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                    COALESCE(fd.settled_amount, 0) as settled_amount,
                    COALESCE((SELECT SUM(pe.amount) FROM payment_entries pe
                              WHERE pe.financial_document_id = fd.id
                                AND pe.status = 'PENDING'), 0) as pending_amount,
                    (SELECT MAX(pe.due_date) FROM payment_entries pe
                     WHERE pe.financial_document_id = fd.id
                       AND pe.status = 'PENDING') as due_date,
                    fd.direction, fd.operation_type
                FROM financial_documents fd
                WHERE fd.counterparty_person_id = ?
                  AND fd.status IN ('OPEN', 'PARTIAL')
                  AND fd.status != 'CANCELLED'
                  AND fd.total_amount > COALESCE(fd.settled_amount, 0)
                ORDER BY fd.finance_date ASC
            '''
            rows = conn.execute(query, (person_id,)).fetchall()

        # ✅ محاسبه تاریخ سررسید از خود فرم
        cut_date_iso = self.cut_date_edit.date().toString('yyyy-MM-dd')
        try:
            cut_dt = datetime.strptime(cut_date_iso, '%Y-%m-%d')
        except Exception:
            cut_dt = datetime.now()

        self.docs_table.setRowCount(0)  # ✅ پاک کردن قبلی
        person_total = 0  # AGING-SAFE
        doc_index = 0

        for r in rows:
            pending = int(r['pending_amount'] or 0)
            remaining = int(r['total_amount'] or 0) - int(r['settled_amount'] or 0) - pending
            if remaining <= 0:
                continue

            try:
                due_date_iso = r['due_date'] or r['finance_date']
                days_old = (cut_dt - datetime.strptime(due_date_iso, '%Y-%m-%d')).days
            except Exception:
                days_old = 0

            self.docs_table.insertRow(doc_index)
            self.docs_table.setItem(doc_index, 0, QTableWidgetItem(str(doc_index + 1)))
            self.docs_table.setItem(doc_index, 1, QTableWidgetItem(str(r['finance_no'])))
            self.docs_table.setItem(doc_index, 2, QTableWidgetItem(
                jalali_date_display_from_iso(r['finance_date']) if r['finance_date'] else '-'
            ))
            self.docs_table.setItem(doc_index, 3, QTableWidgetItem(
                jalali_date_display_from_iso(r['due_date']) if r['due_date'] else '-'
            ))
            self.docs_table.setItem(doc_index, 4, QTableWidgetItem(f"{int(r['total_amount'] or 0):,}"))
            self.docs_table.setItem(doc_index, 5, QTableWidgetItem(f"{int(r['settled_amount'] or 0):,}"))

            rem_item = QTableWidgetItem(f"{remaining:,}")
            rem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.docs_table.setItem(doc_index, 6, rem_item)

            days_item = QTableWidgetItem(str(days_old))
            days_item.setTextAlignment(Qt.AlignCenter)
            if days_old > 180:
                days_item.setBackground(Qt.red)
            elif days_old > 90:
                days_item.setBackground(Qt.yellow)
            self.docs_table.setItem(doc_index, 7, days_item)

            person_total += remaining
            _raw = str(r['operation_type'] or r['direction'] or '-')
            _TYPE_FA = {'OUTBOUND_ISSUE': 'خروج / حواله', 'INBOUND_RECEIPT': 'ورود / رسید',
                        'SALE': 'فروش', 'PURCHASE': 'خرید', 'RECEIVABLE': 'دریافتنی (خروج)',
                        'PAYABLE': 'پرداختنی (ورود)'}
            type_item = QTableWidgetItem(_TYPE_FA.get(_raw, _raw))
            self.docs_table.setItem(doc_index, 8, type_item)
            doc_index += 1

        self.docs_info_lbl.setText(f"📄 ریز اسناد باز: {person_name} ({doc_index} سند)")

        self.docs_info_lbl.setText(
            'نام: {} | تعداد اسناد: {} | مبلغ کل مانده: {:,} ریال'.format(person_name, doc_index, person_total))

    def _build_chart(self, bucket_totals, persons_data):
        """نمودار میله‌ای Aging"""
        if not persons_data:
            self.chart_view.setHtml(
                "<p style='text-align:center; color:#888; padding:40px;'>"
                "داده‌ای برای نمایش نمودار وجود ندارد.</p>"
            )
            return

        labels = [l for _, _, l in self.AGING_BUCKETS]
        max_val = max(bucket_totals) if bucket_totals else 1

        # رنگ برای هر بازه
        colors = ['#16a34a', '#0891b2', '#ea580c', '#dc2626', '#7c2d12']

        bar_w = 60
        gap = 20
        chart_h = 300
        chart_w = max(700, len(labels) * (bar_w + gap))

        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_w}" '
            f'height="{chart_h + 80}" style="font-family:Tahoma; direction:rtl;">',
            f'<rect width="100%" height="100%" fill="#f8fafc" rx="10"/>',
            f'<text x="{chart_w/2}" y="25" text-anchor="middle" '
            f'font-size="16" font-weight="bold" fill="#46505f">'
            f'توزیع مانده باز به تفکیک سن (ریال)</text>',
        ]

        for idx, (label, total) in enumerate(zip(labels, bucket_totals)):
            x = 40 + idx * (bar_w + gap)
            bar_h = int((total / max_val) * (chart_h - 80)) if max_val > 0 else 0
            y = chart_h - bar_h

            svg.append(
                f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
                f'fill="{colors[idx]}" rx="4"/>'
            )
            svg.append(
                f'<text x="{x + bar_w/2}" y="{chart_h + 20}" '
                f'text-anchor="middle" font-size="11" fill="#6b7686">{label}</text>'
            )
            svg.append(
                f'<text x="{x + bar_w/2}" y="{y - 5}" '
                f'text-anchor="middle" font-size="11" font-weight="bold" fill="#46505f">'
                f'{total:,}</text>'
            )

        svg.append('</svg>')
        self.chart_view.setHtml(
            f"<div style='text-align:center; padding:10px;'>{''.join(svg)}</div>"
        )

    def _build_alerts(self, alerts, bucket_totals, grand_total):
        """نمایش هشدارهای مهم"""
        critical_amount = bucket_totals[-1]  # بیش از 180 روز
        over_90_amount = bucket_totals[-1] + bucket_totals[-2]  # بیش از 90 روز

        if grand_total > 0:
            critical_pct = (critical_amount / grand_total) * 100
            over_90_pct = (over_90_amount / grand_total) * 100
        else:
            critical_pct = over_90_pct = 0

        # وضعیت کلی
        if critical_pct > 30:
            status, emoji, color = "بحرانی", "🚨", "#dc2626"
        elif critical_pct > 15:
            status, emoji, color = "نیاز به پیگیری فوری", "️", "#ea580c"
        elif critical_pct > 5:
            status, emoji, color = "قابل قبول با ریسک", "🟡", "#eab308"
        else:
            status, emoji, color = "سالم", "✅", "#16a34a"

        html = f"""
<html dir='rtl' lang='fa'><head><meta charset='utf-8'>
<style>
    body {{ font-family: Tahoma; padding: 20px; background: #f8fafc; color: #243144; }}
    .status-box {{ 
        background: {color}; color: white; padding: 20px; 
        border-radius: 10px; text-align: center; margin: 15px 0;
    }}
    .status-box h2 {{ margin: 0; font-size: 24px; }}
    .status-box p {{ margin: 10px 0 0 0; font-size: 14px; }}
    .section {{ 
        background: white; padding: 15px; margin: 10px 0; 
        border-radius: 8px; border-right: 4px solid #2563eb;
    }}
    h3 {{ color: #46505f; margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #5b6675; color: white; padding: 8px; }}
    td {{ border-bottom: 1px solid #e2e8f0; padding: 8px; }}
    .critical {{ background: #fee2e2; }}
    .warning {{ background: #fef3c7; }}
    .metric {{ 
        display: inline-block; padding: 10px 15px; margin: 5px;
        background: #f1f5f9; border-radius: 5px;
    }}
    .metric b {{ color: #2563eb; }}
</style></head><body>

<div class='status-box'>
    <h2>{emoji} وضعیت: {status}</h2>
    <p>
        {critical_pct:.1f}% از مانده باز شما بیش از 180 روز سن دارد<br>
        {over_90_pct:.1f}% بیش از 90 روز سن دارد
    </p>
</div>

<div class='section'>
    <h3>📊 شاخص‌های کلیدی</h3>
    <div class='metric'><b>جمع مانده باز:</b> {grand_total:,} ریال</div>
    <div class='metric'><b>بحرانی (>180 روز):</b> {critical_amount:,} ریال ({critical_pct:.1f}%)</div>
    <div class='metric'><b>بیش از 90 روز:</b> {over_90_amount:,} ریال ({over_90_pct:.1f}%)</div>
    <div class='metric'><b>تعداد موارد بحرانی:</b> {len(alerts)} مورد</div>
</div>
"""

        if alerts:
            html += """
<div class='section' style='border-right-color: #dc2626;'>
    <h3> موارد بحرانی (بیش از 180 روز)</h3>
    <table>
        <tr><th>شخص</th><th>شماره سند</th><th>مبلغ مانده</th><th>سن (روز)</th></tr>
"""
            for a in sorted(alerts, key=lambda x: x['days'], reverse=True):
                html += f"""
        <tr class='critical'>
            <td>{a['person']}</td>
            <td>{a['doc']}</td>
            <td>{a['amount']:,} ریال</td>
            <td>{a['days']} روز</td>
        </tr>
"""
            html += """
    </table>
</div>
"""
        else:
            html += """
<div class='section' style='border-right-color: #16a34a;'>
    <h3>✅ هیچ مورد بحرانی وجود ندارد</h3>
    <p>هیچ سندی بیش از 180 روز باز نمانده است.</p>
</div>
"""

        html += """
<div class='section' style='border-right-color: #0891b2;'>
    <h3>💡 توصیه‌های مدیریتی</h3>
    <ul>
        <li><b>برای موارد بیش از 180 روز:</b> تماس فوری با شخص و تعیین برنامه تسویه</li>
        <li><b>برای موارد 91-180 روز:</b> ارسال یادآوری کتبی و پیگیری تلفنی</li>
        <li><b>برای موارد 61-90 روز:</b> ارسال یادآوری ایمیلی/پیامکی</li>
        <li><b>برای موارد 31-60 روز:</b> ثبت در سیستم پیگیری معمول</li>
        <li><b>برای موارد جاری:</b> نظارت عادی</li>
    </ul>
</div>

</body></html>"""

        self.alerts_text.setHtml(html)

    # =================================================================
    # چاپ و خروجی
    # =================================================================
    def _build_html_content(self) -> str:
        rows_count = self.persons_table.rowCount()
        if rows_count == 0:
            return ""

        report_type = self.report_type_combo.currentText()
        cut_date = self.cut_date_edit.date().toString('yyyy-MM-dd')

        html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="utf-8">
    <title>گزارش سن بدهی‌ها و مطالبات</title>
    <style>
        @media print {{
            body {{ margin: 0; padding: 10px; }}
            .no-print {{ display: none; }}
        }}
        body {{ font-family: Tahoma, Arial, sans-serif; padding: 20px; }}
        h2 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #999; padding: 8px; text-align: center; }}
        th {{ background: #5b6675; color: white; }}
        tr:nth-child(even) {{ background: #f8fafc; color: #243144; }}
        .total-row {{ background: #e2e8f0; font-weight: bold; }}
    </style>
</head>
<body>
    <button class="no-print" onclick="window.print()"
        style="padding:10px 20px; background:#2563eb; color:white; border:none;
        border-radius:5px; cursor:pointer;">🖨️ چاپ</button>
    <h2>گزارش سن بدهی‌ها و مطالبات</h2>
    <p style="text-align:center;">نوع: {report_type} | باز تاریخ سررسید: {cut_date}</p>

    <table>
        <tr>
            <th>ردیف</th><th>نام شخص</th><th>نقش</th>
            <th>جاری (0-30)</th><th>31-60 روز</th><th>61-90 روز</th>
            <th>91-180 روز</th><th>بیش از 180 روز</th><th>جمع</th>
        </tr>
'''

        total_all = 0
        total_by_bucket = [0] * len(self.AGING_BUCKETS)

        for i in range(rows_count):
            name = self.persons_table.item(i, 1).text() if self.persons_table.item(i, 1) else ''
            role = self.persons_table.item(i, 2).text() if self.persons_table.item(i, 2) else ''
            
            row_total = 0
            cells = []
            for j in range(5):
                val_str = self.persons_table.item(i, 3+j).text().replace(',', '') if self.persons_table.item(i, 3+j) else '0'
                try:
                    val = int(val_str)
                except ValueError:
                    val = 0
                row_total += val
                total_by_bucket[j] += val
                cells.append(f"{val:,}")

            total_all += row_total

            html += f'''<tr>
                <td>{i+1}</td><td>{name}</td><td>{role}</td>
                <td>{cells[0]}</td><td>{cells[1]}</td><td>{cells[2]}</td>
                <td>{cells[3]}</td><td>{cells[4]}</td>
                <td><b>{row_total:,}</b></td>
            </tr>'''

        html += f'''
        <tr class="total-row">
            <td colspan="3">جمع کل</td>
            <td>{total_by_bucket[0]:,}</td><td>{total_by_bucket[1]:,}</td>
            <td>{total_by_bucket[2]:,}</td><td>{total_by_bucket[3]:,}</td>
            <td>{total_by_bucket[4]:,}</td>
            <td><b>{total_all:,}</b></td>
        </tr>
    </table>

    <p style="text-align:center; color:#666; margin-top:20px;">
        گزارش تولید شده توسط سیستم انبار پالت
    </p>
</body>
</html>'''
        return html

    def _print_report(self):
        if self.persons_table.rowCount() == 0:
            QMessageBox.warning(self, "چاپ", "داده‌ای برای چاپ وجود ندارد.")
            return
        try:
            html = self._build_html_content()
            if not html:
                return
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.html', prefix='aging_',
                delete=False, encoding='utf-8'
            )
            tmp.write(html)
            tmp.close()
            webbrowser.open(f'file://{tmp.name}')
            QMessageBox.information(self, "چاپ",
                "گزارش در مرورگر باز شد. با Ctrl+P چاپ کنید.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))

    def _export_html(self):
        if self.persons_table.rowCount() == 0:
            QMessageBox.warning(self, "خروجی", "داده‌ای برای خروجی وجود ندارد.")
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, 'ذخیره گزارش Aging',
                'aging_report.html', 'HTML Files (*.html)'
            )
            if not path:
                return
            html = self._build_html_content()
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "خروجی", f"ذخیره شد:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
