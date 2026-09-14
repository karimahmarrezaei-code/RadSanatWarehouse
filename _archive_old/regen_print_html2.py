# -*- coding: utf-8 -*-
"""بازسازی print_html - نسخه ضدخطا - اجرا: python regen_print_html2.py"""
import os, sqlite3, traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
DBP = os.path.join(ROOT, 'data', 'app.db')

class FakeDB:
    def connect(self):
        c = sqlite3.connect(DBP)
        c.row_factory = sqlite3.Row
        return c

def g(r, k, d=None):
    try:
        v = r[k]
        return d if v is None else v
    except Exception:
        return d

from app.repositories.receipt_repository import ReceiptRepository
from app.repositories.issue_repository import IssueRepository
rr = ReceiptRepository(FakeDB())
ir = IssueRepository(FakeDB())

conn = sqlite3.connect(DBP)
conn.row_factory = sqlite3.Row
first_err = [False]

def cum(table, col, load_id, rid):
    r = conn.execute("SELECT COALESCE(SUM(delivered_qty),0) FROM {} WHERE {}=? AND id<=?".format(table, col), (load_id, rid)).fetchone()
    return int(r[0] or 0)

n1 = 0
for wr in conn.execute("SELECT * FROM warehouse_receipts"):
    try:
        lines = []
        for idx, x in enumerate(conn.execute(
            "SELECT wri.*, p.code AS pallet_code, p.name AS pallet_name, COALESCE(w.name,'') AS warehouse_name "
            "FROM warehouse_receipt_items wri JOIN pallets p ON p.id=wri.pallet_id "
            "LEFT JOIN warehouses w ON w.id=wri.warehouse_id WHERE wri.receipt_id=? ORDER BY wri.id", (wr['id'],)), 1):
            lines.append({'row_no': g(x, 'row_no', idx), 'pallet_code': g(x, 'pallet_code', ''),
                'pallet_name': g(x, 'pallet_name', ''), 'quantity': g(x, 'qty', 0), 'qty': g(x, 'qty', 0),
                'unit_price': g(x, 'unit_price', 0), 'total_price': g(x, 'total_price', 0),
                'total_amount': g(x, 'total_price', 0), 'warehouse_name': g(x, 'warehouse_name', ''),
                'defect_description': g(x, 'defect_description', '')})
        lt = sum(int(l['total_amount'] or 0) for l in lines)
        sup = conn.execute("SELECT COALESCE(first_name||' '||last_name,'') AS n FROM persons WHERE id=?", (g(wr, 'supplier_id'),)).fetchone()
        drv = conn.execute("SELECT COALESCE(first_name||' '||last_name,'') AS n FROM persons WHERE id=?", (g(wr, 'driver_id'),)).fetchone()
        load = conn.execute("SELECT COALESCE(total_load_qty,0) AS t FROM inbound_loads WHERE id=?", (g(wr, 'inbound_load_id'),)).fetchone() if g(wr, 'inbound_load_id') else None
        total_declared = int(load['t'] or 0) if load else int(g(wr, 'total_load_qty', 0) or 0)
        cumv = cum('warehouse_receipts', 'inbound_load_id', g(wr, 'inbound_load_id'), wr['id']) if g(wr, 'inbound_load_id') else int(g(wr, 'delivered_qty', 0) or 0)
        vat = int(g(wr, 'vat_amount', 0) or 0); ext = int(g(wr, 'extra_costs', 0) or 0)
        ctx = {'reference_no': g(wr, 'reference_no', ''), 'receipt_no': g(wr, 'receipt_no', ''),
            'stage_no': g(wr, 'stage_no', 1), 'operation_date_jalali': g(wr, 'jalali_date_text', ''),
            'supplier_name': sup['n'] if sup else '', 'driver_name': drv['n'] if drv else '',
            'vehicle_type': g(wr, 'vehicle_type', ''), 'vehicle_plate': g(wr, 'vehicle_plate', ''),
            'waybill_no': g(wr, 'waybill_no', ''), 'source_location': g(wr, 'source_location', ''),
            'destination_location': g(wr, 'destination_location', ''), 'lines': lines,
            'lines_total_amount': lt, 'vat_amount': vat, 'extra_costs': ext,
            'total_declared_qty': total_declared, 'stage_load_qty': int(g(wr, 'stage_load_qty', 0) or 0),
            'delivered_qty': cumv, 'discrepancy_qty': max(total_declared - cumv, 0),
            'freight_amount': int(g(wr, 'freight_amount', 0) or 0),
            'warehouse_keeper_name': g(wr, 'warehouse_keeper_name', ''), 'receiver_name': g(wr, 'receiver_name', ''),
            'notes': g(wr, 'description', '')}
        html = rr.render_receipt_html(ctx)
        conn.execute("UPDATE warehouse_receipts SET print_html=? WHERE id=?", (html, wr['id']))
        n1 += 1
    except Exception as e:
        if not first_err[0]:
            first_err[0] = True
            traceback.print_exc()
        print('⚠ رسید', wr['id'], str(e)[:90])

