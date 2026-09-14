# auto_patch.py - مخصوص اصلاح پنجره حواله خروج
import os
import re

# نام فایل هدف که شما باز کرده‌اید
TARGET_FILE = "issue_manager_window.py"

def run_patch():
    if not os.path.exists(TARGET_FILE):
        print(f"❌ خطا: فایل '{TARGET_FILE}' یافت نشد.")
        print("   لطفاً مطمئن شوید این فایل را در پوشه app\\ui ذخیره کرده‌اید.")
        return

    print("🔧 در حال اصلاح فایل...")
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # ۱. تغییر سایز پنجره
    if re.search(r'self\.resize\(\d+,\s*\d+\)', content):
        content = re.sub(r'self\.resize\(\d+,\s*\d+\)', 'self.resize(1600, 950)', content, count=1)
        print("✅ سایز پنجره بزرگ‌تر شد.")
    else:
        print("⚠️ الگوی self.resize یافت نشد.")

    # ۲. رنگ‌بندی جدول (یک‌در‌میان خاکستری)
    # جستجوی تعریف جدول و اضافه کردن متد زیر آن
    table_match = re.search(r'(self\.tbl.*?=\s*QTableWidget.*?\))', content)
    if table_match:
        # اضافه کردن متد بعد از تعریف
        insert_pos = table_match.end()
        snippet = "\n        self.tbl.setAlternatingRowColors(True)\n"
        content = content[:insert_pos] + snippet + content[insert_pos:]
        print("✅ رنگ‌بندی جدول فعال شد.")
    else:
        print("⚠️ متغیر جدول (tbl) یافت نشد.")

    # ۳. پیام هشدار ورود
    if 'super().__init__' in content:
        # اضافه کردن پیام بعد از اینیت
        snippet = """
        #  پیام راهنمای ورود
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, lambda: QMessageBox.information(self, "راهنما", "برای مشاهده لیست، ابتدا انبار مقصد را انتخاب کنید."))
        """
        content = content.replace('super().__init__()', 'super().__init__()' + snippet, 1)
        print("✅ پیام راهنما اضافه شد.")

    # . افزودن تابع فیلتر حواله‌های مانده (در انتهای فایل)
    new_func = """

    def _filter_remaining_shipments(self):
        '''فیلتر کردن حواله‌هایی که بار مانده دارند'''
        # این تابع باید توسط دکمه جدید صدا زده شود
        # منطق نمونه:
        try:
            with self.db.connect() as conn:
                # کوئری فرضی - بسته به نام جدول‌های شما ممکن است نیاز به تنظیم داشته باشد
                rows = conn.execute("SELECT * FROM warehouse_issues WHERE status = 'OPEN'").fetchall()
                if hasattr(self, 'tbl'):
                    # فراخوانی متد پرکننده جدول شما
                    self._populate_table(rows) 
                QMessageBox.information(self, 'فیلتر', 'نمایش حواله‌های مانده')
        except Exception as e:
            QMessageBox.critical(self, 'خطا', str(e))
"""
    # پیدا کردن جای مناسب برای اضافه کردن تابع (قبل از آخرین خط خالی)
    if "def _populate_table" in content or "def refresh" in content:
        content = content.rstrip() + new_func
        print("✅ تابع حواله‌های مانده اضافه شد.")

    # ذخیره نهایی
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print("🎉 عملیات با موفقیت پایان یافت.")
    input(" Enter بزنید تا پنجره بسته شود...")

if __name__ == "__main__":
    run_patch()