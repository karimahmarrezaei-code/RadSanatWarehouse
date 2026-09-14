# -*- coding: utf-8 -*-
"""اسکریپت پچ برای اضافه کردن کامبو باکس شماره حواله در گزارش"""

import re

file_path = 'app/ui/issue_report_window.py'

print("📖 در حال خواندن فایل...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# . اضافه کردن کامبو باکس در متد _build (بعد از person_combo)
print("✅ اضافه کردن کامبو باکس شماره حواله...")
content = re.sub(
    r"(        bar\.addWidget\(QLabel\('مشتری:'\)\)\n        self\.person_combo = QComboBox\(\)\n        self\.person_combo\.setMinimumWidth\(200\)\n        bar\.addWidget\(self\.person_combo\))",
    r"\1\n        # کامبو باکس شماره حواله\n        bar.addWidget(QLabel('شماره حواله:'))\n        self.issue_combo = QComboBox()\n        self.issue_combo.setMinimumWidth(250)\n        self.issue_combo.currentIndexChanged.connect(self._on_issue_combo_changed)\n        bar.addWidget(self.issue_combo)",
    content
)

# ۲. اضافه کردن _load_issues() در __init__ (بعد از _load_persons())
print("✅ اضافه کردن فراخوانی _load_issues در __init__...")
content = re.sub(
    r"(        self\._load_persons\(\)\n        self\.refresh\(\))",
    r"        self._load_persons()\n        self._load_issues()\n        self.refresh()",
    content
)

# ۳. اضافه کردن _load_issues() در refresh()
print("✅ اضافه کردن _load_issues در refresh...")
content = re.sub(
    r"(    def refresh\(self\):)",
    r"    def refresh(self):\n        # به‌روزرسانی لیست حواله‌ها\n        if hasattr(self, 'issue_combo'):\n            self._load_issues()",
    content
)

# ۴. اضافه کردن متدهای جدید قبل از _update_from_jalali
print("✅ اضافه کردن متدهای جدید...")
new_methods = """
    def _load_issues(self):
        \"\"\"لود لیست حواله‌ها برای کامبو باکس\"\"\"
        with self.db.connect() as conn:
            try:
                rows = conn.execute(
                    "SELECT wi.id, wi.issue_no, ol.reference_no, "
                    "       COALESCE(p.first_name||' '||p.last_name, '-') as cust, "
                    "       wi.issue_date "
                    "FROM warehouse_issues wi "
                    "LEFT JOIN outbound_loads ol ON ol.id = wi.outbound_load_id "
                    "LEFT JOIN persons p ON p.id = wi.customer_id "
                    "WHERE wi.issue_status != 'CANCELLED' "
                    "ORDER BY wi.id DESC"
                ).fetchall()
            except Exception:
                rows = []
        
        self.issue_combo.blockSignals(True)
        self.issue_combo.clear()
        self.issue_combo.addItem('همه حواله‌ها', None)
        for r in rows:
            issue_no = r['issue_no'] or '-'
            ref_no = r['reference_no'] or '-'
            cust = r['cust'] or '-'
            label = f"{issue_no} | {ref_no} | {cust}"
            self.issue_combo.addItem(label, r['id'])
        self.issue_combo.blockSignals(False)
    
    def _on_issue_combo_changed(self):
        \"\"\"وقتی کاربر حواله‌ای را از کامبو انتخاب می‌کند\"\"\"
        selected_issue_id = self.issue_combo.currentData()
        if selected_issue_id is not None:
            self._filter_by_issue_id(selected_issue_id)
        else:
            self.refresh()
    
    def _filter_by_issue_id(self, issue_id: int):
        \"\"\"فیلتر جدول برای نمایش یک حواله خاص\"\"\"
        with self.db.connect() as conn:
            try:
                rows = conn.execute(
                    "SELECT wi.*, ol.reference_no AS ref, ol.total_load_qty AS tlq, "
                    "       d.first_name||' '||d.last_name AS drv, "
                    "       COALESCE(p.first_name||' '||p.last_name,'-') AS cust, "
                    "       COALESCE(SUM(ii.qty),0) AS q, COALESCE(SUM(ii.qty*ii.unit_price),0) AS amt "
                    "FROM warehouse_issues wi "
                    "LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id "
                    "LEFT JOIN persons p ON p.id=wi.customer_id "
                    "LEFT JOIN persons d ON d.id=wi.driver_id "
                    "LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id "
                    "WHERE wi.id = ? "
                    "GROUP BY wi.id",
                    (issue_id,)
                ).fetchall()
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, 'خطا', str(e))
                rows = []
        
        self.tbl.setRowCount(len(rows))
        self._ids = []
        self._refs = []
        self._loads = []
        self._custs = []
        for i, r in enumerate(rows):
            self._ids.append(r['id'])
            self._refs.append(r['ref'] or '')
            self._loads.append(r['outbound_load_id'])
            self._custs.append(r['cust'] or '-')
            vals = [
                r['issue_no'] or '', r['ref'] or '', str(r['stage_no'] or 1),
                jalali_date_display_from_iso(r['issue_date']), r['cust'],
                r['drv'] or '-', r['waybill_no'] or '',
                f"{int(r['q'] or 0):,}", f"{int(r['tlq'] or 0):,}",
                f"{int(r['amt'] or 0):,}", STATUS_FA.get(r['issue_status'], r['issue_status'] or '')
            ]
            for cc, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(i, cc, it)
        
        if self.tbl.rowCount():
            self._on_select(0, 0, -1, -1)

"""

# پیدا کردن محل اضافه کردن متدها (قبل از _update_from_jalali)
content = re.sub(
    r"(    def _update_from_jalali\(self\):)",
    new_methods + r"\1",
    content
)

# ذخیره تغییرات
print("💾 در حال ذخیره تغییرات...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ تغییرات با موفقیت اعمال شد!")
print("🎉 حالا می‌توانید برنامه را اجرا کنید.")
print("\n📋 تغییرات اعمال شده:")
print("  1. ✅ اضافه شدن کامبو باکس 'شماره حواله' در نوار ابزار")
print("  2. ✅ متد _load_issues() برای لود لیست حواله‌ها")
print("  3. ✅ متد _on_issue_combo_changed() برای مدیریت تغییر")
print("  4. ✅ متد _filter_by_issue_id() برای فیلتر جدول")
print("\n نحوه استفاده:")
print("  - در فرم گزارش، از کامبو باکس 'شماره حواله' یک حواله انتخاب کنید")
print("  - جدول به صورت خودکار فیلتر می‌شود")
print("  - برای نمایش همه حواله‌ها، گزینه 'همه حواله‌ها' را انتخاب کنید")