n2 = 0
for wi in conn.execute("SELECT * FROM warehouse_issues"):
    try:
        lines = []
        for idx, x in enumerate(conn.execute(
            "SELECT wii.*, p.code AS pallet_code, p.name AS pallet_name, COALESCE(w.name,'') AS warehouse_name "
            "FROM warehouse_issue_items wii JOIN pallets p ON p.id=wii.pallet_id "
            "LEFT JOIN warehouses w ON w.id=wii.warehouse_id WHERE wii.issue_id=? ORDER BY wii.id", (wi['id'],)), 1):
            lines.append({'row_no': g(x, 'row_no', idx), 'pallet_code': g(x, 'pallet_code', ''),
                'pallet_name': g(x, 'pallet_name', ''), 'quantity': g(x, 'qty', 0), 'qty': g(x, 'qty', 0),
                'unit_price': g(x, 'unit_price', 0), 'total_price': g(x, 'total_price', 0),
                'total_amount': g(x, 'total_price', 0), 'warehouse_name': g(x, 'warehouse_name', ''),
                'defect_description': g(x, 'defect_description', '')})
        lt = sum(int(l['total_amount'] or 0) for l in lines)
        cus = conn.execute("SELECT COALESCE(first_name||' '||last_name,'') AS n FROM persons WHERE id=?", (g(wi, 'customer_id'),)).fetchone()
        drv = conn.execute("SELECT COALESCE(first_name||' '||last_name,'') AS n FROM persons WHERE id=?", (g(wi, 'driver_id'),)).fetchone()
        load = conn.execute("SELECT COALESCE(total_load_qty,0) AS t FROM outbound_loads WHERE id=?", (g(wi, 'outbound_load_id'),)).fetchone() if g(wi, 'outbound_load_id') else None
        total_declared = int(load['t'] or 0) if load else int(g(wi, 'stage_load_qty', 0) or 0)
        cumv = cum('warehouse_issues', 'outbound_load_id', g(wi, 'outbound_load_id'), wi['id']) if g(wi, 'outbound_load_id') else int(g(wi, 'delivered_qty', 0) or 0)
        vat = int(g(wi, 'vat_amount', 0) or 0); ext = int(g(wi, 'extra_costs', 0) or 0)
        ctx = {'reference_no': g(wi, 'reference_no', ''), 'issue_no': g(wi, 'issue_no', ''),
            'stage_no': g(wi, 'stage_no', 1), 'operation_date_jalali': g(wi, 'jalali_date_text', ''),
            'customer_name': cus['n'] if cus else '', 'driver_name': drv['n'] if drv else '',
            'vehicle_type': g(wi, 'vehicle_type', ''), 'vehicle_plate': g(wi, 'vehicle_plate', ''),
            'waybill_no': g(wi, 'waybill_no', ''), 'source_location': g(wi, 'source_location', ''),
            'destination_location': g(wi, 'destination_location', ''), 'lines': lines,
            'lines_total_amount': lt, 'vat_amount': vat, 'extra_costs': ext,
            'total_declared_qty': total_declared, 'total_load_qty': int(g(wi, 'stage_load_qty', 0) or 0),
            'delivered_qty': cumv, 'discrepancy_qty': max(total_declared - cumv, 0),
            'freight_amount': int(g(wi, 'freight_amount', 0) or 0),
            'warehouse_keeper_name': g(wi, 'warehouse_keeper_name', ''), 'receiver_name': g(wi, 'receiver_name', ''),
            'notes': g(wi, 'description', '')}
        html = ir.render_issue_html(ctx)
        conn.execute("UPDATE warehouse_issues SET print_html=? WHERE id=?", (html, wi['id']))
        n2 += 1
    except Exception as e:
        if not first_err[0]:
            first_err[0] = True
            traceback.print_exc()
        print('⚠ حواله', wi['id'], str(e)[:90])

conn.commit()
conn.close()
print('✔ رسید:', n1, '| حواله:', n2)
input('Enter...')
