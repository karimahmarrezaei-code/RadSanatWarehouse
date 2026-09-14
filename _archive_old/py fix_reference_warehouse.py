# -*- coding: utf-8 -*-
"""انبارمحوری مرجع‌های خروج حواله - اجرا: py fix_reference_warehouse.py"""
import os, re, sqlite3, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(ROOT, 'app', 'ui')
IM = os.path.join(UI, 'issue_manager_window.py')
IR = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')

# ---------------- 1) مهاجرت دیتابیس + backfill ----------------
dbs = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d.lower() not in ('.venv', 'venv', '__pycache__', '.git')]
    for fn in filenames:
        if fn.lower().endswith(('.db', '.sqlite', '.sqlite3')):
            dbs.append(os.path.join(dirpath, fn))
con = sqlite3.connect(sorted(dbs, key=os.path.getmtime)[-1])
try:
    con.execute('ALTER TABLE outbound_loads ADD COLUMN warehouse_id INTEGER')
    print('OK - ستون warehouse_id به outbound_loads اضافه شد')
except Exception:
    print('SKIP - ستون از قبل موجود بود')
# backfill A: از انبار اقلام حواله‌ها
con.execute("""
    UPDATE outbound_loads SET warehouse_id = (
        SELECT wii.warehouse_id FROM warehouse_issue_items wii
        JOIN warehouse_issues wi ON wi.id = wii.issue_id
        WHERE wi.outbound_load_id = outbound_loads.id AND wi.issue_status != 'CANCELLED'
        GROUP BY wii.warehouse_id ORDER BY SUM(wii.qty) DESC LIMIT 1)
    WHERE warehouse_id IS NULL AND EXISTS (
        SELECT 1 FROM warehouse_issues wi WHERE wi.outbound_load_id = outbound_loads.id AND wi.issue_status != 'CANCELLED')
""")
# backfill B: از پیش‌فاکتور CONVERTED هم‌امضا (مشتری + همان پالت/تعداد)
rows = con.execute("""
    SELECT ol.id, ol.customer_id FROM outbound_loads ol
    WHERE ol.warehouse_id IS NULL AND NOT EXISTS (
        SELECT 1 FROM warehouse_issues wi WHERE wi.outbound_load_id = ol.id AND wi.issue_status != 'CANCELLED')
""").fetchall()
cnt_b = 0
for ol_id, cust in rows:
    items = con.execute("SELECT pallet_id, SUM(qty) FROM outbound_load_items WHERE outbound_load_id=? GROUP BY pallet_id ORDER BY pallet_id", (ol_id,)).fetchall()
    if not items:
        continue
    sig = '|'.join('{}:{}'.format(a, int(b or 0)) for a, b in items)
    pros = con.execute("SELECT id, warehouse_id FROM proforma_invoices WHERE status='CONVERTED' AND COALESCE(customer_id,0)=COALESCE(?,0) ORDER BY id DESC", (cust,)).fetchall()
    for pid, pwh in pros:
        if not pwh:
            continue
        pitems = con.execute("SELECT pallet_id, SUM(quantity) FROM proforma_invoice_items WHERE proforma_id=? GROUP BY pallet_id ORDER BY pallet_id", (pid,)).fetchall()
        if '|'.join('{}:{}'.format(a, int(b or 0)) for a, b in pitems) == sig:
            con.execute("UPDATE outbound_loads SET warehouse_id=? WHERE id=?", (pwh, ol_id))
            cnt_b += 1
            break
con.commit(); con.close()
print('OK - backfill مرجع‌ها (B):', cnt_b)

