# -*- coding: utf-8 -*-
"""بازنگری کلی: اعمال افزونه‌های تجاری روی پایه سالم - اجرا: python apply_final_additions.py"""
import os, shutil, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(ROOT, 'app', 'repositories')

def patch(fn, steps):
    p = os.path.join(R, fn)
    s = open(p, encoding='utf-8').read()
    shutil.copy2(p, p + '.bakfinal')
    log = []
    for name, old, new in steps:
        if old in s and name not in s:
            s = s.replace(old, new, 1); log.append(name)
    open(p, 'w', encoding='utf-8').write(s)
    try:
        py_compile.compile(p, doraise=True)
        print('✔', fn, '←', log or 'بدون تغییر')
    except Exception as e:
        shutil.copy2(p + '.bakfinal', p)
        print('❌', fn, 'برگشت؛ خطا:', str(e)[:120])

# ---------- ISSUE: قفل خروج بیش از مانده + اقلام مرجع ----------
B1 = ("\n            if outbound_load_id:\n"
      "                _rem = conn.execute(\"SELECT remaining_qty FROM outbound_loads WHERE id = ?\",\n"
      "                                    (outbound_load_id,)).fetchone()\n"
      "                if _rem and int(_rem[0] or 0) < issued_qty_total:\n"
      "                    raise ValueError(\n"
      "                        \"تعداد اقلام این حواله ({:,}) از ماندهٔ مرجع ({:,}) بیشتر است! \"\n"
      "                        \"ابتدا مقدار حواله را اصلاح کنید یا مرجع دیگری انتخاب کنید.\".format(\n"
      "                            issued_qty_total, int(_rem[0] or 0)))\n")
B2 = ("\n            for _i, _ln in enumerate(lines, start=1):\n"
      "                try:\n"
      "                    conn.execute(\n"
      "                        \"INSERT INTO outbound_load_items (outbound_load_id, row_no, pallet_id, qty) \"\n"
      "                        \"VALUES (?,?,?,?)\",\n"
      "                        (outbound_load_id, _i, _ln.get('pallet_id'), self._safe_int(_ln.get('quantity', 0))))\n"
      "                except Exception:\n"
      "                    pass\n")
B3 = ("\n            for _ln in lines:\n"
      "                _pid = _ln.get('pallet_id')\n"
      "                _has = conn.execute(\n"
      "                    \"SELECT 1 FROM outbound_load_items WHERE outbound_load_id = ? AND pallet_id = ?\",\n"
      "                    (outbound_load_id, _pid)).fetchone()\n"
      "                if not _has:\n"
      "                    _mx = conn.execute(\n"
      "                        \"SELECT COALESCE(MAX(row_no),0) FROM outbound_load_items WHERE outbound_load_id = ?\",\n"
      "                        (outbound_load_id,)).fetchone()[0]\n"
      "                    conn.execute(\n"
      "                        \"INSERT INTO outbound_load_items (outbound_load_id, row_no, pallet_id, qty) \"\n"
      "                        \"VALUES (?,?,?,?)\",\n"
      "                        (outbound_load_id, int(_mx or 0) + 1, _pid, self._safe_int(_ln.get('quantity', 0))))\n")
patch('issue_repository.py', [
    ('[ADD-VAL]', "            now_iso = datetime.now().isoformat()\n            if not outbound_load_id:",
     "            now_iso = datetime.now().isoformat()\n" + B1 + "            if not outbound_load_id:"),
    ('[ADD-OLI]', "            outbound_load_id = conn.execute(\"SELECT last_insert_rowid()\").fetchone()[0]",
     "            outbound_load_id = conn.execute(\"SELECT last_insert_rowid()\").fetchone()[0]" + B2),
    ('[ADD-OLI2]', "            ref_no = conn.execute(\"SELECT reference_no FROM outbound_loads WHERE id = ?\", (outbound_load_id,)).fetchone()[0]",
     "            ref_no = conn.execute(\"SELECT reference_no FROM outbound_loads WHERE id = ?\", (outbound_load_id,)).fetchone()[0]" + B3),
])

# ---------- RECEIPT: پلاک + اقلام مرجع + اعتبارسنجی داخل اتصال اصلی ----------
OLDV = """    # اعتبارسنجی تعداد رسید نسبت به مانده حواله
    if inbound_load_id:
        try:
            with self.db.connect() as check_conn:
                check_conn.row_factory = None
                remaining_row = check_conn.execute(
                    "SELECT remaining_qty FROM inbound_loads WHERE id = ?",
                    (inbound_load_id,)
                ).fetchone()
                if remaining_row:
                    remaining_qty = int(remaining_row[0])
                    if received_qty_total > remaining_qty:
                        raise ValidationError(
                            f"تعداد تحویل ({received_qty_total:,}) از مانده حواله ({remaining_qty:,}) بیشتر است!"
                        )
        except ValidationError:
            raise
        except Exception:
            pass"""
