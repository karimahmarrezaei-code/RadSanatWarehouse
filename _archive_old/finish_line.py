# -*- coding: utf-8 -*-
"""تکمیل نهایی receipt و return - اجرا: python finish_line.py"""
import os, re, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(ROOT, 'app', 'repositories')

def save(p, s, bak):
    shutil.copy2(p, p + bak)
    open(p, 'w', encoding='utf-8').write(s)
    try:
        py_compile.compile(p, doraise=True)
        return True
    except Exception as e:
        shutil.copy2(p + bak, p)
        print('❌ کامپایل', os.path.basename(p), ':', str(e)[:120])
        return False

# ---------------- RECEIPT ----------------
p = os.path.join(R, 'receipt_repository.py')
s = open(p, encoding='utf-8').read()
ch = False
if 'check_conn' in s:
    i = s.find('# اعتبارسنجی تعداد رسید نسبت به مانده حواله')
    j = s.find('    with self.db.connect() as conn:', i if i != -1 else 0)
    if i != -1 and j != -1 and 'check_conn' in s[i:j]:
        s = s[:s.rfind('\n', 0, i) + 1] + s[j:]
        ch = True
        print('✔ بلوک اتصال جداگانه حذف شد')
m = re.search(r"([ \t]*)with self\.db\.connect\(\) as conn:\n[ \t]*conn\.row_factory = None\n[ \t]*# Create or reuse inbound_loads", s)
if m and 'remaining_row = conn.execute' not in s:
    d = m.group(1)
    VIN = (d + "with self.db.connect() as conn:\n" + d + "    conn.row_factory = None\n"
           + d + "    if inbound_load_id:\n" + d + "        try:\n"
           + d + "            remaining_row = conn.execute(\n"
           + d + "                \"SELECT remaining_qty FROM inbound_loads WHERE id = ?\",\n"
           + d + "                (inbound_load_id,)\n" + d + "            ).fetchone()\n"
           + d + "            if remaining_row and received_qty_total > int(remaining_row[0] or 0):\n"
           + d + "                raise ValidationError(\n"
           + d + "                    \"تعداد تحویل ({:,}) از مانده حواله ({:,}) بیشتر است!\".format(\n"
           + d + "                        received_qty_total, int(remaining_row[0] or 0)))\n"
           + d + "        except ValidationError:\n" + d + "            raise\n"
           + d + "        except Exception:\n" + d + "            pass\n"
           + d + "    # Create or reuse inbound_loads")
    s = s[:m.start()] + VIN + s[m.end():]
    ch = True
    print('✔ اعتبارسنجی داخل اتصال اصلی')
if 'vehicle_type_i' not in s:
    ai = s.find('# Insert warehouse_receipts')
    if ai != -1 and re.search(r"waybill_no,\s*supplier_id,\s*driver_id,\s*'',\s*'',", s):
        F = ("        vehicle_type_i, vehicle_plate_i = '', ''\n"
             "        if driver_id:\n"
             "            try:\n"
             "                vr = conn.execute(\n"
             "                    \"SELECT COALESCE(vehicle_type, ''), COALESCE(vehicle_plate, '') \"\n"
             "                    \"FROM driver_profiles WHERE person_id = ?\", (driver_id,)\n"
             "                ).fetchone()\n"
             "                if vr:\n"
             "                    vehicle_type_i, vehicle_plate_i = vr[0] or '', vr[1] or ''\n"
             "            except Exception:\n"
             "                pass\n")
        ls = s.rfind('\n', 0, ai) + 1
        s = s[:ls] + F + s[ls:]
        s = re.sub(r"waybill_no,\s*supplier_id,\s*driver_id,\s*'',\s*'',",
                   "waybill_no, supplier_id, driver_id, vehicle_type_i, vehicle_plate_i,", s, count=1)
        ch = True
        print('✔ پلاک در رسید ذخیره می‌شود')