# ---------------- 2) رپازیتوری: ثبت انبار روی مرجع جدید ----------------
src = open(IR, encoding='utf-8').read()
shutil.copy2(IR, IR + '.bak75')
OLD_INS = (
    '" load_status, waybill_no, source_location, destination_location, register_date) "\n'
    '                 "VALUES (?,?,?,?,?,?,?,?,?,?,?)",\n'
    '                 (ref_no, customer_id, driver_id, total_declared, 0, total_declared, \'OPEN\',\n'
    '                  waybill_no, source_location, destination_location, operation_date)\n'
)
NEW_INS = (
    '" load_status, waybill_no, source_location, destination_location, register_date, warehouse_id) "\n'
    '                 "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",\n'
    '                 (ref_no, customer_id, driver_id, total_declared, 0, total_declared, \'OPEN\',\n'
    '                  waybill_no, source_location, destination_location, operation_date,\n'
    '                  (lines[0].get(\'warehouse_id\') if lines else None))\n'
)
if OLD_INS in src:
    src = src.replace(OLD_INS, NEW_INS, 1)
    print('OK - INSERT مرجع جدید با warehouse_id')
else:
    print('SKIP - الگوی INSERT')
OLD_ELSE = "ref_no = conn.execute(\"SELECT reference_no FROM outbound_loads WHERE id = ?\", (outbound_load_id,)).fetchone()[0]"
if OLD_ELSE in src and 'COALESCE(warehouse_id, ?)' not in src:
    src = src.replace(OLD_ELSE, OLD_ELSE + "\n" + (
        "            try:\n"
        "                conn.execute(\"UPDATE outbound_loads SET warehouse_id = COALESCE(warehouse_id, ?) WHERE id = ?\",\n"
        "                             ((lines[0].get('warehouse_id') if lines else None), outbound_load_id))\n"
        "            except Exception:\n"
        "                pass"), 1)
    print('OK - تکمیل انبار مرجع موجود')
open(IR, 'w', encoding='utf-8').write(src)
py_compile.compile(IR, doraise=True); print('OK سینتکس: issue_repository')

# ---------------- 3) پنجره حواله: فیلتر کامبو مرجع ----------------
src2 = open(IM, encoding='utf-8').read()
shutil.copy2(IM, IM + '.bak75')

METHOD = (
    "    def _infer_reference_warehouse(self, reference_id):\n"
    "        \"\"\"حدس انبار مرجعِ بدون انبار: پیش‌فاکتور CONVERTED هم‌امضا\"\"\"\n"
    "        try:\n"
    "            with self.db.connect() as conn:\n"
    "                conn.row_factory = None\n"
    "                ol = conn.execute(\"SELECT customer_id FROM outbound_loads WHERE id=?\", (reference_id,)).fetchone()\n"
    "                if not ol:\n"
    "                    return None\n"
    "                items = conn.execute(\"SELECT pallet_id, SUM(qty) FROM outbound_load_items WHERE outbound_load_id=? GROUP BY pallet_id ORDER BY pallet_id\", (reference_id,)).fetchall()\n"
    "                if not items:\n"
    "                    return None\n"
    "                sig = '|'.join('{}:{}'.format(a, int(b or 0)) for a, b in items)\n"
    "                pros = conn.execute(\"SELECT id, warehouse_id FROM proforma_invoices WHERE status='CONVERTED' AND COALESCE(customer_id,0)=COALESCE(?,0) ORDER BY id DESC\", (ol[0],)).fetchall()\n"
    "                for pid, pwh in pros:\n"
    "                    if not pwh:\n"
    "                        continue\n"
    "                    pitems = conn.execute(\"SELECT pallet_id, SUM(quantity) FROM proforma_invoice_items WHERE proforma_id=? GROUP BY pallet_id ORDER BY pallet_id\", (pid,)).fetchall()\n"
    "                    if '|'.join('{}:{}'.format(a, int(b or 0)) for a, b in pitems) == sig:\n"
    "                        return int(pwh)\n"
    "                return None\n"
    "        except Exception:\n"
    "            return None\n"
    "\n"
)
if 'def _infer_reference_warehouse' not in src2:
    src2, n0 = re.subn(r"(?m)^(    def _refresh_reference_combo\(self\):)", lambda m: METHOD + m.group(0), src2, count=1)
    print('OK - متد حدس انبار مرجع' if n0 else 'SKIP - متد حدس')

