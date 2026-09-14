# -*- coding: utf-8 -*-
"""
گزارش سود و زیان (Profit & Loss)
محاسبه بر اساس اسناد فروش و خرید موجود در financial_documents
نسخه تمیز و اصلاح‌شده
"""
import webbrowser
import tempfile
from collections import defaultdict
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QComboBox, 
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QDateEdit, QPushButton,
    QHeaderView, QMessageBox, QFrame, QTextBrowser,
    QTabWidget, QWidget, QAbstractItemView, QFileDialog,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from app.core.jalali import jalali_date_display_from_iso


# ===================================================================
# کارت P&L
# ===================================================================
class PnlCard(QFrame):
    def __init__(self, title: str, value: str = "0 ریال",
                 color: str = "#2563eb", subtitle: str = "",
                 is_negative: bool = False, font_size: int = 18) -> None:
        super().__init__()
        self.setObjectName('Card')
        border = "dashed" if is_negative else "solid"
        self.setStyleSheet(
            f"QFrame#Card {{ border: 2px {border} {color}; "
            f"border-radius: 8px; padding: 10px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; color: #555;")
        title_lbl.setAlignment(Qt.AlignCenter)
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"font-size: {font_size}px; font-weight: bold; color: {color};"
        )
        self.value_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)
        layout.addWidget(self.value_lbl)
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("font-size: 11px; color: #888;")
            sub_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(sub_lbl)