if 'inbound_load_items (inbound_load_id, row_no' not in s:
    m3 = re.search(r"[ \t]*inbound_load_id = conn\.execute\(\"SELECT last_insert_rowid\(\)\"\)\.fetchone\(\)\[0\]", s)
    if m3:
        B = ("\n            for _i, _ln in enumerate(lines, start=1):\n"
             "                try:\n"
             "                    conn.execute(\n"
             "                        \"INSERT INTO inbound_load_items (inbound_load_id, row_no, pallet_id, qty) \"\n"
             "                        \"VALUES (?,?,?,?)\",\n"
             "                        (inbound_load_id, _i, _ln.get('pallet_id'), self._safe_int(_ln.get('quantity', 0))))\n"
             "                except Exception:\n"
             "                    pass")
        s = s[:m3.end()] + B + s[m3.end():]
        ch = True
        print('✔ اقلام مرجع ورود')
if ch:
    save(p, s, '.bakfin')

# ---------------- RETURN: خالص‌سازی ----------------
p = os.path.join(R, 'return_repository.py')
s = open(p, encoding='utf-8').read()
if '[ADD-NET]' not in s:
    m = re.search(r"\n([ \t]*)conn\.commit\(\)\n[ \t]*person = conn\.execute\(", s)
    if m:
        d = m.group(1)
        NET = ("\n" + d + "# ── [ADD-NET] خالص‌سازی سند اصلی در برگشت از فروش ──\n"
               + d + "if doc_type == 'ISSUE':\n" + d + "    try:\n"
               + d + "        total_return_qty = sum(int(it['qty'] or 0) for it in items)\n"
               + d + "        for item in items:\n"
               + d + "            conn.execute(\n"
               + d + "                \"UPDATE warehouse_issue_items SET qty = MAX(COALESCE(qty,0) - ?, 0) \"\n"
               + d + "                \"WHERE issue_id = ? AND pallet_id = ?\",\n"
               + d + "                (int(item['qty'] or 0), doc_id, item['pallet_id']))\n"
               + d + "        conn.execute(\n"
               + d + "            \"UPDATE warehouse_issues SET delivered_qty = MAX(COALESCE(delivered_qty,0) - ?, 0), \"\n"
               + d + "            \"stage_load_qty = MAX(COALESCE(stage_load_qty,0) - ?, 0) WHERE id = ?\",\n"
               + d + "            (total_return_qty, total_return_qty, doc_id))\n"
               + d + "        conn.execute(\n"
               + d + "            \"UPDATE financial_documents SET total_amount = MAX(COALESCE(total_amount,0) - ?, 0) \"\n"
               + d + "            \"WHERE issue_id = ? AND operation_type = 'OUTBOUND_ISSUE' AND status <> 'CANCELLED'\",\n"
               + d + "            (total_amount, doc_id))\n"
               + d + "        ol = conn.execute(\"SELECT outbound_load_id FROM warehouse_issues WHERE id = ?\", (doc_id,)).fetchone()\n"
               + d + "        if ol and ol[0]:\n"
               + d + "            row = conn.execute(\"SELECT total_load_qty FROM outbound_loads WHERE id = ?\", (ol[0],)).fetchone()\n"
               + d + "            if row:\n"
               + d + "                dsum = conn.execute(\n"
               + d + "                    \"SELECT COALESCE(SUM(delivered_qty),0) FROM warehouse_issues \"\n"
               + d + "                    \"WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'\", (ol[0],)).fetchone()[0]\n"
               + d + "                conn.execute(\n"
               + d + "                    \"UPDATE outbound_loads SET remaining_qty = MAX(? - ?, 0) WHERE id = ?\",\n"
               + d + "                    (int(row[0] or 0), int(dsum or 0), ol[0]))\n"
               + d + "    except Exception as e:\n"
               + d + "        print('[net] skipped:', str(e)[:120])")
        s = s[:m.start()] + NET + s[m.start():]
        if save(p, s, '.bakfin2'):
            print('✔ خالص‌سازی ۷۵/۹۰ نشست')
    else:
        print('⚠️ لنگر NET پیدا نشد؛ خطوط واقعی:')
        for i, ln in enumerate(s.split('\n')):
            if 'conn.commit()' in ln or 'person = conn.execute' in ln:
                print('{:5d}|{}'.format(i + 1, repr(ln)))
print('پایان ✔ — ری‌استارت و تست.')
input('Enter...')