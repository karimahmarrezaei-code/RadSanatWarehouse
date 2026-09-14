"""
گزارش اقلام راکد (Dead Stock Report)
نمایش پالت‌هایی که در بازه مشخصی هیچ حرکتی نداشته‌اند
"""

import webbrowser
import tempfile
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QGroupBox, QDateEdit, QPushButton,
    QComboBox, QHeaderView, QMessageBox, QFrame, QTextBrowser,
    QTabWidget, QWidget, QAbstractItemView, QFileDialog,
    QSpinBox
)
from PyQt5.QtGui import QColor

from app.core.jalali import jalali_date_display_from_iso


# ===================================================================
# کارت آماری
# ===================================================================
class DeadStockCard(QFrame):
    def __init__(self, title: str, value: str, color: str = "#dc2626") -> None:
        super().__init__()
        self.setObjectName('DeadStockCard')
        self.setStyleSheet('')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        title_lbl.setAlignment(Qt.AlignCenter)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        value_lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        self.value_lbl = value_lbl


# ===================================================================
# فرم اصلی گزارش اقلام راکد
# ===================================================================
class DeadStockWindow(QDialog):
    def __init__(self, db, user_data) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.setWindowTitle('گزارش اقلام راکد (Dead Stock)')
        self.resize(1400, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self._run_report()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # ============================================================
        # بخش فیلتر
        # ============================================================
        filter_group = QGroupBox("فیلتر گزارش اقلام راکد")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("انبار:"))
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.setMinimumWidth(200)
        self._load_warehouses()
        filter_layout.addWidget(self.warehouse_combo)

        filter_layout.addWidget(QLabel("آستانه راکد (روز):"))
        self.dead_threshold = QSpinBox()
        self.dead_threshold.setMinimum(30)
        self.dead_threshold.setMaximum(365)
        self.dead_threshold.setValue(90)
        self.dead_threshold.setSuffix(" روز")
        filter_layout.addWidget(self.dead_threshold)

        filter_layout.addWidget(QLabel("تا تاریخ:"))
        self.cut_date = QDateEdit(QDate.currentDate())
        self.cut_date.setCalendarPopup(True)
        self.cut_date.setDisplayFormat('yyyy-MM-dd')
        filter_layout.addWidget(self.cut_date)

        # دکمه‌ها
        apply_btn = QPushButton("محاسبه اقلام راکد")
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
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        self.card_dead_count = DeadStockCard("تعداد اقلام راکد", "0", "#dc2626")
        self.card_dead_value = DeadStockCard("ارزش ریالی راکد", "0 ریال", "#ea580c")
        self.card_dead_qty = DeadStockCard("تعداد کل راکد", "0 عدد", "#9333ea")
        self.card_dead_pct = DeadStockCard("درصد از کل موجودی", "0%", "#6b7280")
        stats_layout.addWidget(self.card_dead_count)
        stats_layout.addWidget(self.card_dead_value)
        stats_layout.addWidget(self.card_dead_qty)
        stats_layout.addWidget(self.card_dead_pct)
        root.addLayout(stats_layout)

        # ============================================================
        # تب‌ها
        # ============================================================
        self.tabs = QTabWidget()

        # --- تب ۱: جدول اقلام راکد ---
        items_tab = QWidget()
        items_layout = QVBoxLayout(items_tab)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(9)
        self.items_table.setHorizontalHeaderLabels([
            "ردیف", "کد پالت", "نام پالت", "انبار", "موجودی فعلی",
            "آخرین حرکت", "روزهای راکد", "ارزش ریالی", "وضعیت"
        ])
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.verticalHeader().setVisible(False)
        items_layout.addWidget(self.items_table)

        self.items_info_lbl = QLabel("لیست اقلام راکد")
        self.items_info_lbl.setStyleSheet("color: #555; font-size: 12px; padding: 5px;")
        items_layout.addWidget(self.items_info_lbl)

        self.tabs.addTab(items_tab, "📦 اقلام راکد")

        # --- تب ۲: نمودار ---
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)

        self.chart_view = QTextBrowser()
        self.chart_view.setOpenExternalLinks(False)
        self.chart_view.setMinimumHeight(300)
        chart_layout.addWidget(self.chart_view)

        self.tabs.addTab(chart_tab, " نمودار توزیع")

        # --- تب ۳: توصیه‌ها ---
        recommendations_tab = QWidget()
        recommendations_layout = QVBoxLayout(recommendations_tab)

        self.recommendations_text = QTextBrowser()
        self.recommendations_text.setOpenExternalLinks(False)
        self.recommendations_text.setMinimumHeight(300)
        recommendations_layout.addWidget(self.recommendations_text)

        self.tabs.addTab(recommendations_tab, "💡 توصیه‌های مدیریتی")

        root.addWidget(self.tabs, stretch=1)

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

        export_btn = QPushButton(" خروجی HTML")
        export_btn.setObjectName('SecondaryButton')
        export_btn.clicked.connect(self._export_html)
        bottom_row.addWidget(export_btn)

        close_btn = QPushButton("بستن")
        close_btn.setObjectName('SecondaryButton')
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        root.addLayout(bottom_row)

    def _load_warehouses(self):
        self.warehouse_combo.clear()
        self.warehouse_combo.addItem("همه انبارها", None)
        try:
            with self.db.connect() as conn:
                rows = conn.execute("SELECT id, name FROM warehouses ORDER BY name").fetchall()
                for r in rows:
                    self.warehouse_combo.addItem(r['name'], r['id'])
        except Exception:
            pass

    def _clear_filters(self):
        self.warehouse_combo.setCurrentIndex(0)
        self.dead_threshold.setValue(90)
        self.cut_date.setDate(QDate.currentDate())
        self._run_report()

    def _run_report(self):
        """اجرای گزارش اقلام راکد"""
        warehouse_id = self.warehouse_combo.currentData()
        threshold_days = self.dead_threshold.value()
        cut_date = self.cut_date.date()
        cut_date_iso = cut_date.toString('yyyy-MM-dd')

        try:
            cut_dt = datetime.strptime(cut_date_iso, '%Y-%m-%d')
        except Exception:
            QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است.")
            return

        with self.db.connect() as conn:
            # کوئری: پیدا کردن پالت‌هایی که موجودی دارند اما حرکت اخیر نداشته‌اند
            query = '''
                SELECT 
                    il.pallet_id,
                    il.warehouse_id,
                    il.quantity as current_stock,
                    p.code as pallet_code,
                    p.name as pallet_name,
                    w.name as warehouse_name,
                    (SELECT MAX(transaction_date) 
                     FROM inventory_transactions 
                     WHERE pallet_id = il.pallet_id 
                       AND warehouse_id = il.warehouse_id) as last_movement
                FROM inventory_levels il
                JOIN pallets p ON p.id = il.pallet_id
                JOIN warehouses w ON w.id = il.warehouse_id
                WHERE il.quantity > 0
            '''
            params = []

            if warehouse_id:
                query += " AND il.warehouse_id = ?"
                params.append(warehouse_id)

            query += " ORDER BY il.pallet_id"

            rows = conn.execute(query, params).fetchall()

        # محاسبه روزهای راکد و فیلتر
        dead_items = []
        total_stock_value = 0
        total_dead_value = 0
        total_stock_qty = 0
        total_dead_qty = 0

        for r in rows:
            last_movement_iso = r['last_movement']
            
            if last_movement_iso:
                try:
                    last_dt = datetime.strptime(last_movement_iso, '%Y-%m-%d')
                    days_dead = (cut_dt - last_dt).days
                except:
                    days_dead = 999
            else:
                days_dead = 999  # اگر هیچ حرکتی نبوده

            current_stock = int(r['current_stock'] or 0)
            
            # محاسبه ارزش (نیاز به خواندن قیمت از آخرین تراکنش)
            unit_price = 0
            with self.db.connect() as conn2:
                price_row = conn2.execute('''
                    SELECT unit_price FROM inventory_transactions 
                    WHERE pallet_id = ? AND warehouse_id = ?
                    ORDER BY transaction_date DESC, id DESC LIMIT 1
                ''', (r['pallet_id'], r['warehouse_id'])).fetchone()
                if price_row:
                    unit_price = int(price_row['unit_price'] or 0)

            stock_value = current_stock * unit_price
            total_stock_value += stock_value
            total_stock_qty += current_stock

            if days_dead >= threshold_days:
                total_dead_value += stock_value
                total_dead_qty += current_stock
                dead_items.append({
                    'pallet_code': r['pallet_code'],
                    'pallet_name': r['pallet_name'],
                    'warehouse_name': r['warehouse_name'],
                    'current_stock': current_stock,
                    'last_movement': last_movement_iso,
                    'days_dead': days_dead,
                    'stock_value': stock_value,
                    'unit_price': unit_price,
                })

        # به‌روزرسانی کارت‌ها
        self.card_dead_count.value_lbl.setText(str(len(dead_items)))
        self.card_dead_value.value_lbl.setText(f"{total_dead_value:,} ریال")
        self.card_dead_qty.value_lbl.setText(f"{total_dead_qty:,} عدد")
        
        dead_pct = (total_dead_value / total_stock_value * 100) if total_stock_value > 0 else 0
        self.card_dead_pct.value_lbl.setText(f"{dead_pct:.1f}%")

        # پر کردن جدول
        self.items_table.setRowCount(len(dead_items))
        for i, item in enumerate(dead_items):
            self.items_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.items_table.setItem(i, 1, QTableWidgetItem(item['pallet_code'] or '-'))
            self.items_table.setItem(i, 2, QTableWidgetItem(item['pallet_name'] or '-'))
            self.items_table.setItem(i, 3, QTableWidgetItem(item['warehouse_name']))
            self.items_table.setItem(i, 4, QTableWidgetItem(f"{item['current_stock']:,}"))
            
            last_mov_display = jalali_date_display_from_iso(item['last_movement']) if item['last_movement'] else 'بدون حرکت'
            self.items_table.setItem(i, 5, QTableWidgetItem(last_mov_display))
            
            days_item = QTableWidgetItem(str(item['days_dead']))
            days_item.setTextAlignment(Qt.AlignCenter)
            # رنگ‌بندی بر اساس شدت راکد بودن
            if item['days_dead'] > 180:
                days_item.setBackground(QColor("#dc2626"))
                days_item.setForeground(QColor("white"))
            elif item['days_dead'] > 120:
                days_item.setBackground(QColor("#ea580c"))
                days_item.setForeground(QColor("white"))
            elif item['days_dead'] > 90:
                days_item.setBackground(QColor("#eab308"))
            self.items_table.setItem(i, 6, days_item)
            
            self.items_table.setItem(i, 7, QTableWidgetItem(f"{item['stock_value']:,}"))
            
            # وضعیت
            if item['days_dead'] > 180:
                status = "بحرانی ⚠️"
            elif item['days_dead'] > 120:
                status = "جدی"
            else:
                status = "راکد"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(i, 8, status_item)

        self.items_info_lbl.setText(
            f"تعداد اقلام راکد: {len(dead_items)} | ارزش راکد: {total_dead_value:,} ریال | "
            f"آستانه: {threshold_days} روز"
        )

        # نمودار و توصیه‌ها
        self._build_chart(dead_items)
        self._build_recommendations(dead_items, total_dead_value, total_stock_value, threshold_days)

        self.status_lbl.setText(
            f"تعداد اقلام راکد: {len(dead_items)} | ارزش راکد: {total_dead_value:,} ریال | "
            f"درصد از کل: {dead_pct:.1f}%"
        )

    def _build_chart(self, dead_items):
        """نمودار توزیع اقلام راکد بر اساس انبار"""
        if not dead_items:
            self.chart_view.setHtml(
                "<p style='text-align:center; color:#888; padding:40px;'>"
                "هیچ قلم راکدی یافت نشد.</p>"
            )
            return

        # گروه‌بندی بر اساس انبار
        by_warehouse = defaultdict(lambda: {'count': 0, 'value': 0})
        for item in dead_items:
            wh = item['warehouse_name']
            by_warehouse[wh]['count'] += 1
            by_warehouse[wh]['value'] += item['stock_value']

        warehouses = list(by_warehouse.keys())
        counts = [by_warehouse[w]['count'] for w in warehouses]
        max_count = max(counts) if counts else 1

        # SVG bar chart
        bar_w = 60
        gap = 20
        chart_h = 300
        chart_w = max(700, len(warehouses) * (bar_w + gap))

        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart_w}" '
            f'height="{chart_h + 80}" style="font-family:Tahoma; direction:rtl;">',
            f'<rect width="100%" height="100%" fill="#f8fafc" rx="10"/>',
            f'<text x="{chart_w/2}" y="30" text-anchor="middle" '
            f'font-size="16" font-weight="bold" fill="#46505f">'
            f'توزیع اقلام راکد بر اساس انبار</text>',
        ]

        for idx, (wh, count) in enumerate(zip(warehouses, counts)):
            x = 40 + idx * (bar_w + gap)
            bar_h = int((count / max_count) * (chart_h - 80))
            y = chart_h - bar_h

            svg.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
                      f'fill="#dc2626" rx="4"/>')
            svg.append(f'<text x="{x + bar_w/2}" y="{chart_h + 20}" '
                      f'text-anchor="middle" font-size="10" fill="#6b7686">{wh}</text>')
            svg.append(f'<text x="{x + bar_w/2}" y="{y - 5}" '
                      f'text-anchor="middle" font-size="11" font-weight="bold" fill="#46505f">'
                      f'{count}</text>')

        svg.append('</svg>')
        self.chart_view.setHtml(
            f"<div style='text-align:center; padding:10px;'>{''.join(svg)}</div>"
        )

    def _build_recommendations(self, dead_items, total_dead_value, total_stock_value, threshold):
        """تولید توصیه‌های مدیریتی"""
        if not dead_items:
            self.recommendations_text.setHtml(
                "<p style='text-align:center; color:#16a34a; padding:40px; font-size:16px;'>"
                "✅ هیچ قلم راکدی یافت نشد! انبار شما بهینه است.</p>"
            )
            return

        dead_pct = (total_dead_value / total_stock_value * 100) if total_stock_value > 0 else 0

        # دسته‌بندی بر اساس شدت
        critical = [i for i in dead_items if i['days_dead'] > 180]
        serious = [i for i in dead_items if 120 < i['days_dead'] <= 180]
        moderate = [i for i in dead_items if threshold <= i['days_dead'] <= 120]

        html = f"""
<html dir='rtl' lang='fa'><head><meta charset='utf-8'>
<style>
    body {{ font-family: Tahoma; padding: 20px; background: #f8fafc; }}
    .alert-box {{ 
        background: #fee2e2; border: 2px solid #dc2626; padding: 15px; 
        border-radius: 8px; margin: 10px 0;
    }}
    .warning-box {{ 
        background: #fef3c7; border: 2px solid #eab308; padding: 15px; 
        border-radius: 8px; margin: 10px 0;
    }}
    .info-box {{ 
        background: #dbeafe; border: 2px solid #2563eb; padding: 15px; 
        border-radius: 8px; margin: 10px 0;
    }}
    h3 {{ color: #46505f; margin-top: 0; }}
    ul {{ margin: 10px 0; padding-right: 20px; }}
    li {{ margin: 5px 0; }}
    .metric {{ 
        display: inline-block; padding: 8px 12px; margin: 5px;
        background: white; border-radius: 5px; border: 1px solid #e2e8f0;
    }}
    .metric b {{ color: #dc2626; }}
</style></head><body>
"""

        if dead_pct > 30:
            html += f"""
<div class="alert-box">
    <h3> وضعیت بحرانی</h3>
    <p>{dead_pct:.1f}% از ارزش موجودی شما راکد است. این یعنی سرمایه قابل توجهی خوابیده است.</p>
</div>
"""
        elif dead_pct > 15:
            html += f"""
<div class="warning-box">
    <h3>️ نیاز به توجه</h3>
    <p>{dead_pct:.1f}% از ارزش موجودی راکد است. بررسی و اقدام توصیه می‌شود.</p>
</div>
"""
        else:
            html += f"""
<div class="info-box">
    <h3>ℹ️ وضعیت قابل قبول</h3>
    <p>{dead_pct:.1f}% از ارزش موجودی راکد است. در محدوده نرمال قرار دارید.</p>
</div>
"""

        html += f"""
<div class="info-box">
    <h3>📊 خلاصه وضعیت</h3>
    <div class="metric"><b>تعداد اقلام راکد:</b> {len(dead_items)} قلم</div>
    <div class="metric"><b>ارزش راکد:</b> {total_dead_value:,} ریال</div>
    <div class="metric"><b>بحرانی (>180 روز):</b> {len(critical)} قلم</div>
    <div class="metric"><b>جدی (120-180 روز):</b> {len(serious)} قلم</div>
</div>

<h3>💡 توصیه‌های مدیریتی</h3>
<ul>
"""

        if critical:
            html += f"<li><b>برای {len(critical)} قلم بحرانی (>180 روز):</b> فروش فوری با تخفیف ویژه یا انتقال به انبار حراج</li>"
        if serious:
            html += f"<li><b>برای {len(serious)} قلم جدی (120-180 روز):</b> بررسی علت راکد بودن و برنامه‌ریزی برای فروش</li>"
        if moderate:
            html += f"<li><b>برای {len(moderate)} قلم راکد ({threshold}-120 روز):</b> نظارت بیشتر و کاهش سفارش‌های جدید</li>"

        html += """
    <li><b>پیشنهاد کلی:</b> بررسی سیاست خرید و فروش برای جلوگیری از انباشت موجودی</li>
    <li><b>اقدام فوری:</b> مذاکره با مشتریان برای فروش اقلام راکد با شرایط ویژه</li>
    <li><b>بلندمدت:</b> استقرار سیستم پیش‌بینی تقاضا برای کاهش راکدگی</li>
</ul>

</body></html>"""

        self.recommendations_text.setHtml(html)

    def _build_html_content(self) -> str:
        """ساخت HTML برای چاپ/خروجی"""
        rows_count = self.items_table.rowCount()
        if rows_count == 0:
            return ""

        threshold = self.dead_threshold.value()
        cut_date = self.cut_date.date().toString('yyyy-MM-dd')

        html = f'''<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="utf-8">
    <title>گزارش اقلام راکد</title>
    <style>
        @media print {{
            body {{ margin: 0; padding: 10px; }}
            .no-print {{ display: none; }}
        }}
        body {{ font-family: Tahoma, Arial, sans-serif; padding: 20px; }}
        h2 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #999; padding: 8px; text-align: center; font-size: 11px; }}
        th {{ background: #dc2626; color: white; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .critical {{ background: #fee2e2; }}
        .serious {{ background: #fef3c7; }}
    </style>
</head>
<body>
    <button class="no-print" onclick="window.print()"
        style="padding:10px 20px; background:#dc2626; color:white; border:none;
        border-radius:5px; cursor:pointer;">🖨️ چاپ</button>
    <h2>گزارش اقلام راکد (Dead Stock)</h2>
    <p style="text-align:center;">آستانه: {threshold} روز | تاریخ برش: {cut_date}</p>

    <table>
        <tr>
            <th>ردیف</th><th>کد پالت</th><th>نام پالت</th><th>انبار</th>
            <th>موجودی</th><th>آخرین حرکت</th><th>روز راکد</th>
            <th>ارزش (ریال)</th><th>وضعیت</th>
        </tr>
'''

        for i in range(rows_count):
            row_data = []
            for j in range(9):
                item = self.items_table.item(i, j)
                row_data.append(item.text() if item else '')
            
            days = int(row_data[6]) if row_data[6].isdigit() else 0
            row_class = 'critical' if days > 180 else ('serious' if days > 120 else '')
            
            html += f'<tr class="{row_class}">'
            for cell in row_data:
                html += f'<td>{cell}</td>'
            html += '</tr>'

        html += '''
    </table>
    <p style="text-align:center; color:#666; margin-top:20px;">
        گزارش تولید شده توسط سیستم انبار پالت
    </p>
</body>
</html>'''
        return html

    def _print_report(self):
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "چاپ", "داده‌ای برای چاپ وجود ندارد.")
            return
        try:
            html = self._build_html_content()
            if not html:
                return
            tmp = tempfile.NamedTemporaryFile(
                mode='w', suffix='.html', prefix='dead_stock_',
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
        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "خروجی", "داده‌ای برای خروجی وجود ندارد.")
            return
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, 'ذخیره گزارش اقلام راکد',
                'dead_stock_report.html', 'HTML Files (*.html)'
            )
            if not path:
                return
            html = self._build_html_content()
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "خروجی", f"ذخیره شد:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))