# ===================================================================
# فرم اصلی گزارش سود و زیان
# ===================================================================
class PnlReportWindow(QDialog):
    def __init__(self, db, user_data) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.setWindowTitle('گزارش سود و زیان')
        self.resize(1300, 850)
        self.setLayoutDirection(Qt.RightToLeft)
        self._chart_html = ''
        self._summary_html = ''
        self._last = {}
        self._build_ui()
        self._run_report()

    def _money(self, value: int) -> str:
        """نمایش مبلغ با فرمت مناسب"""
        if value < 0:
            return f"({abs(value):,}) ریال"
        return f"{value:,} ریال"

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)
        # ============================================================
        # فیلتر بازه
        # ============================================================
        filter_group = QGroupBox("بازه گزارش سود و زیان")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)
        filter_layout.addWidget(QLabel("از تاریخ:"))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.date_from)
        self.jalali_from_lbl = QLabel('')  # pnl_jalali
        self.jalali_from_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        filter_layout.addWidget(self.jalali_from_lbl)
        filter_layout.addWidget(QLabel("تا تاریخ:"))
        self.date_to = QDateEdit(QDate.currentDate().addDays(365))
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.date_to)
        self.jalali_to_lbl = QLabel('')  # pnl_jalali
        self.jalali_to_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        filter_layout.addWidget(self.jalali_to_lbl)
        self.date_from.dateChanged.connect(lambda *a: self._update_pnl_jalali())
        self.date_to.dateChanged.connect(lambda *a: self._update_pnl_jalali())
        self._update_pnl_jalali()
        apply_btn = QPushButton("محاسبه سود و زیان")
        apply_btn.setObjectName('PrimaryButton')
        apply_btn.clicked.connect(self._run_report)
        filter_layout.addWidget(apply_btn)
        clear_btn = QPushButton("پاک کردن فیلتر")
        clear_btn.setObjectName('SecondaryButton')
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)
        filter_layout.addStretch()
        root.addWidget(filter_group)
        # ============================================================
        # ردیف اول: فروش
        # ============================================================
        sales_layout = QHBoxLayout()
        sales_layout.setSpacing(12)
        self.card_sales = PnlCard("فروش ناخالص", "0 ریال", "#16a34a",
                                  "درآمد کل فروش", font_size=17)
        self.card_sales_returns = PnlCard("برگشت از فروش", "0 ریال", "#dc2626",
                                          "کسر می‌شود", is_negative=True, font_size=17)
        self.card_net_sales = PnlCard("فروش خالص", "0 ریال", "#2563eb",
                                      "درآمد واقعی فروش", font_size=20)
        sales_layout.addWidget(self.card_sales)
        sales_layout.addWidget(self.card_sales_returns)
        sales_layout.addWidget(self.card_net_sales)
        root.addLayout(sales_layout)
        # ============================================================
        # ردیف دوم: خرید
        # ============================================================
        purchases_layout = QHBoxLayout()
        purchases_layout.setSpacing(12)
        self.card_purchases = PnlCard("خرید ناخالص", "0 ریال", "#ea580c",
                                      "بهای کل خرید", font_size=17)
        self.card_purchase_returns = PnlCard("برگشت از خرید", "0 ریال", "#9333ea",
                                             "کسر می‌شود", is_negative=True, font_size=17)
        self.card_net_purchases = PnlCard("خرید خالص", "0 ریال", "#6b7686",
                                          "بهای تمام شده", font_size=20)
        purchases_layout.addWidget(self.card_purchases)
        purchases_layout.addWidget(self.card_purchase_returns)
        purchases_layout.addWidget(self.card_net_purchases)
        root.addLayout(purchases_layout)
        # ============================================================
        # ردیف سوم: سود
        # ============================================================
        profit_layout = QHBoxLayout()
        profit_layout.setSpacing(12)
        self.card_gross_profit = PnlCard("سود ناخالص", "0 ریال", "#059669",
                                         "فروش خالص − خرید خالص", font_size=22)
        self.card_margin = PnlCard("حاشیه سود", "0%", "#0891b2",
                                   "سود ÷ فروش × 100", font_size=22)
        profit_layout.addWidget(self.card_gross_profit, 3)
        profit_layout.addWidget(self.card_margin, 1)
        root.addLayout(profit_layout)
        # ============================================================
        # ردیف چهارم: هزینه‌ها و سود خالص
        # ============================================================
        expenses_layout = QHBoxLayout()
        expenses_layout.setSpacing(12)
        self.card_expenses = PnlCard("هزینه‌های عملیاتی (شامل حمل و کسری)", "0 ریال", "#7c3aed",
                                     "حمل + هزینه‌ها + کسری انبارگردانی", font_size=17)
        self.card_scrap = PnlCard("درآمد ضایعات (عملیاتی)", "0 ریال", "#0891b2",
                                  "فروش خرده‌چوب و ضایعات", font_size=17)
        self.card_net_profit = PnlCard("سود خالص", "0 ریال", "#059669",
                                       "سود ناخالص − هزینه‌ها + ضایعات", font_size=22)
        expenses_layout.addWidget(self.card_expenses)
        expenses_layout.addWidget(self.card_scrap)
        expenses_layout.addWidget(self.card_net_profit)
        root.addLayout(expenses_layout)
        # ============================================================
        # جدول جزئیات (مخفی — در پنجرهٔ تحلیل نمایش داده می‌شود)
        # ============================================================
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(6)
        self.details_table.setHorizontalHeaderLabels([
            'ردیف', 'تاریخ', 'شماره سند', 'نوع', 'طرف حساب', 'مبلغ (ریال)'
        ])
        self.details_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.details_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.details_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.details_table.verticalHeader().setVisible(False)
        self.analysis_dialog = None
        # ============================================================
        # دکمه‌های پایین
        # ============================================================
        bottom_row = QHBoxLayout()
        self.status_lbl = QLabel("آماده")
        self.status_lbl.setStyleSheet("color: #555;")
        bottom_row.addWidget(self.status_lbl)
        bottom_row.addStretch()
        print_btn = QPushButton("🖨️ چاپ گزارش")
        print_btn.setObjectName('SecondaryButton')
        print_btn.clicked.connect(self._print_report)
        bottom_row.addWidget(print_btn)
        export_btn = QPushButton("💾 خروجی HTML")
        export_btn.setObjectName('SecondaryButton')
        export_btn.clicked.connect(self._export_html)
        bottom_row.addWidget(export_btn)
        analysis_btn = QPushButton("📊 جزئیات و تحلیل کامل")
        analysis_btn.setObjectName('PrimaryButton')
        analysis_btn.clicked.connect(self._open_analysis_dialog)
        bottom_row.addWidget(analysis_btn)
        close_btn = QPushButton("بستن")
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)
        root.addLayout(bottom_row)

    def _clear_filters(self):
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate().addDays(365))
        self._run_report()

    # ------------------------------------------------------------ Report
    def _update_pnl_jalali(self):  # pnl_jalali
        try:
            from app.core.jalali import jalali_date_display_from_iso
            d1 = self.date_from.date().toString('yyyy-MM-dd')
            d2 = self.date_to.date().toString('yyyy-MM-dd')
            self.jalali_from_lbl.setText('از تاریخ: ' + jalali_date_display_from_iso(d1))
            self.jalali_to_lbl.setText('تا تاریخ: ' + jalali_date_display_from_iso(d2))
        except Exception:
            pass

    def _run_report(self):
        """محاسبه و نمایش گزارش سود و زیان"""
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        if date_from > date_to:
            QMessageBox.warning(self, "خطا", "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.")
            return
        with self.db.connect() as conn:
            # ۱. فروش عادی
            sales_rows = conn.execute('''
                SELECT fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                       COALESCE(p.first_name || ' ' || p.last_name, 'نامشخص') as person_name
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.finance_date BETWEEN ? AND ?
                  AND fd.operation_type = 'OUTBOUND_ISSUE'
                  AND fd.status != 'CANCELLED'
                  AND fd.finance_no NOT LIKE 'BS-%'
                  AND fd.finance_no NOT LIKE 'WP-%'
                ORDER BY fd.finance_date DESC
            ''', [date_from, date_to]).fetchall()
            # ۲. برگشت از فروش
            sales_return_rows = conn.execute('''
                SELECT fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                       COALESCE(p.first_name || ' ' || p.last_name, 'نامشخص') as person_name
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.finance_date BETWEEN ? AND ?
                  AND fd.operation_type = 'OUTBOUND_ISSUE'
                  AND fd.status != 'CANCELLED'
                  AND fd.finance_no LIKE 'BS-%'
                ORDER BY fd.finance_date DESC
            ''', [date_from, date_to]).fetchall()
            # ۳. خرید عادی
            purchase_rows = conn.execute('''
                SELECT fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                       COALESCE(p.first_name || ' ' || p.last_name, 'نامشخص') as person_name
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.finance_date BETWEEN ? AND ?
                  AND fd.operation_type = 'INBOUND_RECEIPT'
                  AND fd.status != 'CANCELLED'
                  AND fd.finance_no NOT LIKE 'BR-%'
                ORDER BY fd.finance_date DESC
            ''', [date_from, date_to]).fetchall()
            # ۴. برگشت از خرید
            purchase_return_rows = conn.execute('''
                SELECT fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                       COALESCE(p.first_name || ' ' || p.last_name, 'نامشخص') as person_name
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.finance_date BETWEEN ? AND ?
                  AND fd.operation_type = 'INBOUND_RECEIPT'
                  AND fd.status != 'CANCELLED'
                  AND fd.finance_no LIKE 'BR-%'
                ORDER BY fd.finance_date DESC
            ''', [date_from, date_to]).fetchall()
            # ۵. هزینه‌های حمل
            freight_rows = conn.execute('''
                SELECT fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                       COALESCE(p.first_name || ' ' || p.last_name, 'نامشخص') as person_name
                FROM financial_documents fd
                LEFT JOIN persons p ON p.id = fd.counterparty_person_id
                WHERE fd.finance_date BETWEEN ? AND ?
                  AND fd.operation_type IN ('OUTBOUND_FREIGHT', 'INBOUND_FREIGHT')
                  AND fd.status != 'CANCELLED'
                ORDER BY fd.finance_date DESC
            ''', [date_from, date_to]).fetchall()
            freight = sum(int(r['total_amount'] or 0) for r in freight_rows)
            # ۶. هزینه‌های عملیاتی
            try:
                expense_rows = conn.execute('''
                    SELECT id, expense_date, amount, description
                    FROM expenses
                    WHERE expense_date BETWEEN ? AND ?
                    ORDER BY expense_date DESC
                ''', [date_from, date_to]).fetchall()
            except Exception:
                expense_rows = []
            operating_expenses = sum(int(r['amount'] or 0) for r in expense_rows)
            # ۷. درآمد ضایعات
            try:
                sc = conn.execute(
                    "SELECT COALESCE(SUM(total_amount),0) FROM financial_documents "
                    "WHERE finance_no LIKE 'WP-%' AND status!='CANCELLED' "
                    "AND finance_date BETWEEN ? AND ?", (date_from, date_to)).fetchone()
                scrap_income = int(sc[0] or 0)
            except Exception:
                scrap_income = 0
            # ۸. کسری انبارگردانی تاییدشده
            try:
                st = conn.execute(
                    "SELECT COALESCE(SUM(total_value_loss),0) FROM stock_takes "
                    "WHERE status='APPROVED' AND take_date BETWEEN ? AND ?",
                    (date_from, date_to)).fetchone()
                stocktake_loss = int(st[0] or 0)
            except Exception:
                stocktake_loss = 0
        # ===== محاسبات =====
        total_sales = sum(int(r['total_amount'] or 0) for r in sales_rows)
        total_sales_returns = sum(int(r['total_amount'] or 0) for r in sales_return_rows)
        net_sales = total_sales - total_sales_returns
        total_purchases = sum(int(r['total_amount'] or 0) for r in purchase_rows)
        total_purchase_returns = sum(int(r['total_amount'] or 0) for r in purchase_return_rows)
        net_purchases = total_purchases - total_purchase_returns
        gross_profit = net_sales - net_purchases
        margin = (gross_profit / net_sales * 100) if net_sales > 0 else 0
        total_expenses = freight + operating_expenses + stocktake_loss
        net_profit = gross_profit - total_expenses + scrap_income
        # ذخیره برای چاپ/خلاصه
        self._last = {
            'freight': freight, 'operating_expenses': operating_expenses,
            'stocktake_loss': stocktake_loss, 'scrap_income': scrap_income,
            'total_expenses': total_expenses, 'net_profit': net_profit,
        }
        # ===== به‌روزرسانی کارت‌ها =====
        self.card_sales.value_lbl.setText(f"{total_sales:,} ریال")
        self.card_sales_returns.value_lbl.setText(f"({total_sales_returns:,}) ریال")
        self.card_net_sales.value_lbl.setText(f"{net_sales:,} ریال")
        self.card_purchases.value_lbl.setText(f"{total_purchases:,} ریال")
        self.card_purchase_returns.value_lbl.setText(f"({total_purchase_returns:,}) ریال")
        self.card_net_purchases.value_lbl.setText(f"{net_purchases:,} ریال")
        profit_color = "#059669" if gross_profit >= 0 else "#dc2626"
        self.card_gross_profit.value_lbl.setText(self._money(gross_profit))
        self.card_gross_profit.value_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {profit_color};")
        self.card_margin.value_lbl.setText(f"{margin:.1f}%")
        self.card_margin.value_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {profit_color};")
        self.card_expenses.value_lbl.setText(f"{total_expenses:,} ریال")
        self.card_scrap.value_lbl.setText(f"{scrap_income:,} ریال")
        net_color = "#059669" if net_profit >= 0 else "#dc2626"
        self.card_net_profit.value_lbl.setText(self._money(net_profit))
        self.card_net_profit.value_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {net_color};")
        # ===== پر کردن جدول جزئیات =====
        all_rows = []
        for r in sales_rows:
            all_rows.append({'date': r['finance_date'], 'no': r['finance_no'],
                             'type': 'فروش', 'person': r['person_name'],
                             'amount': int(r['total_amount'] or 0)})
        for r in sales_return_rows:
            all_rows.append({'date': r['finance_date'], 'no': r['finance_no'],
                             'type': 'برگشت فروش', 'person': r['person_name'],
                             'amount': -int(r['total_amount'] or 0)})
        for r in purchase_rows:
            all_rows.append({'date': r['finance_date'], 'no': r['finance_no'],
                             'type': 'خرید', 'person': r['person_name'],
                             'amount': -int(r['total_amount'] or 0)})
        for r in purchase_return_rows:
            all_rows.append({'date': r['finance_date'], 'no': r['finance_no'],
                             'type': 'برگشت خرید', 'person': r['person_name'],
                             'amount': int(r['total_amount'] or 0)})
        if stocktake_loss > 0:
            all_rows.append({'date': date_to, 'no': 'STOCK-TAKE',
                             'type': 'کسری انبارگردانی', 'person': '—',
                             'amount': -stocktake_loss})
        all_rows.sort(key=lambda x: x['date'] or '', reverse=True)
        self.details_table.setRowCount(len(all_rows))
        for i, row in enumerate(all_rows):
            self.details_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.details_table.setItem(i, 1, QTableWidgetItem(
                jalali_date_display_from_iso(row['date']) if row['date'] else '-'))
            self.details_table.setItem(i, 2, QTableWidgetItem(row['no']))
            self.details_table.setItem(i, 3, QTableWidgetItem(row['type']))
            self.details_table.setItem(i, 4, QTableWidgetItem(row['person']))
            amount_item = QTableWidgetItem(self._money(row['amount']))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.details_table.setItem(i, 5, amount_item)
        # ===== نمودار و خلاصه =====
        self._build_chart(sales_rows, sales_return_rows, purchase_rows, purchase_return_rows)
        self._build_summary(
            total_sales, total_sales_returns, net_sales,
            total_purchases, total_purchase_returns, net_purchases,
            gross_profit, margin,
            len(sales_rows), len(sales_return_rows),
            len(purchase_rows), len(purchase_return_rows),
            freight=freight, operating_expenses=operating_expenses,
            stocktake_loss=stocktake_loss, scrap_income=scrap_income,
            net_profit=net_profit)
        self.status_lbl.setText(
            f"سود ناخالص: {self._money(gross_profit)} | سود خالص: {self._money(net_profit)} | حاشیه سود: {margin:.1f}%")

    # ------------------------------------------------------------ Chart
    def _build_chart(self, sales_rows, sales_return_rows,
                     purchase_rows, purchase_return_rows):
        """نمودار مقایسه فروش و خرید (SVG — نمایش در QWebEngineView)"""
        if not sales_rows and not purchase_rows and not sales_return_rows and not purchase_return_rows:
            self._chart_html = (
                "<p style='text-align:center; color:#888; padding:40px;'>"
                "داده‌ای برای نمایش نمودار وجود ندارد.</p>")
            return
        daily_sales = defaultdict(float)
        daily_purchases = defaultdict(float)
        for r in sales_rows:
            key = jalali_date_display_from_iso(r['finance_date']) if r['finance_date'] else '-'
            daily_sales[key] += int(r['total_amount'] or 0)
        for r in sales_return_rows:
            key = jalali_date_display_from_iso(r['finance_date']) if r['finance_date'] else '-'
            daily_sales[key] -= int(r['total_amount'] or 0)
        for r in purchase_rows:
            key = jalali_date_display_from_iso(r['finance_date']) if r['finance_date'] else '-'
            daily_purchases[key] += int(r['total_amount'] or 0)
        for r in purchase_return_rows:
            key = jalali_date_display_from_iso(r['finance_date']) if r['finance_date'] else '-'
            daily_purchases[key] -= int(r['total_amount'] or 0)
        all_dates = sorted(set(list(daily_sales.keys()) + list(daily_purchases.keys())))[:15]
        max_val = max(
            max([abs(daily_sales.get(d, 0)) for d in all_dates] or [1]),
            max([abs(daily_purchases.get(d, 0)) for d in all_dates] or [1]),
            1)
        bar_w = 30
        group_gap = 20
        chart_h = 280
        chart_w = max(700, len(all_dates) * (bar_w * 2 + group_gap))
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_w}" '
            f'height="{chart_h + 80}" style="font-family:Tahoma; direction:rtl;">',
            f'<rect width="100%" height="100%" fill="#f8fafc" rx="10"/>',
            f'<text x="{chart_w/2}" y="25" text-anchor="middle" '
            f'font-size="16" font-weight="bold" fill="#46505f">'
            f'مقایسه فروش و خرید بر اساس تاریخ (ریال)</text>',
            f'<rect x="20" y="40" width="15" height="15" fill="#16a34a" rx="3"/>',
            f'<text x="40" y="52" font-size="11" fill="#6b7686">فروش خالص</text>',
            f'<rect x="130" y="40" width="15" height="15" fill="#ea580c" rx="3"/>',
            f'<text x="150" y="52" font-size="11" fill="#6b7686">خرید خالص</text>',
        ]
        for idx, date in enumerate(all_dates):
            base_x = 40 + idx * (bar_w * 2 + group_gap)
            s_val = daily_sales.get(date, 0)
            p_val = daily_purchases.get(date, 0)
            s_h = int((abs(s_val) / max_val) * (chart_h - 80))
            p_h = int((abs(p_val) / max_val) * (chart_h - 80))
            s_y = chart_h - s_h
            p_y = chart_h - p_h
            svg.append(f'<rect x="{base_x}" y="{s_y}" width="{bar_w}" height="{s_h}" fill="#16a34a" rx="3"/>')
            svg.append(f'<rect x="{base_x + bar_w + 2}" y="{p_y}" width="{bar_w}" height="{p_h}" fill="#ea580c" rx="3"/>')
            svg.append(f'<text x="{base_x + bar_w}" y="{chart_h + 20}" text-anchor="middle" font-size="9" fill="#6b7686">{date}</text>')
        svg.append('</svg>')
        self._chart_html = f"<div style='text-align:center; padding:10px;'>{''.join(svg)}</div>"

    # ------------------------------------------------------------ Summary
    def _build_summary(self, total_sales, total_sales_returns, net_sales,
                       total_purchases, total_purchase_returns, net_purchases,
                       gross_profit, margin,
                       sales_count, sales_return_count,
                       purchase_count, purchase_return_count,
                       freight=0, operating_expenses=0, stocktake_loss=0,
                       scrap_income=0, net_profit=None):
        """خلاصه تحلیلی HTML"""
        total_expenses = freight + operating_expenses + stocktake_loss
        if net_profit is None:
            net_profit = gross_profit - total_expenses + scrap_income
        sales_ret_ratio = (total_sales_returns / total_sales * 100) if total_sales > 0 else 0
        purch_ret_ratio = (total_purchase_returns / total_purchases * 100) if total_purchases > 0 else 0
        if gross_profit > 0:
            status, emoji, color = "سودده", "✅", "#059669"
        elif gross_profit < 0:
            status, emoji, color = "زیان‌ده", "❌", "#dc2626"
        else:
            status, emoji, color = "سر به سر", "⚠️", "#f59e0b"
        net_color = "#059669" if net_profit >= 0 else "#dc2626"
        html = f"""
<html dir='rtl' lang='fa'><head><meta charset='utf-8'>
<style>
body {{ font-family: Tahoma; padding: 20px; background: #0f172a; color: #f5f7fa; }}
.section {{ background: #1e293b; padding: 15px; margin: 10px 0;
border-radius: 8px; border-right: 4px solid #2563eb; }}
h3 {{ color: #f5f7fa; margin-top: 0; }}
.positive {{ color: #059669; font-weight: bold; }}
.negative {{ color: #dc2626; font-weight: bold; }}
.warning {{ color: #ea580c; }}
table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #334155; }}
.label {{ color: #94a3b8; }}
.value {{ text-align: left; font-weight: bold; color: #f5f7fa; }}
</style></head><body>
<div class='section'>
<h3>{emoji} وضعیت کلی: {status}</h3>
<p>در بازه انتخابی، شرکت <b>{status}</b> بوده است.</p>
</div>
<div class='section'>
<h3>💰 درآمد فروش</h3>
<table>
<tr><td class='label'>تعداد فاکتورهای فروش:</td><td class='value'>{sales_count} سند</td></tr>
<tr><td class='label'>مبلغ فروش ناخالص:</td><td class='value'>{total_sales:,} ریال</td></tr>
<tr><td class='label'>تعداد برگشت فروش:</td><td class='value'>{sales_return_count} سند</td></tr>
<tr><td class='label'>مبلغ برگشت فروش:</td><td class='value negative'>({total_sales_returns:,}) ریال</td></tr>
<tr><td class='label'>نسبت برگشت به فروش:</td><td class='value'>{sales_ret_ratio:.1f}%</td></tr>
<tr><td class='label' style='font-size:14px;'><b>فروش خالص:</b></td>
<td class='value' style='font-size:14px;'><b>{net_sales:,} ریال</b></td></tr>
</table>
</div>
<div class='section'>
<h3> بهای خرید</h3>
<table>
<tr><td class='label'>تعداد فاکتورهای خرید:</td><td class='value'>{purchase_count} سند</td></tr>
<tr><td class='label'>مبلغ خرید ناخالص:</td><td class='value'>{total_purchases:,} ریال</td></tr>
<tr><td class='label'>تعداد برگشت خرید:</td><td class='value'>{purchase_return_count} سند</td></tr>
<tr><td class='label'>مبلغ برگشت خرید:</td><td class='value'>({total_purchase_returns:,}) ریال</td></tr>
<tr><td class='label'>نسبت برگشت به خرید:</td><td class='value'>{purch_ret_ratio:.1f}%</td></tr>
<tr><td class='label' style='font-size:14px;'><b>خرید خالص:</b></td>
<td class='value' style='font-size:14px;'><b>{net_purchases:,} ریال</b></td></tr>
</table>
</div>
<div class='section' style='border-right-color: {color};'>
<h3>📊 سود و زیان</h3>
<table>
<tr><td class='label'>فروش خالص:</td><td class='value'>{net_sales:,} ریال</td></tr>
<tr><td class='label'>بهای تمام شده (خرید خالص):</td><td class='value'>({net_purchases:,}) ریال</td></tr>
<tr><td class='label' style='font-size:16px;'><b>سود ناخالص:</b></td>
<td class='value' style='font-size:16px; color:{color};'><b>{gross_profit:,} ریال</b></td></tr>
<tr><td class='label' style='font-size:14px;'><b>حاشیه سود ناخالص:</b></td>
<td class='value' style='font-size:14px;'><b>{margin:.1f}%</b></td></tr>
</table>
</div>
<div class='section' style='border-right-color: #7c3aed;'>
<h3>💸 هزینه‌های عملیاتی</h3>
<table>
<tr><td class='label'>هزینه‌های حمل:</td><td class='value'>{freight:,} ریال</td></tr>
<tr><td class='label'>هزینه‌های عملیاتی ثبت‌شده:</td><td class='value'>{operating_expenses:,} ریال</td></tr>
<tr><td class='label'>کسری انبارگردانی:</td><td class='value negative'>({stocktake_loss:,}) ریال</td></tr>
<tr><td class='label'><b>جمع هزینه‌های عملیاتی:</b></td><td class='value'><b>{total_expenses:,} ریال</b></td></tr>
<tr><td class='label'>درآمد ضایعات:</td><td class='value positive'>+{scrap_income:,} ریال</td></tr>
</table>
</div>
<div class='section' style='border-right-color: {net_color};'>
<h3>🏁 سود خالص</h3>
<table>
<tr><td class='label'>سود ناخالص:</td><td class='value'>{gross_profit:,} ریال</td></tr>
<tr><td class='label'>کسر: جمع هزینه‌ها:</td><td class='value negative'>({total_expenses:,}) ریال</td></tr>
<tr><td class='label'>جمع: درآمد ضایعات:</td><td class='value positive'>+{scrap_income:,} ریال</td></tr>
<tr><td class='label' style='font-size:16px;'><b>سود خالص:</b></td>
<td class='value' style='font-size:16px; color:{net_color};'><b>{net_profit:,} ریال</b></td></tr>
</table>
</div>
</body></html>"""
        self._summary_html = html

    # ------------------------------------------------------------ Print / Export
    def _build_html_content(self) -> str:
        """ساخت HTML نهایی برای چاپ/خروجی"""
        rows_count = self.details_table.rowCount()
        if rows_count == 0:
            return ""
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        last = getattr(self, '_last', {})
        total_expenses = last.get('total_expenses', 0)
        scrap_income = last.get('scrap_income', 0)
        net_profit = last.get('net_profit', 0)
        profit_color = "#dcfce7" if net_profit >= 0 else "#fee2e2"
        html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8">
