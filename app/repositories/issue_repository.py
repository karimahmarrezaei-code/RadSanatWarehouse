
def _cumulative_issue_delivered(conn, outbound_load_id, issue_no=None, stage_no=None, current_delivered=0):
    """تحویل تجمعی حواله‌های یک بار. [CUMDEL2]"""
    if not outbound_load_id:
        return int(current_delivered or 0)
    sm = int(conn.execute(
        "SELECT COALESCE(SUM(delivered_qty),0) FROM warehouse_issues "
        "WHERE outbound_load_id=? AND issue_status!='CANCELLED'",
        (outbound_load_id,)).fetchone()[0])
    already = conn.execute(
        "SELECT 1 FROM warehouse_issues WHERE outbound_load_id=? AND issue_no=? AND stage_no=?",
        (outbound_load_id, issue_no, stage_no)).fetchone()
    return sm if already else sm + int(current_delivered or 0)

# -*- coding: utf-8 -*-
"""Issue Repository - نسخه نهایی کامل (خودرو + مسئول انبار + تحویل گیرنده)
⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
[PRICE] کنترل قیمت ردیف‌ها: قیمت صفر/منفی برای ردیف با تعداد>0 دیگر پذیرفته نمی‌شود
[SAFE]  در rollback_issue: اگر سند مالی دارای پرداخت/چک وصول‌شده (CLEARED) باشد، ابطال رد می‌شود
[FIX]   تعمیر کامل تخریب‌های کپی-پیست (سینتکس و ایندنت)
[ROLLBACK] sync inventory_levels + BEGIN IMMEDIATE + ثبت cancelled_by/cancelled_at/cancel_reason
"""
import datetime as _dt
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.core.numbering_service import NumberingService
from app.core.sequence_utils import next_sequence_no, peek_sequence_no
def _load_metrics(db, reference_no):
    try:
        with db.connect() as cn:
            cn.row_factory = None
            r = cn.execute("SELECT id FROM outbound_loads WHERE reference_no=?", (reference_no,)).fetchone()
            if not r:
                return (0, 0)
            pl = cn.execute("SELECT COALESCE(SUM(qty),0) FROM outbound_load_items WHERE outbound_load_id=?", (r[0],)).fetchone()[0]
            iss = cn.execute("SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=? AND wi.issue_status!='CANCELLED'", (r[0],)).fetchone()[0]
            return (int(pl or 0), int(iss or 0))
    except Exception:
        return (0, 0)






class IssueRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ---------------------------------------------------------------
    # Lookups
    # ---------------------------------------------------------------
    def list_customers(self) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT p.id, p.first_name, p.last_name, p.mobile "
                    "FROM persons p JOIN person_roles pr ON pr.person_id = p.id AND pr.role_type = 'CUSTOMER' "
                    "WHERE p.is_active = 1 ORDER BY p.first_name, p.last_name"
                ).fetchall()
                return [{'id': r[0], 'first_name': r[1] or '', 'last_name': r[2] or '', 'mobile': r[3] or ''} for r in rows]
        except Exception:
            return []

    def list_drivers(self) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT p.id, p.first_name, p.last_name, p.mobile, "
                    "       COALESCE(dp.vehicle_type,''), COALESCE(dp.vehicle_plate,'') "
                    "FROM persons p JOIN person_roles pr ON pr.person_id = p.id AND pr.role_type = 'DRIVER' "
                    "LEFT JOIN driver_profiles dp ON dp.person_id = p.id "
                    "WHERE p.is_active = 1 ORDER BY p.first_name, p.last_name"
                ).fetchall()
                return [{'id': r[0], 'first_name': r[1] or '', 'last_name': r[2] or '',
                         'mobile': r[3] or '', 'vehicle_type': r[4] or '', 'vehicle_plate': r[5] or ''} for r in rows]
        except Exception:
            return []

    def list_pallets(self) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT id, code, name FROM pallets WHERE is_active = 1 ORDER BY code").fetchall()
                return [{'id': r[0], 'code': r[1] or '', 'name': r[2] or ''} for r in rows]
        except Exception:
            return []

    def list_warehouses(self) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY code").fetchall()
                return [{'id': r[0], 'code': r[1] or '', 'name': r[2] or ''} for r in rows]
        except Exception:
            return []

    def list_open_outbound_references(self) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, reference_no, customer_id, driver_id, total_load_qty, remaining_qty, "
                    "waybill_no, source_location, destination_location FROM outbound_loads "
                    "WHERE load_status IN ('OPEN','PARTIAL') AND remaining_qty > 0 AND is_active = 1 ORDER BY id DESC"
                ).fetchall()
                return [{'id': r[0], 'reference_no': r[1], 'customer_id': r[2], 'driver_id': r[3],
                         'total_load_qty': r[4], 'remaining_qty': r[5], 'waybill_no': r[6],
                         'source_location': r[7], 'destination_location': r[8]} for r in rows]
        except Exception:
            return []

    def list_outbound_load_pallet_ids(self, outbound_load_id: int) -> List[int]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                try:
                    rows = conn.execute(
                        "SELECT pallet_id FROM outbound_load_items WHERE outbound_load_id = ? ORDER BY row_no",
                        (outbound_load_id,)
                    ).fetchall()
                    ids = [r[0] for r in rows]
                    if ids:
                        return ids
                except Exception:
                    pass
                rows = conn.execute(
                    "SELECT DISTINCT wii.pallet_id FROM warehouse_issue_items wii "
                    "JOIN warehouse_issues wi ON wi.id = wii.issue_id "
                    "WHERE wi.outbound_load_id = ? ORDER BY wii.pallet_id",
                    (outbound_load_id,)
                ).fetchall()
                return [r[0] for r in rows]
        except Exception:
            return []

    # ---------------------------------------------------------------
    # Numbers
    # ---------------------------------------------------------------
    def next_reference_no(self, iso_date: str) -> str:
        """شماره مرجع خروج - سریالی سالانه (استاندارد)"""
        with self.db.connect() as conn:
            return NumberingService.next('LOAD_OUT', conn, iso_date=iso_date)

    def peek_reference_no(self, iso_date: str) -> str:
        """پیش‌نمایش شماره مرجع (بدون جلو بردن شمارنده)"""
        with self.db.connect() as _conn:
            return peek_sequence_no(_conn, 'LOAD_OUT', iso_date=iso_date)

    def next_stage_no(self, outbound_load_id: int) -> int:
        with self.db.connect() as conn:
            conn.row_factory = None
            row = conn.execute(
                "SELECT COALESCE(MAX(stage_no), 0) FROM warehouse_issues WHERE outbound_load_id = ?",
                (outbound_load_id,)
            ).fetchone()
            return (int(row[0]) if row else 0) + 1

    def peek_stage_no(self, outbound_load_id: int) -> int:
        """پیش‌نمایش شماره مرحله (بدون جلو بردن)"""
        with self.db.connect() as _conn:
            _conn.row_factory = None
            row = _conn.execute(
                "SELECT COALESCE(MAX(stage_no), 0) FROM warehouse_issues WHERE outbound_load_id = ?",
                (outbound_load_id,)
            ).fetchone()
            return (int(row[0]) if row else 0) + 1

    def peek_document_no(self, reference_no: str, stage_no: int, personnel_id: Optional[int] = None) -> str:
        """پیش‌نمایش شماره حواله مرحله (بدون جلو بردن شمارنده)"""
        with self.db.connect() as conn:
            year = '1405'
            try:
                if '-' in reference_no:
                    year = reference_no.split('-')[1]
            except Exception:
                pass
            return NumberingService.peek('ISSUE', conn, iso_date=today_iso_date(), person_id=personnel_id)

    def build_document_no(self, conn, reference_no: str, stage_no: int, personnel_id: Optional[int] = None) -> str:
        """شماره حواله مرحله - سریالی سالانه (استاندارد)"""
        year = '1405'
        try:
            if '-' in reference_no:
                year = reference_no.split('-')[1]
        except Exception:
            pass
        return NumberingService.next('ISSUE', conn, iso_date=today_iso_date(), person_id=personnel_id)

    def _next_finance_no(self, conn) -> str:
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(finance_no, 4) AS INTEGER)) FROM financial_documents WHERE finance_no LIKE 'FN-%'"
        ).fetchone()
        next_num = (int(row[0]) if row and row[0] else 0) + 1
        return "FN-{:06d}".format(next_num)

    def get_pallet_avg_price(self, pallet_id: int) -> int:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT COALESCE(SUM(total_price), 0), COALESCE(SUM(qty_in), 0) "
                    "FROM inventory_transactions WHERE pallet_id = ? AND transaction_type = 'IN' AND qty_in > 0",
                    (pallet_id,)
                ).fetchone()
                tp, q = int(row[0] or 0), int(row[1] or 0)
                return tp // q if q > 0 else 0
        except Exception:
            return 0

    # ---------------------------------------------------------------
    # Create
    # ---------------------------------------------------------------
    def create_outbound_issue(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        outbound_load_id = payload.get('outbound_load_id')
        operation_date = payload.get('operation_date', today_iso_date())
        customer_id = payload.get('customer_person_id')
        driver_id = payload.get('driver_person_id')
        total_declared = self._safe_int(payload.get('total_declared_qty', '0'))
        stage_declared = self._safe_int(payload.get('stage_declared_qty', '0'))
        delivered_qty = self._safe_int(payload.get('delivered_qty', '0'))
        freight_amount = self._safe_int(payload.get('freight_amount', '0'))
        vat_enabled = bool(payload.get('vat_enabled', False))
        vat_amount = self._safe_int(payload.get('vat_amount', '0'))
        extra_costs = self._safe_int(payload.get('extra_costs', '0'))
        waybill_no = payload.get('waybill_no', '') or ''
        source_location = payload.get('source_location', '') or ''
        destination_location = payload.get('destination_location', '') or ''
        warehouse_keeper_name = payload.get('warehouse_keeper_name', '') or ''
        receiver_name = payload.get('receiver_name', '') or ''
        notes = payload.get('notes', '') or ''
        lines = payload.get('lines', [])
        if not lines:
            raise ValueError("حداقل یک ردیف پالت الزامی است")
        if not customer_id:
            raise ValueError("مشتری انتخاب نشده است")
        if not driver_id:
            raise ValueError("راننده انتخاب نشده است")
        if stage_declared <= 0:
            raise ValueError("تعداد این مرحله باید بزرگ‌تر از صفر باشد")
        if delivered_qty <= 0:
            raise ValueError("تعداد تحویل باید بزرگ‌تر از صفر باشد")
        for idx, line in enumerate(lines, start=1):
            q = self._safe_int(line.get('quantity', 0))
            u = self._safe_int(line.get('unit_price', 0))
            if not line.get('pallet_id'):
                raise ValueError("ردیف {}: پالت انتخاب نشده".format(idx))
            if q > 0 and u <= 0:
                raise ValueError("ردیف {}: قیمت واحد باید بزرگ‌تر از صفر باشد (مقدار فعلی: {} ریال).".format(idx, u))
        issued_qty_total = sum(self._safe_int(line.get('quantity', 0)) for line in lines)
        total_amount = sum(self._safe_int(line.get('quantity', 0)) * self._safe_int(line.get('unit_price', 0)) for line in lines)
        lines_total_amount = total_amount
        if vat_enabled:
            vat_amount = int(lines_total_amount * 9 / 100)
        total_amount = lines_total_amount + vat_amount + extra_costs
        with self.db.connect() as conn:
            conn.row_factory = None
            now_iso = datetime.now().isoformat()

            if outbound_load_id:
                _rem = conn.execute("SELECT remaining_qty FROM outbound_loads WHERE id = ?",
                                    (outbound_load_id,)).fetchone()
                if _rem and int(_rem[0] or 0) < issued_qty_total:
                    raise ValueError(
                        "تعداد اقلام این حواله ({:,}) از ماندهٔ مرجع ({:,}) بیشتر است! "
                        "ابتدا مقدار حواله را اصلاح کنید یا مرجع دیگری انتخاب کنید.".format(
                            issued_qty_total, int(_rem[0] or 0)))
            if not outbound_load_id:
                if total_declared <= 0:
                    total_declared = issued_qty_total
                ref_no = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)

                conn.execute(
                    "INSERT INTO outbound_loads "
                    "(reference_no, customer_id, driver_id, total_load_qty, issued_qty_total, remaining_qty, "
                    " load_status, waybill_no, source_location, destination_location, register_date) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (ref_no, customer_id, driver_id, total_declared, 0, total_declared, 'OPEN',
                     waybill_no, source_location, destination_location, operation_date)
                )
                outbound_load_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for _i, _ln in enumerate(lines, start=1):
                try:
                    conn.execute(
                        "INSERT INTO outbound_load_items (outbound_load_id, row_no, pallet_id, qty) "
                        "VALUES (?,?,?,?)",
                        (outbound_load_id, _i, _ln.get('pallet_id'), self._safe_int(_ln.get('quantity', 0))))
                except Exception:
                    pass

            else:
                ref_no = conn.execute("SELECT reference_no FROM outbound_loads WHERE id = ?", (outbound_load_id,)).fetchone()[0]
            for _ln in lines:
                _pid = _ln.get('pallet_id')
                _has = conn.execute(
                    "SELECT 1 FROM outbound_load_items WHERE outbound_load_id = ? AND pallet_id = ?",
                    (outbound_load_id, _pid)).fetchone()
                if not _has:
                    _mx = conn.execute(
                        "SELECT COALESCE(MAX(row_no),0) FROM outbound_load_items WHERE outbound_load_id = ?",
                        (outbound_load_id,)).fetchone()[0]
                    conn.execute(
                        "INSERT INTO outbound_load_items (outbound_load_id, row_no, pallet_id, qty) "
                        "VALUES (?,?,?,?)",
                        (outbound_load_id, int(_mx or 0) + 1, _pid, self._safe_int(_ln.get('quantity', 0))))

            stage_no = int(conn.execute("SELECT COALESCE(MAX(stage_no),0) FROM warehouse_issues WHERE outbound_load_id=?", (outbound_load_id,)).fetchone()[0] or 0) + 1
            issue_no = self.build_document_no(conn, ref_no, stage_no, personnel_id=customer_id)
            stage_declared = issued_qty_total  # LOGIC
            _prev = conn.execute("SELECT COALESCE(SUM(delivered_qty),0) FROM warehouse_issues "
                                 "WHERE outbound_load_id=? AND issue_status!='CANCELLED'",
                                 (outbound_load_id,)).fetchone()[0]
            delivered_qty = int(_prev or 0) + stage_declared  # LOGIC
            discrepancy = total_declared - delivered_qty  # LOGIC
            vehicle_type, vehicle_plate = '', ''
            if driver_id:
                vr = conn.execute("SELECT COALESCE(vehicle_type,''), COALESCE(vehicle_plate,'') FROM driver_profiles WHERE person_id=?", (driver_id,)).fetchone()
                if vr:
                    vehicle_type, vehicle_plate = vr[0] or '', vr[1] or ''
            conn.execute(
                "INSERT INTO warehouse_issues "
                "(outbound_load_id, issue_no, stage_no, issue_date, jalali_date_text, waybill_no, "
                " customer_id, driver_id, vehicle_type, vehicle_plate, stage_load_qty, delivered_qty, "
                " discrepancy_qty, freight_amount, source_location, destination_location, "
                " warehouse_keeper_name, receiver_name, issue_status, description, print_html, created_by, created_at, vat_amount, extra_costs) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (outbound_load_id, issue_no, stage_no, operation_date, jalali_date_display_from_iso(operation_date),
                 waybill_no, customer_id, driver_id, vehicle_type, vehicle_plate,
                 stage_declared, delivered_qty, discrepancy, freight_amount,
                 source_location, destination_location, warehouse_keeper_name, receiver_name,
                 'CONFIRMED', notes, '', user_id, now_iso, vat_amount, extra_costs)
            )
            issue_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for idx, line in enumerate(lines, start=1):
                pallet_id = line.get('pallet_id')
                qty = self._safe_int(line.get('quantity', 0))
                unit_price = self._safe_int(line.get('unit_price', 0))
                warehouse_id = line.get('warehouse_id')
                if not warehouse_id:
                    raise ValueError("ردیف {}: انبار انتخاب نشده".format(idx))
                if qty <= 0:
                    raise ValueError("ردیف {}: تعداد باید بزرگ‌تر از صفر باشد".format(idx))
                conn.execute(
                    "INSERT INTO warehouse_issue_items "
                    "(issue_id, row_no, pallet_id, qty, unit_price, total_price, warehouse_id, defect_description) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (issue_id, idx, pallet_id, qty, unit_price, qty * unit_price, warehouse_id, line.get('defect_notes', '') or '')
                )
            for line in lines:
                qty = self._safe_int(line.get('quantity', 0))
                unit_price = self._safe_int(line.get('unit_price', 0))
                conn.execute(
                    "INSERT INTO inventory_transactions "
                    "(transaction_date, transaction_type, reference_type, reference_id, pallet_id, warehouse_id, "
                    " qty_in, qty_out, unit_price, total_price, description, created_at) "
                    "VALUES (?, 'OUT', 'ISSUE', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (operation_date, issue_id, line.get('pallet_id'), line.get('warehouse_id'), 0,
                     qty, unit_price, qty * unit_price, 'Issue ' + issue_no, now_iso)
                )
            row = conn.execute("SELECT total_load_qty FROM outbound_loads WHERE id = ?", (outbound_load_id,)).fetchone()
            if row:
                total_load = int(row[0] or 0)
                delivered_sum = conn.execute(
                    "SELECT COALESCE(SUM(delivered_qty), 0) FROM warehouse_issues "
                    "WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'",
                    (outbound_load_id,)
                ).fetchone()[0]
                new_remaining = max(total_load - int(delivered_sum or 0), 0)
                cur_issued = conn.execute(
                    "SELECT COALESCE(SUM(stage_load_qty), 0) FROM warehouse_issues "
                    "WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'",
                    (outbound_load_id,)
                ).fetchone()[0]
                new_status = 'OPEN' if new_remaining >= total_load else ('PARTIAL' if new_remaining > 0 else 'COMPLETE')
                conn.execute(
                    "UPDATE outbound_loads SET remaining_qty = ?, issued_qty_total = ?, load_status = ? WHERE id = ?",
                    (new_remaining, int(cur_issued or 0), new_status, outbound_load_id)
                )
            if total_amount > 0:
                conn.execute(
                    "INSERT INTO financial_documents "
                    "(finance_no, operation_type, direction, outbound_load_id, issue_id, counterparty_person_id, "
                    " finance_date, total_amount, settled_amount, status, description, created_at, created_by) "
                    "VALUES (?, 'OUTBOUND_ISSUE', 'RECEIVABLE', ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)",
                    (self._next_finance_no(conn), outbound_load_id, issue_id, customer_id, operation_date, total_amount, notes, now_iso, user_id)
                )
            if freight_amount > 0:
                conn.execute(
                    "INSERT INTO financial_documents "
                    "(finance_no, operation_type, direction, outbound_load_id, issue_id, counterparty_person_id, "
                    " finance_date, total_amount, settled_amount, status, description, created_at, created_by) "
                    "VALUES (?, 'OUTBOUND_FREIGHT', 'PAYABLE', ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)",
                    (self._next_finance_no(conn), outbound_load_id, issue_id, driver_id, operation_date, freight_amount, notes, now_iso, user_id)
                )
            print_lines = []
            for idx, line in enumerate(lines, start=1):
                pr = conn.execute("SELECT code, name FROM pallets WHERE id=?", (line.get('pallet_id'),)).fetchone()
                wr = conn.execute("SELECT name FROM warehouses WHERE id=?", (line.get('warehouse_id'),)).fetchone()
                print_lines.append({
                    'row_no': idx,
                    'pallet_code': (pr[0] or '-') if pr else '-',
                    'pallet_name': (pr[1] or '-') if pr else '-',
                    'quantity': self._safe_int(line.get('quantity', 0)),
                    'unit_price': self._safe_int(line.get('unit_price', 0)),
                    'total_amount': self._safe_int(line.get('quantity', 0)) * self._safe_int(line.get('unit_price', 0)),
                    'warehouse_name': (wr[0] or '-') if wr else '-',
                    'defect_description': line.get('defect_notes', '') or '-'
                })
            cr = conn.execute("SELECT first_name || ' ' || last_name FROM persons WHERE id=?", (customer_id,)).fetchone()
            customer_name = (cr[0] or '-').strip() if cr and cr[0] else '-'
            dr = conn.execute("SELECT first_name || ' ' || last_name FROM persons WHERE id=?", (driver_id,)).fetchone()
            driver_name = (dr[0] or '-').strip() if dr and dr[0] else '-'
            conn.commit()
        with self.db.connect() as _c2:  # CUMDEL2
            _cum = _cumulative_issue_delivered(_c2, outbound_load_id, issue_no, stage_no, delivered_qty)
        _disc = int(total_declared or 0) - _cum  # CUMDEL2
        print_html = self.render_issue_html({
            'reference_no': ref_no, 'issue_no': issue_no, 'stage_no': stage_no,
            'operation_date_jalali': jalali_date_display_from_iso(operation_date),
            'customer_name': customer_name,
            'driver_name': driver_name,
            'vehicle_type': vehicle_type or '-', 'vehicle_plate': vehicle_plate or '-',
            'waybill_no': waybill_no or '-',
            'source_location': source_location or '-',
            'destination_location': destination_location or '-',
            'total_declared_qty': total_declared, 'total_load_qty': stage_declared,
            'delivered_qty': _cum,  # CUMDEL2
            'discrepancy_qty': _disc,  # CUMDEL2
            'freight_amount': freight_amount, 'lines_total_amount': lines_total_amount,
            'vat_amount': vat_amount, 'extra_costs': extra_costs,
            'warehouse_keeper_name': warehouse_keeper_name or '-',
            'receiver_name': receiver_name or '-',
            'notes': notes or '-', 'lines': print_lines
        })
        return {'issue_id': issue_id, 'issue_no': issue_no, 'reference_no': ref_no, 'print_html': print_html}


    def list_issue_tree(self):  # ISSUE-TREE-V3
        query = (
            "SELECT ol.id, ol.reference_no, COALESCE(ol.total_load_qty,0), "
            "COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii "
            " JOIN warehouse_issues wi0 ON wi0.id=wii.issue_id "
            " WHERE wi0.outbound_load_id=ol.id AND wi0.issue_status!='CANCELLED'),0), "
            "wi.id, wi.issue_no, wi.issue_date, wi.issue_status, "
            "COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii WHERE wii.issue_id=wi.id),0), "
            "COALESCE(cp.first_name||' '||cp.last_name,'-'), COALESCE(dr.first_name||' '||dr.last_name,'-'), "
            "(SELECT GROUP_CONCAT(DISTINCT w.name) FROM warehouse_issue_items wii2 "
            " LEFT JOIN warehouses w ON w.id=wii2.warehouse_id WHERE wii2.issue_id=wi.id), "
            "ol.load_status "
            "FROM outbound_loads ol "
            "LEFT JOIN warehouse_issues wi ON wi.outbound_load_id=ol.id "
            "LEFT JOIN persons cp ON cp.id=wi.customer_id "
            "LEFT JOIN persons dr ON dr.id=wi.driver_id "
            "ORDER BY ol.reference_no, wi.issue_date, wi.id"
        )
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(query).fetchall()
        return [{
            'load_id': r[0], 'mother_no': r[1], 'mother_total': int(r[2] or 0), 'mother_drawn': int(r[3] or 0),
            'issue_id': r[4], 'issue_no': r[5], 'issue_date': r[6], 'issue_status': r[7],
            'issue_qty': int(r[8] or 0), 'customer': r[9], 'driver': r[10], 'warehouses': r[11],
            'load_status': r[12],
        } for r in rows]


    def list_recent_issues(self) -> List[Dict[str, Any]]:
        """لیست همه حواله‌های ثبت‌شده + مانده واقعی مرجع (یک تعریف واحد)"""
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wi.id, wi.issue_no, ol.reference_no, wi.outbound_load_id, "
                "       COALESCE(p1.first_name || ' ' || p1.last_name, '-'), "
                "       COALESCE(p2.first_name || ' ' || p2.last_name, '-'), "
                "       COALESCE(ol.total_load_qty, 0), "
                "       COALESCE(wi.stage_load_qty, 0), "  # LIST-FIX
                "       MAX(0, COALESCE(ol.total_load_qty,0) - (SELECT COALESCE(SUM(w2.stage_load_qty),0) FROM warehouse_issues w2 WHERE w2.outbound_load_id=ol.id AND w2.issue_status!='CANCELLED')), "
                "       wi.issue_date, wi.issue_status "
                "FROM warehouse_issues wi "
                "LEFT JOIN outbound_loads ol ON wi.outbound_load_id = ol.id "
                "LEFT JOIN persons p1 ON wi.customer_id = p1.id "
                "LEFT JOIN persons p2 ON wi.driver_id = p2.id "
                "WHERE wi.issue_status != 'CANCELLED' "
                "ORDER BY wi.id DESC LIMIT 200"
            ).fetchall()
            return [{'id': r[0], 'issue_no': r[1] or '-', 'reference_no': r[2] or '-',
                    'outbound_load_id': r[3],
                    'customer_name': r[4] or '-', 'driver_name': r[5] or '-',
                    'total_qty': r[6] or 0, 'delivered_qty': r[7] or 0,
                    'ref_remaining': r[8] or 0, 'issue_date': r[9] or '-',
                    'issue_status': r[10] or 'CONFIRMED'} for r in rows]
    def get_issue(self, issue_id: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as conn:
            conn.row_factory = None
            row = conn.execute(
                "SELECT wi.id, wi.issue_no, COALESCE(ol.reference_no, ''), wi.stage_no, wi.issue_date, "
                "       wi.jalali_date_text, wi.customer_id, wi.driver_id, "
                "       COALESCE(wi.vehicle_type, ''), COALESCE(wi.vehicle_plate, ''), "
                "       COALESCE(wi.source_location, ''), COALESCE(wi.destination_location, ''), "
                "       COALESCE(wi.stage_load_qty, 0), COALESCE(wi.delivered_qty, 0), "
                "       COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii WHERE wii.issue_id = wi.id), 0), "
                "       COALESCE(ol.remaining_qty, 0), wi.issue_status, COALESCE(wi.description, ''), "
                "       COALESCE(wi.print_html, ''), wi.created_by, "
                "       COALESCE((SELECT SUM(wii.total_price) FROM warehouse_issue_items wii WHERE wii.issue_id = wi.id), 0), "
                "       COALESCE(wi.waybill_no, ''), COALESCE(wi.warehouse_keeper_name, ''), "
                "       COALESCE(wi.receiver_name, ''), COALESCE(wi.freight_amount, 0), "
                "       COALESCE(wi.vat_amount, 0), COALESCE(wi.extra_costs, 0) "
                "FROM warehouse_issues wi LEFT JOIN outbound_loads ol ON wi.outbound_load_id = ol.id "
                "WHERE wi.id = ?", (issue_id,)
            ).fetchone()
            if not row:
                return None
            return {'id': row[0], 'issue_no': row[1], 'reference_no': row[2], 'stage_no': row[3],
                    'issue_date': row[4], 'jalali_date_text': row[5], 'customer_id': row[6],
                    'driver_id': row[7], 'vehicle_type': row[8], 'vehicle_plate': row[9],
                    'source_location': row[10], 'destination_location': row[11],
                    'total_load_qty': row[12], 'delivered_qty': row[13], 'issued_qty_total': row[14],
                    'remaining_qty': row[15], 'issue_status': row[16], 'load_status': row[16],
                    'description': row[17], 'print_html': row[18], 'created_by': row[19],
                    'total_amount': row[20], 'waybill_no': row[21], 'warehouse_keeper_name': row[22],
                    'receiver_name': row[23], 'freight_amount': row[24], 'vat_amount': row[25],
                    'extra_costs': row[26]}
    def _sync_inventory_levels_for_issue(self, conn, issue_id: int) -> None:
        """همگام‌سازی موجودی = افتتاحیه(پالت) + خالص کاردکس(پالت+انبار)"""
        try:
            conn.execute("""
                UPDATE inventory_levels
                SET quantity = (
                    SELECT COALESCE(SUM(q), 0) FROM (
                        SELECT o.qty AS q
                        FROM opening_inventory_items o
                        WHERE o.pallet_id = inventory_levels.pallet_id
                        UNION ALL
                        SELECT CASE WHEN t.transaction_type = 'IN' THEN t.qty_in ELSE -t.qty_out END
                        FROM inventory_transactions t
                        WHERE t.pallet_id = inventory_levels.pallet_id
                          AND t.warehouse_id = inventory_levels.warehouse_id
                          AND COALESCE(t.is_void, 0) = 0
                    )
                )
                WHERE EXISTS (
                    SELECT 1 FROM warehouse_issue_items wii
                    WHERE wii.issue_id = ?
                      AND wii.pallet_id   = inventory_levels.pallet_id
                      AND wii.warehouse_id = inventory_levels.warehouse_id
                )
            """, (issue_id,))
        except Exception as e:
            print('[rollback] inventory_levels sync skipped:', str(e))

    def _reverse_journals_for_docs(self, conn, doc_ids, user_id, reason):
        """ثبت سند برگشتی روزنامه (با تاریخ امروز) برای هر سند مالی، قبل از ابطال آن"""
        try:
            import sqlite3
            from app.repositories.finance_repository import FinanceRepository
            fin = FinanceRepository(self.db)
            prev = conn.row_factory
            conn.row_factory = sqlite3.Row
            for did in doc_ids:
                d = conn.execute(
                    "SELECT * FROM financial_documents WHERE id = ?", (did,)
                ).fetchone()
                if not d:
                    continue
                doc = {k: d[k] for k in d.keys()}
                fin._create_reversal_journal_for_finance_doc(conn, doc, user_id=user_id, reason=reason)
            conn.row_factory = prev
        except Exception as e:
            print('[rollback] reversal journal skipped:', str(e))      


    def rollback_issue(self, issue_id: int, user_id: Optional[int] = None, reason: str = '') -> Dict[str, Any]:
        with self.db.connect() as conn:
            conn.row_factory = None
            st = conn.execute("SELECT issue_status FROM warehouse_issues WHERE id = ?", (issue_id,)).fetchone()
            if not st:
                raise ValueError("حواله یافت نشد")
            if st[0] == 'CANCELLED':
                raise ValueError("این حواله قبلاً ابطال شده است")
            issue = self.get_issue(issue_id)
            issue_no = issue['issue_no']
            outbound_load_id = conn.execute(
                "SELECT outbound_load_id FROM warehouse_issues WHERE id = ?", (issue_id,)
            ).fetchone()[0]
            finance_ids = conn.execute(
                "SELECT id FROM financial_documents WHERE issue_id = ? AND status <> 'CANCELLED'",
                (issue_id,)
            ).fetchall()
            for fid in finance_ids:
                cleared = conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM payment_entries "
                    "WHERE financial_document_id = ? AND status = 'CLEARED'", (fid[0],)
                ).fetchone()
                if cleared and cleared[0] > 0:
                    raise ValueError(
                        f"این حواله دارای {cleared[0]} پرداخت وصول‌شده به مبلغ {int(cleared[1]):,} ریال است؛ "
                        "ابتدا تسویه‌ها را برگردانید، سپس ابطال کنید."
                    )
            now_iso = datetime.now().isoformat()
            operation_date = issue.get('issue_date') or today_iso_date()
            rollback_reason = reason or f'ابطال امن حواله {issue_no}'
            conn.execute("BEGIN IMMEDIATE")
            doc_ids = [r[0] for r in conn.execute(
                "SELECT id FROM financial_documents WHERE issue_id = ? AND status <> 'CANCELLED'",
                (issue_id,)
            ).fetchall()]
            self._reverse_journals_for_docs(conn, doc_ids, user_id, reason or f'ابطال حواله {issue_no}')
            conn.execute(
                "UPDATE financial_documents SET status = 'CANCELLED' "
                "WHERE issue_id = ? AND status <> 'CANCELLED'", (issue_id,)
            )
            items = conn.execute(
                "SELECT pallet_id, warehouse_id, qty, unit_price, total_price "
                "FROM warehouse_issue_items WHERE issue_id = ?", (issue_id,)
            ).fetchall()
            for it in items:
                qty = int(it[2] or 0)
                conn.execute(
                    "INSERT INTO inventory_transactions "
                    "(transaction_date, transaction_type, reference_type, reference_id, "
                    " pallet_id, warehouse_id, qty_in, qty_out, unit_price, total_price, description, created_at) "
                    "VALUES (?, 'IN', 'ISSUE', ?, ?, ?, ?, 0, ?, ?, ?, ?)",
                    (operation_date, issue_id, it[0], it[1], qty,
                     int(it[3] or 0), int(it[4] or 0), 'ابطال حواله ' + issue_no, now_iso)
                )
            self._sync_inventory_levels_for_issue(conn, issue_id)
            conn.execute("UPDATE warehouse_issues SET issue_status = 'CANCELLED' WHERE id = ?", (issue_id,))
            for column, value in [('cancelled_by', user_id), ('cancelled_at', now_iso), ('cancel_reason', rollback_reason)]:
                try:
                    conn.execute(f"UPDATE warehouse_issues SET {column} = ? WHERE id = ?", (value, issue_id))
                except Exception:
                    pass
            if outbound_load_id:
                row = conn.execute(
                    "SELECT total_load_qty FROM outbound_loads WHERE id = ?", (outbound_load_id,)
                ).fetchone()
                if row:
                    total_load = int(row[0] or 0)
                    delivered_sum = conn.execute(
                        "SELECT COALESCE(SUM(delivered_qty), 0) FROM warehouse_issues "
                        "WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'",
                        (outbound_load_id,)
                    ).fetchone()[0]
                    new_remaining = max(total_load - int(delivered_sum or 0), 0)
                    cur_issued = conn.execute(
                        "SELECT COALESCE(SUM(stage_load_qty), 0) FROM warehouse_issues "
                        "WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'",
                        (outbound_load_id,)
                    ).fetchone()[0]
                    new_status = 'OPEN' if new_remaining >= total_load else ('PARTIAL' if new_remaining > 0 else 'COMPLETE')
                    conn.execute(
                        "UPDATE outbound_loads SET remaining_qty = ?, issued_qty_total = ?, load_status = ? WHERE id = ?",
                        (new_remaining, int(cur_issued or 0), new_status, outbound_load_id)
                    )
            conn.commit()
        return {'status': 'success', 'issue_no': issue_no,
                'message': f'حواله {issue_no} با موفقیت ابطال شد'}
    def get_company_info(self) -> Dict[str, Any]:
        try:
            from app.core.letterhead import get_filtered_company
            return get_filtered_company(self.db)
        except Exception:
            return {}

    def _pallet_info(self, pallet_id):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute("SELECT code, name FROM pallets WHERE id = ?", (pallet_id,)).fetchone()
                if row:
                    return row[0] or '-', row[1] or '-'
        except Exception:
            pass
        return '-', '-'

    def _warehouse_name(self, warehouse_id):
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute("SELECT name FROM warehouses WHERE id = ?", (warehouse_id,)).fetchone()
                return (row[0] or '-') if row else '-'
        except Exception:
            return '-'

    def _driver_vehicle(self, driver_id):
        if not driver_id:
            return '', ''
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT COALESCE(vehicle_type, ''), COALESCE(vehicle_plate, '') "
                    "FROM driver_profiles WHERE person_id = ?", (driver_id,)
                ).fetchone()
                if row:
                    return row[0] or '', row[1] or ''
        except Exception:
            pass
        return '', ''

    @staticmethod
    def _number_to_persian_words(number):
        if number == 0:
            return 'صفر'
        ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
        tens = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
        hundreds = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
        
        def three_digits(n):
            result = ''
            h = n // 100
            t = (n % 100) // 10
            o = n % 10
            if h > 0:
                result += hundreds[h] + ' و '
            if t == 1:
                result += ones[10 + o]
            else:
                if t > 0:
                    result += tens[t]
                    if o > 0:
                        result += ' و ' + ones[o]
                elif o > 0:
                    result += ones[o]
            return result.strip(' و ')
            
        if number < 0:
            return 'منفی ' + IssueRepository._number_to_persian_words(-number)
        parts = []
        if number >= 1000000000:
            parts.append(three_digits(number // 1000000000) + ' میلیارد')
            number %= 1000000000
        if number >= 1000000:
            parts.append(three_digits(number // 1000000) + ' میلیون')
            number %= 1000000
        if number >= 1000:
            parts.append(three_digits(number // 1000) + ' هزار')
            number %= 1000
        if number > 0:
            parts.append(three_digits(number))
        return ' و '.join(parts)

    def render_saved_issue_html(self, issue_id: int) -> Optional[str]:
        """بازسازی HTML حواله ذخیره‌شده با قالب جدید و همه المان‌ها"""
        issue = self.get_issue(issue_id)
        if not issue:
            return None
        with self.db.connect() as conn:
            conn.row_factory = None
            items = conn.execute(
                "SELECT row_no, pallet_id, qty, unit_price, total_price, warehouse_id, "
                "COALESCE(defect_description,'') FROM warehouse_issue_items WHERE issue_id=? ORDER BY row_no",
                (issue_id,)
            ).fetchall()
        lines = []
        for it in items:
            p_code, p_name = self._pallet_info(it[1])
            lines.append({'row_no': it[0], 'pallet_code': p_code, 'pallet_name': p_name,
                          'quantity': int(it[2] or 0), 'unit_price': int(it[3] or 0),
                          'total_amount': int(it[4] or 0), 'warehouse_name': self._warehouse_name(it[5]),
                          'defect_description': it[6] or '-'})
        stage_qty = int(issue.get('total_load_qty') or 0)
        delivered = int(issue.get('delivered_qty') or 0)
        return self.render_issue_html({
            'reference_no': issue.get('reference_no') or '-',
            'issue_no': issue.get('issue_no') or '-',
            'stage_no': issue.get('stage_no') or 1,
            'operation_date_jalali': issue.get('jalali_date_text') or (jalali_date_display_from_iso(issue['issue_date']) if issue.get('issue_date') else '-'),
            'customer_name': self._customer_name(issue.get('customer_id')),
            'driver_name': self._driver_name(issue.get('driver_id')),
            'vehicle_type': issue.get('vehicle_type') or '-',
            'vehicle_plate': issue.get('vehicle_plate') or '-',
            'waybill_no': issue.get('waybill_no') or '-',
            'source_location': issue.get('source_location') or '-',
            'destination_location': issue.get('destination_location') or '-',
            'total_declared_qty': stage_qty, 'total_load_qty': stage_qty,
            'delivered_qty': delivered, 'discrepancy_qty': max(stage_qty - delivered, 0),
            'freight_amount': int(issue.get('freight_amount') or 0),
            'lines_total_amount': int(issue.get('total_amount') or 0) - int(issue.get('vat_amount') or 0) - int(issue.get('extra_costs') or 0),
            'vat_amount': int(issue.get('vat_amount') or 0),
            'extra_costs': int(issue.get('extra_costs') or 0),
            'warehouse_keeper_name': issue.get('warehouse_keeper_name') or '-',
            'receiver_name': issue.get('receiver_name') or '-',
            'notes': issue.get('description') or '-', 'lines': lines
        })

    def render_issue_html(self, context: Dict[str, Any]) -> str:
        try:
            _m_pl, _m_is = _load_metrics(self.db, context.get('reference_no'))
            context = dict(context)
            context['total_load_qty'] = _m_pl
            context['delivered_qty'] = _m_is
            context['discrepancy_qty'] = _m_pl - _m_is
        except Exception:
            pass
        company = self.get_company_info()
        lines_html = ""
        defect_html = ""
        for line in context.get('lines', []):
            _up = '{:,}'.format(int(line.get('unit_price', 0) or 0)).replace(',', ',\u2060')
            _ta = '{:,}'.format(int(line.get('total_amount', 0) or 0)).replace(',', ',\u2060')
            lines_html += (  # NOBR
                "<tr><td>{row_no}</td><td>{pallet_code}</td><td>{pallet_name}</td>"
                "<td>{quantity:,}</td><td align='left'>" + _up + "</td><td align='left'>" + _ta + "</td>"
                "<td>{warehouse_name}</td></tr>"
            ).format(**line)
            _dd = str(line.get('defect_description') or '').strip()
            if _dd and _dd != '-':
                defect_html += '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (line.get('row_no',''), line.get('pallet_code',''), _dd)
        defect_table = ('<table width="100%" border="0" cellspacing="0" cellpadding="4">'
                        '<tr><td bgcolor="#f8fafc"><font size="2"><b>توضیحات ردیف‌ها:</b></font></td></tr>'
                        + defect_html + '</table>') if defect_html else ''
        lines_total_amount = int(context.get('lines_total_amount', 0) or 0)
        vat_amount = int(context.get('vat_amount', 0) or 0)
        extra_costs = int(context.get('extra_costs', 0) or 0)
        total_amount = lines_total_amount + vat_amount + extra_costs
        amount_words = self._number_to_persian_words(total_amount) + ' ریال' if total_amount > 0 else '-'
        ceo_line = "<p>مدیر عامل: {}</p>".format(company.get('ceo_name', '')) if company.get('ceo_name') else ""
        national_parts = []
        if company.get('national_id'):
            national_parts.append("شناسه ملی: {}".format(company['national_id']))
        if company.get('economic_code'):
            national_parts.append("کد اقتصادی: {}".format(company['economic_code']))
        if company.get('registration_number'):
            national_parts.append("شماره ثبت: {}".format(company['registration_number']))
        national_line = "<p>{}</p>".format(" | ".join(national_parts)) if national_parts else ""
        phone_parts = []
        if company.get('phone'):
            phone_parts.append("تلفن: {}".format(company['phone']))
        if company.get('mobile'):
            phone_parts.append("موبایل: {}".format(company['mobile']))
        if company.get('email'):
            phone_parts.append("ایمیل: {}".format(company['email']))
        if company.get('website'):
            phone_parts.append("وب‌سایت: {}".format(company['website']))
        phone_line = "<p>{}</p>".format(" | ".join(phone_parts)) if phone_parts else ""
        addr_line = "<p>آدرس: {}</p>".format(company.get('address')) if company.get('address') else ""
        notes = context.get('notes', '-') or '-'
        notes_box = '<div class="notes-box"><strong>توضیحات:</strong> {}</div>'.format(notes) if notes and notes != '-' else ""
        
        return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>حواله خروج انبار {issue_no}</title></head>
<body dir="rtl" style="font-family:Tahoma,Arial,sans-serif;color:#1e293b;">
<table dir="rtl" width="100%" border="0" dir="rtl"><tr><td>
<table dir="rtl" width="100%" cellspacing="0" cellpadding="3" border="0"><tr>
<td width="62%" valign="top">
<font size="6" color="#1e293b"><b>{company_name}</b></font><br>
<font size="2" color="#475569">{ceo_line}{national_line}{phone_line}{addr_line}</font>
</td>
<td width="38%" valign="top">
<table dir="rtl" width="100%" cellspacing="0" cellpadding="6" border="1">
<tr><td bgcolor="#f5f3ff" align="center">
<font size="4" color="#9333ea"><b>حواله خروج انبار</b></font><br>
<font size="2" color="#334155">
<b>شماره:</b> {issue_no}<br>
<b>مرجع بار:</b> {reference_no}<br>
<b>تاریخ:</b> {operation_date_jalali}<br>
<b>مرحله:</b> {stage_no}
</font></td></tr></table>
</td></tr></table>
<hr color="#9333ea" size="2">
<table dir="rtl" width="100%" cellspacing="0" cellpadding="8" border="1"><tr><td bgcolor="#fef3c7">
<font size="2">
<b>مشتری:</b> {customer_name} &nbsp;|&nbsp;
<b>راننده:</b> {driver_name} &nbsp;|&nbsp;
<b>خودرو:</b> {vehicle_type} | {vehicle_plate} &nbsp;|&nbsp;
<b>بارنامه:</b> {waybill_no} &nbsp;|&nbsp;
<b>مبدأ:</b> {source_location} &nbsp;|&nbsp;
<b>مقصد:</b> {destination_location}
</font></td></tr></table>
<table dir="rtl" width="100%" border="1" cellspacing="0" cellpadding="7">
<tr><th>ردیف</th><th>کد</th><th>پالت</th><th>تعداد</th><th>قیمت</th><th>مبلغ</th><th>انبار</th></tr>
{lines_html}
<tr bgcolor="#dbeafe"><td colspan="5"><b>جمع کل:</b></td><td colspan="2"><b>{lines_total_amount:,} ریال</b></td></tr>
<tr bgcolor="#f5f3ff"><td colspan="5"><b>ارزش افزوده ۹٪:</b></td><td colspan="2"><b>{vat_amount:,} ریال</b></td></tr>
<tr bgcolor="#f5f3ff"><td colspan="5"><b>مخارج اضافی:</b></td><td colspan="2"><b>{extra_costs:,} ریال</b></td></tr>
<tr bgcolor="#dcfce7"><td colspan="5"><b>قیمت نهایی:</b></td><td colspan="2"><b>{final_total:,} ریال</b></td></tr>
</table>
{defect_table}
<table dir="rtl" width="100%" cellspacing="0" cellpadding="8" border="0"><tr><td bgcolor="#f8fafc">
<font size="2">مبلغ به حروف: <b>{amount_words}</b></font>
</td></tr></table>
<table dir="rtl" width="100%" cellspacing="0" cellpadding="10" border="0"><tr><td bgcolor="#f1f5f9">
<table dir="rtl" width="100%" border="0" cellspacing="0" cellpadding="3"><tr>
<td><font size="2">تعداد کل بار: <b>{total_declared_qty:,}</b></font></td>
<td><font size="2">تعداد این مرحله: <b>{total_load_qty:,}</b></font></td>
</tr><tr>
<td><font size="2">تحویل به انبار: <b>{delivered_qty:,}</b></font></td>
<td><font size="2">مغایرت: <b>{discrepancy_qty:,}</b></font></td>
</tr><tr>
<td><font size="2">پس‌کرایه: <b>{freight_amount:,} ریال</b></font></td>
<td><font size="2">مسئول انبار: <b>{warehouse_keeper_name}</b> &nbsp;|&nbsp; تحویل‌گیرنده: <b>{receiver_name}</b></font></td>
</tr></table>
</td></tr></table>
{notes_box}
<table dir="rtl" width="100%" cellspacing="0" cellpadding="10" border="0"><tr>
<td align="center"><br><br>____________________<br><font size="2">مهر و امضای فروشنده</font></td>
<td align="center"><br><br>____________________<br><font size="2">مسئول انبار</font></td>
<td align="center"><br><br>____________________<br><font size="2">تحویل‌گیرنده</font></td>
</tr></table>
<p align="center"><font size="1" color="#7c3aed">این سند به صورت سیستمی تولید شده است</font></p>
</td></tr></table>
</body></html>

<!-- UNIFIED-V3 --><!-- MARGIN-FIX --><!-- MOVE-NOTES --><!-- FONT-SMALL --><!-- LAYOUT-V2 -->
""".format(
            company_name=company.get('company_name', 'نام شرکت'),
            ceo_line=ceo_line, national_line=national_line, phone_line=phone_line, addr_line=addr_line,
            issue_no=context.get('issue_no', '-'), reference_no=context.get('reference_no', '-'),
            stage_no=context.get('stage_no', 1),
            operation_date_jalali=context.get('operation_date_jalali', '-'),
            customer_name=context.get('customer_name', '-'), driver_name=context.get('driver_name', '-'),
            vehicle_type=context.get('vehicle_type', '-'), vehicle_plate=context.get('vehicle_plate', '-'),
            waybill_no=context.get('waybill_no', '-'), source_location=context.get('source_location', '-'),
            destination_location=context.get('destination_location', '-'), lines_html=lines_html,
            delivered_qty=int(context.get('delivered_qty', 0) or 0), lines_total_amount=lines_total_amount,
            vat_amount=vat_amount, extra_costs=extra_costs, final_total=total_amount,
            amount_words=amount_words, total_declared_qty=int(context.get('total_declared_qty', 0) or 0),
            total_load_qty=int(context.get('total_load_qty', 0) or 0),
            discrepancy_qty=int(context.get('discrepancy_qty', 0) or 0),
            freight_amount=int(context.get('freight_amount', 0) or 0),
            warehouse_keeper_name=context.get('warehouse_keeper_name', '-'),
            receiver_name=context.get('receiver_name', '-'), defect_table=defect_table, notes_box=notes_box)

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------
    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            cleaned = str(value).replace(',', '').replace(' ', '')
            return int(float(cleaned))
        except (ValueError, TypeError):
            return 0

    def _customer_name(self, customer_id) -> str:
        if not customer_id:
            return '-'
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute("SELECT first_name || ' ' || last_name FROM persons WHERE id = ?", (customer_id,)).fetchone()
                return (row[0] or '-').strip() if row else '-'
        except Exception:
            return '-'

    def _driver_name(self, driver_id) -> str:
        if not driver_id:
            return '-'
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute("SELECT first_name || ' ' || last_name FROM persons WHERE id = ?", (driver_id,)).fetchone()
                return (row[0] or '-').strip() if row else '-'
        except Exception:
            return '-'
