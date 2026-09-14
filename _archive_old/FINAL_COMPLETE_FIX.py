# -*- coding: utf-8 -*-
"""
FINAL COMPLETE FIX - اصلاح نهایی تمام مشکلات
این فایل رو یکبار اجرا کنید و دیگه نیازی به اسکریپت نیست
"""
import os
import re
import sqlite3
import shutil
import glob

print("=" * 70)
print("FINAL COMPLETE FIX - اصلاح نهایی")
print("=" * 70)

# ============================================================
# مرحله 1: بک‌آپ
# ============================================================
print("\n[1] Creating backup...")
db_path = 'data/app.db'
if os.path.exists(db_path):
    shutil.copy2(db_path, db_path + '.backup_final')
    print(f"  ✓ Backup: {db_path}.backup_final")

# ============================================================
# مرحله 2: اصلاح فایل‌ها
# ============================================================
print("\n[2] Fixing files...")

files_to_fix = [
    ('app/repositories/receipt_repository.py', 'receipt'),
    ('app/repositories/issue_repository.py', 'issue'),
    ('app/ui/receipt_manager_window.py', 'receipt_window'),
    ('app/ui/issue_manager_window.py', 'issue_window'),
    ('app/ui/proforma_window.py', 'proforma'),
]

for file_path, file_type in files_to_fix:
    if not os.path.exists(file_path):
        print(f"  ⚠ {file_path} not found")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix corrupted links
    content = re.sub(r'\[([a-zA-Z_0-9\[\]]+)\]\(http://[a-zA-Z_0-9\[\]]+\)', r'\1', content)
    
    # Fix HTML entities
    content = content.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
    
    # Fix method names
    content = content.replace('**init**', '__init__')
    content = content.replace('*build*', '_build_')
    content = content.replace('*load*', '_load_')
    content = content.replace('*refresh*', '_refresh_')
    content = content.replace('*reference*', '_reference_')
    content = content.replace('*current*', '_current_')
    content = content.replace('*driver*', '_driver_')
    content = content.replace('*on*', '_on_')
    content = content.replace('*filter*', '_filter_')
    content = content.replace('*collect*', '_collect_')
    content = content.replace('*select*', '_select_')
    content = content.replace('*fmt*', '_fmt_')
    content = content.replace('*int*', '_int_')
    content = content.replace('*handle*', '_handle_')
    content = content.replace('*format*', '_format_')
    content = content.replace('*edit*', '_edit_')
    content = content.replace('*apply*', '_apply_')
    content = content.replace('*save*', '_save_')
    content = content.replace('*preview*', '_preview_')
    content = content.replace('*clear*', '_clear_')
    content = content.replace('*show*', '_show_')
    content = content.replace('*print*', '_print_')
    content = content.replace('*safe*', '_safe_')
    content = content.replace('*customer*', '_customer_')
    content = content.replace('*number*', '_number_')
    content = content.replace('*delete*', '_delete_')
    content = content.replace('*convert*', '_convert_')
    content = content.replace('*view*', '_view_')
    
    # Fix specific column names based on file type
    if file_type == 'issue':
        content = content.replace('wi.total_load_qty', 'wi.stage_load_qty')
        content = content.replace('received_qty_total', 'issued_qty_total')
    
    if file_type == 'issue_window':
        content = content.replace('total_load_qty', 'stage_load_qty')
    
    if file_type == 'receipt' or file_type == 'receipt_window':
        content = content.replace('SUM(COALESCE(total_amount', 'SUM(COALESCE(total_price')
        content = content.replace('COALESCE(total_amount, unit_price', 'COALESCE(total_price, unit_price')
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Fixed: {file_path}")
    else:
        print(f"  ✓ No changes: {file_path}")

# ============================================================
# مرحله 3: پاکسازی کش
# ============================================================
print("\n[3] Clearing cache...")
for cache_dir in glob.glob('**/__pycache__', recursive=True):
    try:
        shutil.rmtree(cache_dir)
    except:
        pass
print("  ✓ Cache cleared")

# ============================================================
# مرحله 4: پاکسازی سندها (اختیاری)
# ============================================================
print("\n[4] Cleaning documents (optional)...")
print("  ⚠ If you want to clean all documents, run: python RESET_ALL.py")

print("\n" + "=" * 70)
print("✅ ALL FIXES APPLIED!")
print("=" * 70)
print("\nNow run: python main.py")
print("\nنکته مهم:")
print("  - این اسکریپت رو فقط یکبار اجرا کنید")
print("  - بعد از اون نیازی به اسکریپت اضافی نیست")
print("  - اگه مشکلی پیش اومد، از بک‌آپ برگردانید")
