# -*- coding: utf-8 -*-
"""بررسی مطابقت مانده مرجع و حواله‌ها - نسخه امن بدون recursion"""
import os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))

dbs = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    # وارد این پوشه‌ها نشو (هم برای سرعت هم برای جلوگیری از حلقه بی‌پایان)
    dirnames[:] = [d for d in dirnames if d.lower() not in
                   ('.venv', 'venv', '__pycache__', '.git', 'node_modules', '.idea')]
    if dirpath.replace(ROOT, '').count(os.sep) > 4:
        dirnames[:] = []
        continue
    for fn in filenames:
        if fn.lower().endswith(('.db', '.sqlite', '.sqlite3')):
            dbs.append(os.path.join(dirpath, fn))

if not dbs:
    print('دیتابیس پیدا نشد؛ مسیر کامل فایل .db را وارد کنید:')
    path = input('> ').strip().strip('"')
else:
    path = sorted(dbs, key=os.path.getmtime)[-1]

print('DB:', path)
con = sqlite3.connect(path)

rows = con.execute("""
    SELECT ol.id, ol.reference_no, COALESCE(ol.total_load_qty,0),
           COALESCE((SELECT SUM(COALESCE(wi.delivered_qty,0))
                     FROM warehouse_issues wi
                     WHERE wi.outbound_load_id=ol.id AND wi.issue_status!='CANCELLED'),0),
           COALESCE(ol.remaining_qty,0)
    FROM outbound_loads ol WHERE ol.is_active=1 ORDER BY ol.id DESC""").fetchall()

for oid, ref, total, dsum, stored_rem in rows:
    rem = max(total - dsum, 0)
    print("\nمرجع {} | کل بار: {} | تحویل‌شده: {} | مانده محاسبه‌شده: {} | ذخیره‌شده در جدول: {}".format(
        ref, total, dsum, rem, stored_rem))
    for ino, st, dv in con.execute(
            "SELECT issue_no, COALESCE(stage_load_qty,0), COALESCE(delivered_qty,0) "
            "FROM warehouse_issues WHERE outbound_load_id=? AND issue_status!='CANCELLED' "
            "ORDER BY stage_no", (oid,)):
        print("   حواله {} | بار مرحله: {} | تحویل: {} | مانده حواله: {}".format(
            ino, st, dv, max(st - dv, 0)))

input('Enter...')