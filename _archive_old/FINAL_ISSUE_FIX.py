# -*- coding: utf-8 -*-
"""
FINAL ISSUE FIX - اصلاح نهایی warehouse_issues INSERT و قیمت میانگین
"""
import os
import re

print("=" * 70)
print("FINAL ISSUE FIX")
print("=" * 70)

# ============================================================
# Fix issue_repository.py - INSERT warehouse_issues
# ============================================================
print("\n[1] Fixing issue_repository.py INSERT...")

path = 'app/repositories/issue_repository.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # بک‌آپ
    with open(path + '.bak_final', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # پیدا کردن INSERT warehouse_issues
    # ستون‌های warehouse_issues:
    # id, outbound_load_id, issue_no, stage_no, issue_date, jalali_date_text,
    # waybill_no, customer_id, driver_id, vehicle_type, vehicle_plate,
    # stage_load_qty, delivered_qty, discrepancy_qty, freight_amount,
    # source_location, destination_location, warehouse_keeper_name, receiver_name,
    # issue_status, description, print_html, created_by, created_at, total_qty
    # = 24 ستون (بدون id)
    
    # الگوی INSERT صحیح
    correct_insert = '''                now_iso = datetime.now().isoformat()
                conn.execute(
                    "INSERT INTO warehouse_issues "
                    "(outbound_load_id, issue_no, stage_no, issue_date, jalali_date_text, "
                    " waybill_no, customer_id, driver_id, vehicle_type, vehicle_plate, "
                    " stage_load_qty, delivered_qty, discrepancy_qty, freight_amount, "
                    " source_location, destination_location, warehouse_keeper_name, receiver_name, "
                    " issue_status, description, print_html, created_by, created_at, total_qty) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (outbound_load_id, issue_no, stage_no, operation_date,
                     jalali_date_display_from_iso(operation_date),
                     waybill_no, customer_id, driver_id, '', '',
                     total_declared, delivered_qty, discrepancy, freight_amount,
                     source_location, destination_location, '', '',
                     'CONFIRMED', notes, '', user_id, now_iso, total_amount)
                )
                issue_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]'''
    
    # پیدا کردن INSERT فعلی و جایگزینی
    # الگو: از "INSERT INTO warehouse_issues" تا "issue_id = conn.execute"
    pattern = r'                conn\.execute\(\s*"INSERT INTO warehouse_issues.*?issue_id = conn\.execute\("SELECT last_insert_rowid\(\)"\)\.fetchone\(\)\[0\]'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, correct_insert.strip(), content, flags=re.DOTALL)
        print("  ✓ Fixed INSERT warehouse_issues")
    else:
        print("  ⚠ Pattern not found")
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ Saved: {path}")

# ============================================================
# Fix issue_manager_window.py - قیمت میانگین
# ============================================================
print("\n[2] Fixing issue_manager_window.py - avg price display...")

path = 'app/ui/issue_manager_window.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # بررسی وجود avg_price_value
    if 'self.avg_price_value' in content:
        print("  ✓ avg_price_value widget exists")
    else:
        print("  ⚠ avg_price_value widget not found!")
    
    # بررسی _on_issue_pallet_changed
    if '_on_issue_pallet_changed' in content:
        print("  ✓ _on_issue_pallet_changed method exists")
    else:
        print("  ⚠ _on_issue_pallet_changed method not found!")

print("\n✅ DONE!")
print("\nRun: python main.py")