VIN = ("        if inbound_load_id:\n"
       "            try:\n"
       "                remaining_row = conn.execute(\n"
       "                    \"SELECT remaining_qty FROM inbound_loads WHERE id = ?\",\n"
       "                    (inbound_load_id,)\n"
       "                ).fetchone()\n"
       "                if remaining_row and received_qty_total > int(remaining_row[0] or 0):\n"
       "                    raise ValidationError(\n"
       "                        \"تعداد تحویل ({:,}) از مانده حواله ({:,}) بیشتر است!\".format(\n"
       "                            received_qty_total, int(remaining_row[0] or 0)))\n"
       "            except ValidationError:\n"
       "                raise\n"
       "            except Exception:\n"
       "                pass\n")
FPL = ("        vehicle_type_i, vehicle_plate_i = '', ''\n"
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
BIL = ("\n            for _i, _ln in enumerate(lines, start=1):\n"
       "                try:\n"
       "                    conn.execute(\n"
       "                        \"INSERT INTO inbound_load_items (inbound_load_id, row_no, pallet_id, qty) \"\n"
       "                        \"VALUES (?,?,?,?)\",\n"
       "                        (inbound_load_id, _i, _ln.get('pallet_id'), self._safe_int(_ln.get('quantity', 0))))\n"
       "                except Exception:\n"
       "                    pass\n")
patch('receipt_repository.py', [
    ('[ADD-VAL-IN]', OLDV, "    # اعتبارسنجی مانده داخل اتصال اصلی (پایین‌تر) انجام می‌شود"),
    ('[ADD-VAL-IN2]', "    with self.db.connect() as conn:\n        conn.row_factory = None\n        # Create or reuse inbound_loads",
     "    with self.db.connect() as conn:\n        conn.row_factory = None\n" + VIN + "        # Create or reuse inbound_loads"),
    ('[ADD-PLATE]', "        # Insert warehouse_receipts", FPL + "        # Insert warehouse_receipts"),
    ('[ADD-PLATE2]', "waybill_no, supplier_id, driver_id, '', '',",
     "waybill_no, supplier_id, driver_id, vehicle_type_i, vehicle_plate_i,"),
    ('[ADD-ILI]', "            inbound_load_id = conn.execute(\"SELECT last_insert_rowid()\").fetchone()[0]",
     "            inbound_load_id = conn.execute(\"SELECT last_insert_rowid()\").fetchone()[0]" + BIL),
])

# ---------- RETURN: خالص‌سازی سند اصلی (۷۵/۹۰) ----------
NET = ("        # ── [ADD-NET] خالص‌سازی سند اصلی در برگشت از فروش ──\n"
       "        if doc_type == 'ISSUE':\n"
       "            try:\n"
       "                total_return_qty = sum(int(it['qty'] or 0) for it in items)\n"
       "                for item in items:\n"
       "                    conn.execute(\n"
       "                        \"UPDATE warehouse_issue_items SET qty = MAX(COALESCE(qty,0) - ?, 0) \"\n"
       "                        \"WHERE issue_id = ? AND pallet_id = ?\",\n"
       "                        (int(item['qty'] or 0), doc_id, item['pallet_id']))\n"
       "                conn.execute(\n"
       "                    \"UPDATE warehouse_issues SET delivered_qty = MAX(COALESCE(delivered_qty,0) - ?, 0), \"\n"
       "                    \"stage_load_qty = MAX(COALESCE(stage_load_qty,0) - ?, 0) WHERE id = ?\",\n"
       "                    (total_return_qty, total_return_qty, doc_id))\n"
       "                conn.execute(\n"
       "                    \"UPDATE financial_documents SET total_amount = MAX(COALESCE(total_amount,0) - ?, 0) \"\n"
       "                    \"WHERE issue_id = ? AND operation_type = 'OUTBOUND_ISSUE' AND status <> 'CANCELLED'\",\n"
       "                    (total_amount, doc_id))\n"
       "                ol = conn.execute(\"SELECT outbound_load_id FROM warehouse_issues WHERE id = ?\", (doc_id,)).fetchone()\n"
       "                if ol and ol[0]:\n"
       "                    row = conn.execute(\"SELECT total_load_qty FROM outbound_loads WHERE id = ?\", (ol[0],)).fetchone()\n"
       "                    if row:\n"
       "                        dsum = conn.execute(\n"
       "                            \"SELECT COALESCE(SUM(delivered_qty),0) FROM warehouse_issues \"\n"
       "                            \"WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'\", (ol[0],)).fetchone()[0]\n"
       "                        conn.execute(\n"
       "                            \"UPDATE outbound_loads SET remaining_qty = MAX(? - ?, 0) WHERE id = ?\",\n"
       "                            (int(row[0] or 0), int(dsum or 0), ol[0]))\n"
       "            except Exception as e:\n"
       "                print('[net] skipped:', str(e)[:120])\n")
patch('return_repository.py', [
    ('[ADD-NET]', "        conn.commit()\n        person = conn.execute(",
     NET + "        conn.commit()\n        person = conn.execute("),
])
print('پایان بازنگری ✔ — حالا ری‌استارت کنید.')
input('Enter...')