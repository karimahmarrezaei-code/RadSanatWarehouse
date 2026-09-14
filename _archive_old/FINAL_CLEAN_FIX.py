# -*- coding: utf-8 -*-
"""
FINAL CLEAN FIX - اصلاح نهایی فایل‌های اصلی
"""
import os
import re

print("=" * 70)
print("FINAL CLEAN FIX")
print("=" * 70)

# ============================================================
# اصلاح receipt_manager_window.py
# ============================================================
print("\n[1] اصلاح receipt_manager_window.py...")

path = 'app/ui/receipt_manager_window.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # پیدا کردن و اصلاح متد _load_pallet_prices
    new_lines = []
    in_method = False
    method_fixed = False
    
    for i, line in enumerate(lines):
        # پیدا کردن شروع متد
        if 'def *load*pallet_prices' in line or 'def _load_pallet_prices' in line:
            in_method = True
            # جایگزینی کل متد
            new_lines.append('    def _load_pallet_prices(self) -> None:\n')
            new_lines.append('        """⭐ بارگذاری قیمت میانگین پالت‌ها"""\n')
            new_lines.append('        self.avg_pallet_prices = {}\n')
            new_lines.append('        self.pallet_stock = {}\n')
            new_lines.append('        try:\n')
            new_lines.append('            with self.db.connect() as conn:\n')
            new_lines.append('                conn.row_factory = None\n')
            new_lines.append('\n')
            new_lines.append('                # قیمت میانگین از تراکنش‌های ورودی\n')
            new_lines.append('                rows = conn.execute(\n')
            new_lines.append('                    "SELECT pallet_id, "\n')
            new_lines.append('                    "       CASE WHEN SUM(qty_in) > 0 THEN "\n')
            new_lines.append('                    "           SUM(COALESCE(total_price, unit_price * qty_in)) / SUM(qty_in) "\n')
            new_lines.append('                    "       ELSE 0 END AS avg_price "\n')
            new_lines.append('                    "FROM inventory_transactions "\n')
            new_lines.append('                    "WHERE transaction_type = \'IN\' AND COALESCE(is_void, 0) = 0 "\n')
            new_lines.append('                    "GROUP BY pallet_id"\n')
            new_lines.append('                ).fetchall()\n')
            new_lines.append('\n')
            new_lines.append('                for r in rows:\n')
            new_lines.append('                    self.avg_pallet_prices[r[0]] = float(r[1] or 0)\n')
            new_lines.append('\n')
            new_lines.append('                # موجودی فعلی هر پالت\n')
            new_lines.append('                rows2 = conn.execute(\n')
            new_lines.append('                    "SELECT pallet_id, "\n')
            new_lines.append('                    "       SUM(CASE WHEN transaction_type=\'IN\' THEN qty_in ELSE qty_out END) AS stock "\n')
            new_lines.append('                    "FROM inventory_transactions "\n')
            new_lines.append('                    "WHERE COALESCE(is_void, 0) = 0 "\n')
            new_lines.append('                    "GROUP BY pallet_id"\n')
            new_lines.append('                ).fetchall()\n')
            new_lines.append('\n')
            new_lines.append('                for r in rows2:\n')
            new_lines.append('                    self.pallet_stock[r[0]] = max(int(r[1] or 0), 0)\n')
            new_lines.append('\n')
            new_lines.append('        except Exception as e:\n')
            new_lines.append('            print(f\'Load pallet prices error: {e}\')\n')
            new_lines.append('            import traceback\n')
            new_lines.append('            traceback.print_exc()\n')
            new_lines.append('\n')
            method_fixed = True
            print(f"  ✓ متد _load_pallet_prices اصلاح شد")
            continue
        
        # حذف خطوط قدیمی متد
        if in_method:
            if line.strip().startswith('def ') and '_load_pallet_prices' not in line:
                in_method = False
            else:
                continue
        
        new_lines.append(line)
    
    # ذخیره
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"  ✓ ذخیره: {path}")

# ============================================================
# اصلاح issue_repository.py
# ============================================================
print("\n[2] اصلاح issue_repository.py...")

path = 'app/repositories/issue_repository.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix corrupted links
    content = re.sub(r'\[([a-zA-Z_0-9\[\]]+)\]\(http://[a-zA-Z_0-9\[\]]+\)', r'\1', content)
    
    # Fix HTML entities
    content = content.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
    
    # Fix method names
    content = content.replace('**init**', '__init__')
    content = content.replace('*safe*', '_safe_')
    content = content.replace('*customer*', '_customer_')
    content = content.replace('*driver*', '_driver_')
    content = content.replace('*number*', '_number_')
    
    # Fix stage_load_qty -> total_load_qty for outbound_loads
    content = content.replace('stage_load_qty', 'total_load_qty')
    
    # Fix received_qty_total -> issued_qty_total
    content = content.replace('received_qty_total', 'issued_qty_total')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ ذخیره: {path}")

# ============================================================
# پاکسازی کش
# ============================================================
print("\n[3] پاکسازی کش...")
import shutil
for cache_dir in ['__pycache__', 'app/__pycache__', 'app/ui/__pycache__', 'app/repositories/__pycache__']:
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(f"  ✓ حذف: {cache_dir}")

print("\n" + "=" * 70)
print("✅ اصلاح کامل شد!")
print("=" * 70)
print("\nحالا اجرا کنید: python main.py")
