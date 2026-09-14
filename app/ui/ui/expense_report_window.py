"""
گزارش هزینه‌های عملیاتی - نسخه بهبود یافته
با نمودارهای واقعی matplotlib
"""

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import webbrowser
import tempfile
from typing import Dict, List
from collections import defaultdict

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QDateEdit, QPushButton,
    QComboBox, QHeaderView, QMessageBox, QFrame, QProgressBar,
    QTabWidget, QWidget, QAbstractItemView, QFileDialog,
    QSplitter
)
from app.core.jalali import jalali_date_display_from_iso


# ===================================================================
# کارت آماری
# ===================================================================
class ExpenseCard(QFrame):
    def __init__(self, title: str, value: str = "0 ریال",
                 color: str = "#2563eb") -> None:
        super().__init__()
        self.setObjectName('Card')
        self.setStyleSheet(
            f"QFrame#Card {{ border: 2px solid {color}; "
            f"border-radius: 8px; padding: 10px; }}"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; color: #64748b;")
        title_lbl.setAlignment(Qt.AlignCenter)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {color};"
        )
        self.value_lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_lbl)
        layout.addWidget(self.value_lbl)


# ===================================================================
# جدول دسته‌بندی با نوار پیشرفت
# ===================================================================
class CategoryTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["دسته‌بندی", "مبلغ", "درصد", "نمودار"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        self.layout.addWidget(self.table)
    
    def update_data(self, category_totals, total_amount):
        if not category_totals or total_amount == 0:
            self.table.setRowCount(0)
            return
        
        sorted_cats = sorted(category_totals.items(),
                           key=lambda x: x[1]['amount'], reverse=True)
        
        self.table.setRowCount(len(sorted_cats))
        for idx, (cat_name, data) in enumerate(sorted_cats):
            amount = data['amount']
            color = data.get('color', '#2563eb')
            percentage = (amount / total_amount) * 100
            
            # نام دسته
            name_item = QTableWidgetItem(cat_name)
            name_item.setForeground(QColor(color))
            self.table.setItem(idx, 0, name_item)
            
            # مبلغ
            amount_item = QTableWidgetItem(f"{amount:,} ریال")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 1, amount_item)
            
            # درصد
            pct_item = QTableWidgetItem(f"{percentage:.1f}%")
            pct_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 2, pct_item)
            
            # نوار پیشرفت
            progress = QProgressBar()
            progress.setValue(int(percentage))
            progress.setTextVisible(False)
            progress.setStyleSheet('')
            self.table.setCellWidget(idx, 3, progress)


