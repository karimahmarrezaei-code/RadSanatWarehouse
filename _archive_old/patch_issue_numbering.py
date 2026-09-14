# -*- coding: utf-8 -*-
"""
اسکریپت تغییر سیستم شماره‌گذاری حواله‌ها
از: IS-1405-0034-1 (بر اساس customer_id و stage)
به: IS-1405-0001 (سریال سالانه مستقل)
"""

import re

file_path = 'app/repositories/issue_repository.py'

print("📖 در حال خواندن فایل issue_repository.py...")
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print(f" فایل {file_path} یافت نشد!")
    exit(1)

# 🔍 پیدا کردن بخش تولید شماره حواله
print("🔍 در حال جستجوی بخش تولید شماره حواله...")

# الگوی قدیمی (بر اساس ref_digits)
old_pattern = r"""(try:\s+from app\.core\.jalali import jalali_date_display_from_iso\s+import datetime as _dt\s+jy = jalali_date_display_from_iso\(_dt\.date\.today\(\)\.isoformat\(\)\)\[:4\]\s+ref_digits = ''\.join\(ch for ch in str\(ref_no or ''\)\.split\('-'\)\[-1\] if ch\.isdigit\(\)\) or '0'\s+issue_no = f"IS-\{jy\}-\{int\(ref_digits\):04d\}-\{int\(stage_no or 1\)\}"\s+except Exception:\s+issue_no = self\.build_document_no\(conn, ref_no, stage_no, personnel_id=customer_id\))"""

# کد جدید (سریال سالانه مستقل)
new_code = """# ✅ تولید شماره حواله سریال سالانه مستقل (نه بر اساس customer_id)
from app.core.jalali import jalali_date_display_from_iso
import datetime as _dt

jy = jalali_date_display_from_iso(_dt.date.today().isoformat())[:4]

try:
    conn.row_factory = None
    # دریافت آخرین شماره حواله در سال جاری
    last_issue = conn.execute(
        "SELECT issue_no FROM warehouse_issues "
        "WHERE issue_no LIKE ? AND issue_status != 'CANCELLED' "
        "ORDER BY id DESC LIMIT 1",
        (f'IS-{jy}-%',)
    ).fetchone()
    
    if last_issue and last_issue[0]:
        # استخراج شماره سریال از آخرین حواله
        last_serial = int(last_issue[0].split('-')[-1])
        new_serial = last_serial + 1
    else:
        new_serial = 1
    
    issue_no = f"IS-{jy}-{new_serial:04d}"
except Exception as e:
    print(f"️ خطا در تولید شماره حواله: {e}")
    issue_no = f"IS-{jy}-0001"
"""

# جایگزینی
if re.search(old_pattern, content, re.MULTILINE | re.DOTALL):
    print("✅ بخش قدیمی پیدا شد. در حال جایگزینی...")
    content = re.sub(old_pattern, new_code, content, flags=re.MULTILINE | re.DOTALL)
    
    # ذخیره تغییرات
    print("💾 در حال ذخیره تغییرات...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ تغییرات با موفقیت اعمال شد!")
    print("\n📋 تغییرات:")
    print("  قبل: IS-1405-0034-1 (بر اساس customer_id)")
    print("  بعد: IS-1405-0001 (سریال سالانه مستقل)")
    print("\n نحوه کار:")
    print("  - اولین حواله سال: IS-1405-0001")
    print("  - دومین حواله: IS-1405-0002")
    print("  - و الی آخر...")
    
else:
    print("⚠️ الگوی قدیمی پیدا نشد!")
    print("📝 ممکن است کد قبلاً تغییر کرده باشد یا ساختار متفاوتی دارد.")
    
    # جستجوی جایگزین
    if "ref_digits" in content:
        print("🔍 رشته 'ref_digits' در فایل یافت شد.")
        print("لطفاً به صورت دستی بخش زیر را پیدا و جایگزین کنید:")
        print("\n--- پیدا کنید: ---")
        print("ref_digits = ''.join(ch for ch in str(ref_no or '').split('-')[-1] if ch.isdigit()) or '0'")
        print("issue_no = f\"IS-{jy}-{int(ref_digits):04d}-{int(stage_no or 1)}\"")
        print("\n--- جایگزین کنید با: ---")
        print(new_code)

print("\n✅ پایان اسکریپت")