<title>گزارش سود و زیان</title>
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
.total-row {{ background: #e2e8f0; font-weight: bold; }}
.profit-row {{ background: {profit_color}; font-weight: bold; font-size: 14px; }}
</style>
</head>
<body>
<button class="no-print" onclick="window.print()"
style="padding:10px 20px; background:#2563eb; color:white; border:none;
border-radius:5px; cursor:pointer;">🖨️ چاپ</button>
<h2>گزارش سود و زیان</h2>
<p style="text-align:center;">بازه: {date_from} تا {date_to}</p>
<table>
<tr><th>شرح</th><th>مبلغ (ریال)</th></tr>
<tr><td>فروش ناخالص</td><td>{self.card_sales.value_lbl.text()}</td></tr>
<tr><td>کسر: برگشت از فروش</td><td>{self.card_sales_returns.value_lbl.text()}</td></tr>
<tr class="total-row"><td>فروش خالص</td><td>{self.card_net_sales.value_lbl.text()}</td></tr>
<tr><td>خرید ناخالص</td><td>{self.card_purchases.value_lbl.text()}</td></tr>
<tr><td>کسر: برگشت از خرید</td><td>{self.card_purchase_returns.value_lbl.text()}</td></tr>
<tr class="total-row"><td>خرید خالص (بهای تمام شده)</td><td>{self.card_net_purchases.value_lbl.text()}</td></tr>
<tr class="profit-row"><td>سود ناخالص</td><td>{self.card_gross_profit.value_lbl.text()}</td></tr>
<tr><td>حاشیه سود ناخالص</td><td>{self.card_margin.value_lbl.text()}</td></tr>
<tr><td>کسر: هزینه‌های عملیاتی (حمل + هزینه‌ها + کسری)</td><td>({total_expenses:,}) ریال</td></tr>
<tr><td>جمع: درآمد ضایعات</td><td>+{scrap_income:,} ریال</td></tr>
<tr class="profit-row"><td>سود خالص</td><td>{net_profit:,} ریال</td></tr>
</table>
<h3>جزئیات اسناد</h3>
<table>
<tr><th>ردیف</th><th>تاریخ</th><th>شماره سند</th><th>نوع</th><th>طرف حساب</th><th>مبلغ (ریال)</th></tr>'''
        for i in range(rows_count):
            row_data = []
            for j in range(6):
                item = self.details_table.item(i, j)
                row_data.append(item.text() if item else '')
            html += f'''<tr>
<td>{row_data[0]}</td><td>{row_data[1]}</td><td>{row_data[2]}</td>
<td>{row_data[3]}</td><td>{row_data[4]}</td><td>{row_data[5]}</td>
</tr>'''
        html += '''
</table>
<p style="text-align:center; color:#666; margin-top:20px;">
گزارش تولید شده توسط سیستم انبار پالت
</p>
</body>
</html>'''
        return html

    def _print_report(self):
        if self.details_table.rowCount() == 0:
            QMessageBox.warning(self, "چاپ", "داده‌ای برای چاپ وجود ندارد.")
            return
        try:
            html = self._build_html_content()
            if not html:
                return
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.html', prefix='pnl_',
                delete=False, encoding='utf-8')
            tmp.write(html)
            tmp.close()
            webbrowser.open('file:///' + tmp.name.replace('\\', '/'))
            QMessageBox.information(self, "چاپ",
                "گزارش در مرورگر باز شد. با Ctrl+P چاپ کنید.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))

    def _export_html(self):
        if self.details_table.rowCount() == 0:
            QMessageBox.warning(self, "خروجی", "داده‌ای برای خروجی وجود ندارد.")
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, 'ذخیره گزارش سود و زیان',
                'pnl_report.html', 'HTML Files (*.html)')
            if not path:
                return
            html = self._build_html_content()
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "خروجی", f"ذخیره شد:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))

    # ------------------------------------------------------------ Analysis dialog
    def _open_analysis_dialog(self):
        """پنجره تحلیل با سه تب + کامبو فیلتر (سازگار با هر دو نسخه ویجت‌ها)"""
        try:
            from PyQt5.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, QHBoxLayout,
                                         QTableWidget, QTableWidgetItem, QTextBrowser,
                                         QPushButton, QComboBox, QLabel, QWidget)
            dlg = QDialog(self)
            dlg.setWindowTitle('جزئیات و تحلیل سود و زیان')
            dlg.resize(1150, 720)
            dlg.setLayoutDirection(Qt.RightToLeft)
            lay = QVBoxLayout(dlg)
            tabs = QTabWidget()
            tabs.setLayoutDirection(Qt.RightToLeft)
            tabs.setDocumentMode(True)
            # --- تب ۱: جزئیات اسناد + کامبو فیلتر ---
            det_wrap = QWidget()
            det_layout = QVBoxLayout(det_wrap)
            filter_bar = QHBoxLayout()
            filter_bar.addWidget(QLabel('فیلتر نوع سند:'))
            filter_combo = QComboBox()
            filter_combo.setMinimumWidth(220)
            filter_combo.addItem('همه اسناد', 'ALL')
            types = []
            for r in range(self.details_table.rowCount()):
                it = self.details_table.item(r, 3)
                t = it.text().strip() if it else ''
                if t and t not in types:
                    types.append(t)
            for t in types:
                filter_combo.addItem(t, t)
            filter_bar.addWidget(filter_combo, 1)
            count_lbl = QLabel('')
            count_lbl.setStyleSheet('color:#555;')
            filter_bar.addWidget(count_lbl)
            det_layout.addLayout(filter_bar)
            det = QTableWidget()
            ncols = self.details_table.columnCount()
            det.setColumnCount(ncols)
            headers = []
            for c in range(ncols):
                h = self.details_table.horizontalHeaderItem(c)
                headers.append(h.text() if h else '')
            det.setHorizontalHeaderLabels(headers)
            det.setEditTriggers(QAbstractItemView.NoEditTriggers)
            det.setSelectionBehavior(QAbstractItemView.SelectRows)
            det.verticalHeader().setVisible(False)

            def _parse_money(txt):
                t = (txt or '').replace('ریال', '').replace(',', '').strip()
                neg = t.startswith('(') and t.endswith(')')
                if neg:
                    t = t[1:-1]
                try:
                    v = int(t)
                except ValueError:
                    return 0
                return -v if neg else v

            def apply_filter(*_a):
                mode = filter_combo.currentData()
                rows_data = []
                for r in range(self.details_table.rowCount()):
                    vals = []
                    for c in range(ncols):
                        it = self.details_table.item(r, c)
                        vals.append(it.text() if it else '')
                    if mode != 'ALL' and (vals[3] if len(vals) > 3 else '') != mode:
                        continue
                    rows_data.append(vals)
                det.setRowCount(len(rows_data))
                tot = 0
                for ri, vals in enumerate(rows_data):
                    tot += _parse_money(vals[5] if len(vals) > 5 else '')
                    for c, v in enumerate(vals):
                        det.setItem(ri, c, QTableWidgetItem(v))
                det.resizeColumnsToContents()
                count_lbl.setText('ردیف: {} | جمع مبلغ: {:,} ریال'.format(len(rows_data), tot))

            filter_combo.currentIndexChanged.connect(apply_filter)
            det_layout.addWidget(det, 1)
            apply_filter()
            tabs.addTab(det_wrap, '📋 جزئیات اسناد')
            # --- تب ۲: نمودار (هر منبعی که موجود باشد) ---
            chart_html = getattr(self, '_chart_html', '') or ''
            if not chart_html and hasattr(self, 'chart_view'):
                try:
                    chart_html = self.chart_view.toHtml()
                except Exception:
                    chart_html = ''
            try:
                from PyQt5.QtWebEngineWidgets import QWebEngineView
                ch = QWebEngineView()
            except Exception:
                ch = QTextBrowser()
            ch.setHtml(chart_html or "<p style='text-align:center; color:#888; padding:40px;'>داده‌ای برای نمایش نمودار وجود ندارد.</p>")
            tabs.addTab(ch, '📊 نمودار')
            # --- تب ۳: خلاصه تحلیلی ---
            summary_html = getattr(self, '_summary_html', '') or ''
            if not summary_html and hasattr(self, 'summary_text'):
                try:
                    summary_html = self.summary_text.toHtml()
                except Exception:
                    summary_html = ''
            sm = QTextBrowser()
            sm.setOpenExternalLinks(False)
            sm.setHtml(summary_html or "<p>خلاصه‌ای موجود نیست.</p>")
            tabs.addTab(sm, '📝 خلاصه تحلیلی')
            lay.addWidget(tabs, 1)
            close_btn = QPushButton('بستن')
            close_btn.setObjectName('SecondaryButton')
            close_btn.clicked.connect(dlg.accept)
            hb = QHBoxLayout()
            hb.addStretch()
            hb.addWidget(close_btn)
            lay.addLayout(hb)
            self.analysis_dialog = dlg
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در باز کردن تحلیل:\n{}'.format(e))