# ===================================================================
# فرم اصلی گزارش
# ===================================================================
class ExpenseReportWindow(QDialog):
    def __init__(self, db, user_data) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.setWindowTitle('گزارش هزینه‌های عملیاتی')
        self.resize(1600, 1000)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._run_report()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # ============================================================
        # فیلتر
        # ============================================================
        filter_group = QGroupBox("فیلتر گزارش هزینه‌ها")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("از تاریخ:"))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("تا تاریخ:"))
        self.date_to = QDateEdit(QDate.currentDate().addDays(365))
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.date_to)

        filter_layout.addWidget(QLabel("دسته‌بندی:"))
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(200)
        self._load_categories()
        filter_layout.addWidget(self.category_combo)

        filter_layout.addWidget(QLabel("وضعیت:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("همه وضعیت‌ها", "ALL")
        self.status_combo.addItem("باز (OPEN)", "OPEN")
        self.status_combo.addItem("ناقص (PARTIAL)", "PARTIAL")
        self.status_combo.addItem("تسویه (SETTLED)", "SETTLED")
        filter_layout.addWidget(self.status_combo)

        apply_btn = QPushButton("اعمال فیلتر")
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
        # کارت‌های آماری
        # ============================================================
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        self.card_total = ExpenseCard("جمع کل هزینه‌ها", "0 ریال", "#2563eb")
        self.card_paid = ExpenseCard("پرداخت‌شده", "0 ریال", "#16a34a")
        self.card_open = ExpenseCard("مانده باز", "0 ریال", "#f59e0b")  # نارنجی به جای قرمز
        self.card_count = ExpenseCard("تعداد هزینه‌ها", "0", "#0891b2")
        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_paid)
        cards_layout.addWidget(self.card_open)
        cards_layout.addWidget(self.card_count)
        root.addLayout(cards_layout)

        # ============================================================
        # تب‌ها
        # ============================================================
        self.tabs = QTabWidget()
        
        self.tabs

        # --- تب ۱: جدول هزینه‌ها ---
        expenses_tab = QWidget()
        expenses_layout = QVBoxLayout(expenses_tab)

        self.expenses_table = QTableWidget()
        self.expenses_table.setColumnCount(10)
        self.expenses_table.setHorizontalHeaderLabels([
            "ردیف", "شناسه", "شماره هزینه", "تاریخ", "دسته‌بندی", "مبلغ کل",
            "پرداخت‌شده", "مانده باز", "وضعیت", "توضیحات"
        ])
        self.expenses_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.expenses_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.expenses_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.expenses_table.verticalHeader().setVisible(False)
        self.expenses_table.setColumnHidden(1, True)
        expenses_layout.addWidget(self.expenses_table)

        self.tabs.addTab(expenses_tab, "جدول هزینه‌ها")

        # --- تب ۲: نمودار دسته‌بندی (Donut + جدول) ---
        category_chart_tab = QWidget()
        category_chart_layout = QVBoxLayout(category_chart_tab)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # نمودار دایره‌ای
        self.fig_category = Figure(figsize=(8, 6), facecolor='#46505f')
        self.canvas_category = FigureCanvas(self.fig_category)
        splitter.addWidget(self.canvas_category)
        
        # جدول دسته‌بندی
        self.category_table = CategoryTableWidget()
        splitter.addWidget(self.category_table)
        
        splitter.setSizes([500, 400])
        category_chart_layout.addWidget(splitter)
        
        self.tabs.addTab(category_chart_tab, "نمودار دسته‌بندی")

        # --- تب ۳: نمودار روند زمانی ---
        timeline_chart_tab = QWidget()
        timeline_chart_layout = QVBoxLayout(timeline_chart_tab)

        self.fig_timeline = Figure(figsize=(12, 6), facecolor='#46505f')
        self.canvas_timeline = FigureCanvas(self.fig_timeline)
        timeline_chart_layout.addWidget(self.canvas_timeline)

        self.tabs.addTab(timeline_chart_tab, "روند زمانی")

        # --- تب : خلاصه تحلیلی ---
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)

        self.summary_text = QLabel()
        self.summary_text.setWordWrap(True)
        self.summary_text
        summary_layout.addWidget(self.summary_text)

        self.tabs.addTab(summary_tab, "خلاصه تحلیلی")

        root.addWidget(self.tabs, stretch=1)

        # ============================================================
        # دکمه‌های پایین
        # ============================================================
        bottom_row = QHBoxLayout()
        self.status_lbl = QLabel("آماده")
        self.status_lbl.setStyleSheet("color: #64748b;")
        bottom_row.addWidget(self.status_lbl)
        bottom_row.addStretch()

        settle_btn = QPushButton("تسویه هزینه")
        settle_btn.setObjectName('PrimaryButton')
        settle_btn.setMinimumHeight(40)
        settle_btn.clicked.connect(self._settle_expense)
        bottom_row.addWidget(settle_btn)

        export_btn = QPushButton("خروجی HTML")
        export_btn.setObjectName('SecondaryButton')
        export_btn.clicked.connect(self._export_html)
        bottom_row.addWidget(export_btn)

        close_btn = QPushButton("بستن")
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        root.addLayout(bottom_row)

    def _load_categories(self):
        """بارگذاری دسته‌بندی‌ها"""
        self.category_combo.clear()
        self.category_combo.addItem("همه دسته‌بندی‌ها", None)
        try:
            with self.db.connect() as conn:
                rows = conn.execute('''
                    SELECT id, name FROM expense_categories
                    WHERE is_active = 1 ORDER BY name
                ''').fetchall()
                for r in rows:
                    self.category_combo.addItem(r['name'], r['id'])
        except:
            pass

    def _clear_filters(self):
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate().addDays(365))
        self.category_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self._run_report()

    def _run_report(self):
        """اجرای گزارش"""
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        category_id = self.category_combo.currentData()
        status = self.status_combo.currentData()

        if date_from > date_to:
            QMessageBox.warning(self, "خطا", "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.")
            return

        with self.db.connect() as conn:
            query = '''
                SELECT 
                    e.id, e.expense_no, e.expense_date, e.amount, e.paid_amount,
                    e.status, e.description,
                    c.name as category_name, c.color as category_color
                FROM expenses e
                JOIN expense_categories c ON c.id = e.category_id
                WHERE e.expense_date BETWEEN ? AND ?
            '''
            params = [date_from, date_to]

            if category_id:
                query += " AND e.category_id = ?"
                params.append(category_id)

            if status and status != 'ALL':
                query += " AND e.status = ?"
                params.append(status)

            query += " ORDER BY e.expense_date DESC, e.id DESC"

            rows = conn.execute(query, params).fetchall()

        # محاسبات
        total_amount = 0
        total_paid = 0
        total_open = 0
        category_totals = defaultdict(lambda: {'amount': 0, 'color': '#2563eb'})
        daily_totals = defaultdict(float)

        for r in rows:
            amount = int(r['amount'] or 0)
            paid = int(r['paid_amount'] or 0)
            open_amount = amount - paid

            total_amount += amount
            total_paid += paid
            total_open += open_amount

            category_name = r['category_name']
            category_totals[category_name]['amount'] += amount
            category_totals[category_name]['color'] = r['category_color'] or '#2563eb'

            daily_totals[r['expense_date']] += amount

        # به‌روزرسانی کارت‌ها
        self.card_total.value_lbl.setText(f"{total_amount:,} ریال")
        self.card_paid.value_lbl.setText(f"{total_paid:,} ریال")
        self.card_open.value_lbl.setText(f"{total_open:,} ریال")
        self.card_count.value_lbl.setText(str(len(rows)))

        # جدول
        self.expenses_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.expenses_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.expenses_table.setItem(i, 1, QTableWidgetItem(str(r['id'])))
            self.expenses_table.setItem(i, 2, QTableWidgetItem(r['expense_no'] or '-'))
            self.expenses_table.setItem(i, 3, QTableWidgetItem(
                jalali_date_display_from_iso(r['expense_date']) if r['expense_date'] else '-'
            ))
            self.expenses_table.setItem(i, 4, QTableWidgetItem(r['category_name']))

            amount_item = QTableWidgetItem(f"{int(r['amount']):,}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.expenses_table.setItem(i, 5, amount_item)

            paid_item = QTableWidgetItem(f"{int(r['paid_amount'] or 0):,}")
            paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.expenses_table.setItem(i, 6, paid_item)

            open_item = QTableWidgetItem(f"{int(r['amount'] or 0) - int(r['paid_amount'] or 0):,}")
            open_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.expenses_table.setItem(i, 7, open_item)

            status_labels = {'OPEN': 'باز', 'PARTIAL': 'ناقص', 'SETTLED': 'تسویه'}
            self.expenses_table.setItem(i, 8, QTableWidgetItem(
                status_labels.get(r['status'], r['status'])
            ))

            desc = r['description'] or '-'
            if len(desc) > 50:
                desc = desc[:50] + '...'
            self.expenses_table.setItem(i, 9, QTableWidgetItem(desc))

        # نمودارها
        self._build_category_chart(category_totals, total_amount)
        self._build_timeline_chart(daily_totals)
        self._build_summary(total_amount, total_paid, total_open, len(rows),
                          category_totals, daily_totals)

        self.status_lbl.setText(
            f"جمع کل: {total_amount:,} ریال | پرداخت‌شده: {total_paid:,} ریال | "
            f"مانده باز: {total_open:,} ریال"
        )

    def _build_category_chart(self, category_totals, total_amount):
        """نمودار دایره‌ای توخالی (Donut) توزیع هزینه"""
        self.fig_category.clear()
        
        if not category_totals or total_amount == 0:
            ax = self.fig_category.add_subplot(111)
            ax.text(0.5, 0.5, 'داده‌ای برای نمایش وجود ندارد',
                   ha='center', va='center', color='#64748b', fontsize=14)
            ax.set_facecolor('#46505f')
            self.canvas_category.draw()
            self.category_table.update_data({}, 0)
            return

        # مرتب‌سازی
        sorted_cats = sorted(category_totals.items(),
                           key=lambda x: x[1]['amount'], reverse=True)
        
        categories = [c[0] for c in sorted_cats]
        amounts = [c[1]['amount'] for c in sorted_cats]
        colors = [c[1]['color'] for c in sorted_cats]
        
        # رسم نمودار
        ax = self.fig_category.add_subplot(111)
        wedges, texts, autotexts = ax.pie(amounts, labels=None, colors=colors,
                              autopct='%1.1f%%', startangle=90,
                              pctdistance=0.85, wedgeprops=dict(width=0.4))
        
        # استایل متن درصد
        for autotext in autotexts:
            autotext.set_color('#e2e8f0')
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        # دایره توخالی
        centre_circle = Circle((0, 0), 0.70, fc='#46505f')
        ax.add_artist(centre_circle)
        
        # عنوان مرکزی
        ax.text(0, 0, f'{total_amount:,}\nریال', ha='center', va='center',
               fontsize=16, fontweight='bold', color='#e2e8f0')
        
        ax.set_facecolor('#46505f')
        self.fig_category.patch.set_facecolor('#46505f')
        
        # راهنما
        ax.legend(wedges, categories, title="دسته‌بندی‌ها",
                 loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                 fontsize=10, title_fontsize=12,
                 facecolor='#5b6675', edgecolor='#6b7686',
                 labelcolor='#e2e8f0')
        
        ax.tick_params(colors='#e2e8f0')
        
        self.fig_category.tight_layout()
        self.canvas_category.draw()
        
        # بروزرسانی جدول
        self.category_table.update_data(category_totals, total_amount)

    def _build_timeline_chart(self, daily_totals):
        """نمودار میله‌ای روند زمانی"""
        self.fig_timeline.clear()
        
        if not daily_totals:
            ax = self.fig_timeline.add_subplot(111)
            ax.text(0.5, 0.5, 'داده‌ای برای نمایش وجود ندارد',
                   ha='center', va='center', color='#64748b', fontsize=14)
            ax.set_facecolor('#46505f')
            self.canvas_timeline.draw()
            return

        sorted_dates = sorted(daily_totals.keys())
        jalali_dates = [jalali_date_display_from_iso(d) for d in sorted_dates]
        amounts = [daily_totals[d] for d in sorted_dates]

        ax = self.fig_timeline.add_subplot(111)
        bars = ax.bar(range(len(jalali_dates)), amounts, color='#ef4444', edgecolor='#dc2626')
        
        ax.set_xticks(range(len(jalali_dates)))
        ax.set_xticklabels(jalali_dates, rotation=45, ha='right', color='#e2e8f0')
        ax.set_ylabel('مبلغ (ریال)', color='#e2e8f0', fontsize=12)
        ax.set_title('روند هزینه بر اساس تاریخ', color='#e2e8f0', fontsize=14, fontweight='bold')
        
        ax.set_facecolor('#46505f')
        self.fig_timeline.patch.set_facecolor('#46505f')
        
        ax.tick_params(colors='#e2e8f0')
        ax.spines['bottom'].set_color('#6b7686')
        ax.spines['left'].set_color('#6b7686')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # نمایش مقدار روی هر میله
        for bar, amount in zip(bars, amounts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{amount:,}', ha='center', va='bottom',
                   color='#e2e8f0', fontsize=8)
        
        self.fig_timeline.tight_layout()
        self.canvas_timeline.draw()

    def _build_summary(self, total_amount, total_paid, total_open,
                      count, category_totals, daily_totals):
        """خلاصه تحلیلی"""
        paid_pct = (total_paid / total_amount * 100) if total_amount > 0 else 0
        open_pct = (total_open / total_amount * 100) if total_amount > 0 else 0
        avg_expense = total_amount / count if count > 0 else 0

        # بیشترین دسته
        if category_totals:
            top_cat = max(category_totals.items(), key=lambda x: x[1]['amount'])
            top_cat_name = top_cat[0]
            top_cat_amount = top_cat[1]['amount']
            top_cat_pct = (top_cat_amount / total_amount * 100) if total_amount > 0 else 0
        else:
            top_cat_name = '-'
            top_cat_amount = 0
            top_cat_pct = 0

        html = f"""
<html dir='rtl' lang='fa'><head><meta charset='utf-8'>
<style>
    body {{ font-family: Tahoma; padding: 20px; background: #46505f; color: #e2e8f0; }}
    .section {{ background: #5b6675; padding: 15px; margin: 10px 0;
                border-radius: 8px; border-right: 4px solid #2563eb; }}
    h3 {{ color: #1d4ed8; margin-top: 0; }}
    .metric {{ display: inline-block; padding: 10px 15px; margin: 5px;
               background: #6b7686; border-radius: 5px; }}
    .metric b {{ color: #1d4ed8; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #6b7686; }}
    .label {{ color: #64748b; }}
    .value {{ text-align: left; font-weight: bold; color: #e2e8f0; }}
</style></head><body>

<div class='section'>
    <h3>📊 شاخص‌های کلیدی</h3>
    <div class='metric'><b>جمع کل هزینه‌ها:</b> {total_amount:,} ریال</div>
    <div class='metric'><b>تعداد هزینه‌ها:</b> {count} مورد</div>
    <div class='metric'><b>میانگین هر هزینه:</b> {avg_expense:,.0f} ریال</div>
    <div class='metric'><b>پرداخت‌شده:</b> {total_paid:,} ریال ({paid_pct:.1f}%)</div>
    <div class='metric'><b>مانده باز:</b> {total_open:,} ریال ({open_pct:.1f}%)</div>
</div>

<div class='section'>
    <h3>🏆 بیشترین هزینه بر اساس دسته‌بندی</h3>
    <table>
        <tr><td class='label'>دسته‌بندی:</td><td class='value'>{top_cat_name}</td></tr>
        <tr><td class='label'>مبلغ:</td><td class='value'>{top_cat_amount:,} ریال</td></tr>
        <tr><td class='label'>درصد از کل:</td><td class='value'>{top_cat_pct:.1f}%</td></tr>
    </table>
</div>

<div class='section'>
    <h3>💡 توصیه‌های مدیریتی</h3>
    <ul>
"""

        if open_pct > 50:
            html += "<li><b>⚠️ هشدار:</b> بیش از 50% هزینه‌ها پرداخت نشده است. پیگیری تسویه ضروری است.</li>"
        elif open_pct > 20:
            html += "<li><b>⚠️ توجه:</b> درصد قابل توجهی از هزینه‌ها باز است. برنامه‌ریزی برای پرداخت توصیه می‌شود.</li>"
        else:
            html += "<li><b>✅ عالی:</b> اکثر هزینه‌ها تسویه شده‌اند.</li>"

        if top_cat_pct > 40:
            html += f"<li><b>🎯 تمرکز هزینه:</b> {top_cat_pct:.1f}% هزینه‌ها در دسته «{top_cat_name}» متمرکز است.</li>"

        html += """
    </ul>
</div>

</body></html>"""
        self.summary_text.setText(html)

    def _settle_expense(self):
        """تسویه هزینه انتخاب‌شده"""
        row = self.expenses_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تسویه", "لطفاً یک هزینه از جدول انتخاب کنید.")
            return
        
        # دریافت اطلاعات هزینه
        expense_id = int(self.expenses_table.item(row, 1).text())
        amount = int(self.expenses_table.item(row, 5).text().replace(',', ''))
        paid = int(self.expenses_table.item(row, 6).text().replace(',', ''))
        remaining = amount - paid
        
        if remaining <= 0:
            QMessageBox.information(self, "تسویه", "این هزینه قبلاً تسویه شده است.")
            return
        
        # باز کردن فرم تسویه
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                     QLineEdit, QComboBox, QPushButton, QDateEdit,
                                     QGroupBox, QMessageBox as QMsgBox)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("تسویه هزینه")
        dialog.resize(500, 400)
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # اطلاعات هزینه
        info_group = QGroupBox("اطلاعات هزینه")
        info_layout = QVBoxLayout(info_group)
        
        info_layout.addWidget(QLabel(f"شناسه: {expense_id}"))
        info_layout.addWidget(QLabel(f"مبلغ کل: {amount:,} ریال"))
        info_layout.addWidget(QLabel(f"پرداخت‌شده: {paid:,} ریال"))
        
        remaining_lbl = QLabel(f"مانده باز: {remaining:,} ریال")
        remaining_lbl.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 14px;")
        info_layout.addWidget(remaining_lbl)
        
        layout.addWidget(info_group)
        
        # فرم تسویه
        form_group = QGroupBox("جزئیات پرداخت")
        form_layout = QVBoxLayout(form_group)
        
        # مبلغ پرداختی
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("مبلغ پرداختی (ریال):"))
        payment_amount = QLineEdit()
        payment_amount.setText(str(remaining))
        amount_layout.addWidget(payment_amount)
        form_layout.addLayout(amount_layout)
        
        # حساب پرداخت
        account_layout = QHBoxLayout()
        account_layout.addWidget(QLabel("حساب پرداخت:"))
        account_combo = QComboBox()
        account_combo.setMinimumWidth(200)
        
        # بارگذاری حساب‌ها
        try:
            with self.db.connect() as conn:
                accounts = conn.execute("""
                    SELECT id, name, account_type, current_balance 
                    FROM treasury_accounts 
                    WHERE is_active = 1 
                    ORDER BY name
                """).fetchall()
                for acc in accounts:
                    acc_type = "صندوق" if acc['account_type'] == 'CASHBOX' else "بانک"
                    display = f"{acc['name']} ({acc_type}) - موجودی: {acc['current_balance']:,} ریال"
                    account_combo.addItem(display, acc['id'])
        except Exception as e:
            QMsgBox.critical(self, "خطا", f"خطا در بارگذاری حساب‌ها: {e}")
            return
        
        account_layout.addWidget(account_combo)
        form_layout.addLayout(account_layout)
        
        # تاریخ
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("تاریخ:"))
        payment_date = QDateEdit(QDate.currentDate())
        payment_date.setCalendarPopup(True)
        payment_date.setDisplayFormat('yyyy-MM-dd')
        date_layout.addWidget(payment_date)
        form_layout.addLayout(date_layout)
        
        layout.addWidget(form_group)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        def do_settle():
            pay_amount = int(payment_amount.text().replace(',', ''))
            account_id = account_combo.currentData()
            date = payment_date.date().toString('yyyy-MM-dd')
            
            if pay_amount <= 0:
                QMsgBox.warning(dialog, "خطا", "مبلغ پرداختی باید بیشتر از صفر باشد.")
                return
            
            if pay_amount > remaining:
                QMsgBox.warning(dialog, "خطا", "مبلغ پرداختی نمی‌تواند بیشتر از مانده باز باشد.")
                return
            
            try:
                with self.db.connect() as conn:
                    # آپدیت paid_amount و status
                    new_paid = paid + pay_amount
                    if new_paid >= amount:
                        new_status = 'SETTLED'
                    elif new_paid > 0:
                        new_status = 'PARTIAL'
                    else:
                        new_status = 'OPEN'
                    conn.execute("""
                        UPDATE expenses 
                        SET paid_amount = ?, status = ?
                        WHERE id = ?
                    """, (new_paid, new_status, expense_id))
                    
                    # ثبت در cash_transactions
                    conn.execute("""
                        UPDATE treasury_accounts
                        SET current_balance = current_balance - ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (pay_amount, account_id))
                    _bal = conn.execute("SELECT current_balance FROM treasury_accounts WHERE id = ?", (account_id,)).fetchone()
                    _new_bal = int(_bal["current_balance"] or 0) if _bal else 0
                    from datetime import datetime as _dt
                    conn.execute("""
                        INSERT INTO treasury_transactions (
                            treasury_account_id, transaction_date, transaction_type,
                            source_type, source_id, amount, balance_after, description, created_at
                        ) VALUES (?, ?, 'OUT', 'EXPENSE', ?, ?, ?, ?, ?)
                    """, (account_id, date, expense_id, pay_amount, _new_bal,
                          f"پرداخت هزینه {expense_id}", _dt.now().strftime("%Y-%m-%d %H:%M:%S")))
                    
                    
                    conn.commit()
                
                QMsgBox.information(dialog, "موفق", 
                    f"پرداخت {pay_amount:,} ریال با موفقیت ثبت شد.\n"
                    f"مانده باز جدید: {remaining - pay_amount:,} ریال")
                
                dialog.accept()
                self._run_report()  # بروزرسانی گزارش
                
            except Exception as e:
                QMsgBox.critical(dialog, "خطا", f"خطا در ثبت پرداخت: {e}")
        
        def cancel():
            dialog.reject()
        
        settle_btn = QPushButton("ثبت پرداخت")
        settle_btn.setObjectName('PrimaryButton')
        settle_btn.clicked.connect(do_settle)
        btn_layout.addWidget(settle_btn)
        
        cancel_btn = QPushButton("انصراف")
        cancel_btn.setObjectName('SecondaryButton')
        cancel_btn.clicked.connect(cancel)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec_()

    def _export_html(self):
        if self.expenses_table.rowCount() == 0:
            QMessageBox.warning(self, "خروجی", "داده‌ای برای خروجی وجود ندارد.")
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, 'ذخیره گزارش هزینه',
                'expense_report.html', 'HTML Files (*.html)'
            )
            if not path:
                return
            
            # ساخت HTML ساده
            rows_count = self.expenses_table.rowCount()
            date_from = self.date_from.date().toString('yyyy-MM-dd')
            date_to = self.date_to.date().toString('yyyy-MM-dd')
            
            html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="utf-8">
    <title>گزارش هزینه‌های عملیاتی</title>
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; padding: 20px; }}
        h2 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #999; padding: 8px; text-align: center; }}
        th {{ background: #5b6675; color: white; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
    </style>
</head>
<body>
    <h2>گزارش هزینه‌های عملیاتی</h2>
    <p style="text-align:center;">بازه: {date_from} تا {date_to}</p>
    <table>
        <tr>
            <th>ردیف</th><th>شماره هزینه</th><th>تاریخ</th><th>دسته‌بندی</th><th>مبلغ کل</th>
            <th>پرداخت‌شده</th><th>مانده باز</th><th>وضعیت</th><th>توضیحات</th>
        </tr>
'''
            for i in range(rows_count):
                row_data = []
                for j in [0, 2, 3, 4, 5, 6, 7, 8, 9]:
                    item = self.expenses_table.item(i, j)
                    row_data.append(item.text() if item else '')
                html += f'''<tr>
                    <td>{row_data[0]}</td><td>{row_data[1]}</td><td>{row_data[2]}</td>
                    <td>{row_data[3]}</td><td>{row_data[4]}</td><td>{row_data[5]}</td>
                    <td>{row_data[6]}</td><td>{row_data[7]}</td><td>{row_data[8]}</td>
                </tr>'''
            
            html += '''
    </table>
    <p style="text-align:center; color:#666; margin-top:20px;">
        گزارش تولید شده توسط سیستم انبار پالت
    </p>
</body>
</html>'''
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "خروجی", f"ذخیره شد:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