# افزودن ol.warehouse_id به SELECT کامبو مرجع
src2, n1 = re.subn(
    r"(\(SELECT COUNT\(\*\) FROM warehouse_issues wi\s+WHERE wi\.outbound_load_id = ol\.id\s+AND wi\.issue_status != 'CANCELLED'\))\s*(FROM outbound_loads ol\s+WHERE ol\.is_active = 1\s+ORDER BY ol\.id DESC)",
    lambda m: m.group(1) + ",\n                 ol.warehouse_id\n                 " + m.group(2),
    src2, count=1)
print('OK - SELECT کامبو مرجع + warehouse_id' if n1 else 'SKIP - SELECT کامبو')

# منطق فیلتر جدید کامبو مرجع
OLD_SKIP1 = (
    "                rws = wh_map.get(ref_id) or set()\n"
    "                # فقط انبارهای مربوط: مرجع جدید (بدون حواله) یا انبارِ ردیف‌ها = انبار انتخابی\n"
    "                # (اگر انبار ردیف‌ها در داده‌های قدیمی خالی باشد، حذف نمی‌شود)\n"
    "                if rws and (None not in rws) and (wid not in rws):\n"
    "                    continue"
)
NEW_SKIP1 = (
    "                ol_wh = row[6]\n"
    "                rws = wh_map.get(ref_id) or set()\n"
    "                if ol_wh:\n"
    "                    if int(ol_wh) != int(wid):\n"
    "                        continue\n"
    "                else:\n"
    "                    inferred = self._infer_reference_warehouse(ref_id)\n"
    "                    if inferred:\n"
    "                        if int(inferred) != int(wid):\n"
    "                            continue\n"
    "                    elif rws and (None not in rws) and (wid not in rws):\n"
    "                        continue"
)
if OLD_SKIP1 in src2:
    src2 = src2.replace(OLD_SKIP1, NEW_SKIP1, 1)
    print('OK - فیلتر کامبو مرجع بر اساس انبار')
else:
    print('SKIP - فیلتر کامبو')

# افزودن ol.warehouse_id به SELECT حواله‌های مانده
src2, n2 = re.subn(
    r"(COALESCE\(ol\.register_date,''\))\s*(FROM outbound_loads ol)",
    lambda m: m.group(1) + ",\n                        ol.warehouse_id\n                 " + m.group(2),
    src2, count=1)
print('OK - SELECT حواله‌های مانده + warehouse_id' if n2 else 'SKIP - SELECT مانده')

OLD_SKIP2 = (
    "            rws = wh_map.get(r[0]) or set()\n"
    "            if rws and (None not in rws) and (wid not in rws):\n"
    "                continue"
)
NEW_SKIP2 = (
    "            ol_wh = r[7]\n"
    "            rws = wh_map.get(r[0]) or set()\n"
    "            if ol_wh:\n"
    "                if int(ol_wh) != int(wid):\n"
    "                    continue\n"
    "            else:\n"
    "                inferred = self._infer_reference_warehouse(r[0])\n"
    "                if inferred:\n"
    "                    if int(inferred) != int(wid):\n"
    "                        continue\n"
    "                elif rws and (None not in rws) and (wid not in rws):\n"
    "                    continue"
)
if OLD_SKIP2 in src2:
    src2 = src2.replace(OLD_SKIP2, NEW_SKIP2, 1)
    print('OK - فیلتر حواله‌های مانده بر اساس انبار')
else:
    print('SKIP - فیلتر مانده')

open(IM, 'w', encoding='utf-8').write(src2)
py_compile.compile(IM, doraise=True); print('OK سینتکس: issue_manager_window')
input('Enter...')