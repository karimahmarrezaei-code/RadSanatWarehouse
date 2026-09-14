# -*- coding: utf-8 -*-
"""
READ LINE 195 - نمایش خط مشکل‌دار
"""
import os

path = 'app/repositories/issue_repository.py'
if not os.path.exists(path):
    print(f"ERROR: {path} not found!")
    exit(1)

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# نمایش خطوط 190-200
print("\nLines 190-200:")
for i in range(189, min(200, len(lines))):
    print(f"  {i+1}: {repr(lines[i])}")

# پیدا کردن و اصلاح خط مشکل‌دار
print("\n[Fixing...]")

for i, line in enumerate(lines):
    if 'discrepancy' in line and 'max(' in line:
        # اگر e یا هر کاراکتر غیر عددی داره
        import re
        match = re.search(r'max\(stage_declared - delivered_qty,\s*(\w+)\)', line)
        if match:
            val = match.group(1)
            if val != '0':
                lines[i] = line.replace(val, '0')
                print(f"  ✓ Fixed line {i+1}: {val} -> 0")

# ذخیره
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n✅ Saved: {path}")
print("\nRun: python main.py")
