
def _cumulative_receipt_delivered(conn, inbound_load_id, receipt_no=None, stage_no=None, current_delivered=0):
    """تحویل تجمعی رسیدهای یک بار. [CUMDEL2]"""
    if not inbound_load_id:
        return int(current_delivered or 0)
    sm = int(conn.execute(
        "SELECT COALESCE(SUM(delivered_qty),0) FROM warehouse_receipts "
        "WHERE inbound_load_id=? AND receipt_status!='CANCELLED'",
        (inbound_load_id,)).fetchone()[0])
    already = conn.execute(
        "SELECT 1 FROM warehouse_receipts WHERE inbound_load_id=? AND receipt_no=? AND stage_no=?",
        (inbound_load_id, receipt_no, stage_no)).fetchone()
    return sm if already else sm + int(current_delivered or 0)

# -*- coding: utf-8 -*-
"""
Receipt Repository - نسخه نهایی با rollback امن

تغییرات اعمال‌شده (بازبینی ۱۴۰۵/۰۵/۱۱ + اصلاح rollback):
  ✅ BEGIN IMMEDIATE برای جلوگیری از race condition
  ✅ sync inventory_levels (مستقل از trigger)
  ✅ پیام خطای دقیق با تعداد و مبلغ پرداخت‌های وصول‌شده
  ✅ ثبت cancelled_by / cancelled_at / cancel_reason (اگر ستون‌ها موجود باشند)
  ✅ حذف try/except خاموش روی void کردن تراکنش‌ها
  ✅ چک receipt_status == CANCELLED قبل از ابطال
  ✅ تعیین درست وضعیت inbound_loads (OPEN/PARTIAL/COMPLETE)
  ✅ Pre-flight کامل در rollback_inbound_load
  ✅ یکپارچه‌سازی با finance_repository
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.core.numbering_service import NumberingService
from app.core.validators import ValidationError


class ReceiptRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ---------------------------------------------------------------
    # Lookups
    # ---------------------------------------------------------------

    def list_suppliers(self) -> List[Dict[str, Any]]:
        """لیست تأمین‌کنندگان فعال"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT p.id, p.first_name, p.last_name, p.mobile "
                    "FROM persons p "
                    "JOIN person_roles pr ON pr.person_id = p.id AND pr.role_type = 'SUPPLIER' "
                    "WHERE p.is_active = 1 ORDER BY p.first_name, p.last_name"
                ).fetchall()
                return [
                    {'id': r[0], 'first_name': r[1] or '', 'last_name': r[2] or '', 'mobile': r[3] or ''}
                    for r in rows
                ]
        except Exception:
            return []

    def list_drivers(self) -> List[Dict[str, Any]]:
        """لیست رانندگان فعال"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT p.id, p.first_name, p.last_name, p.mobile, "
                    "       COALESCE(dp.vehicle_type,''), COALESCE(dp.vehicle_plate,'') "
                    "FROM persons p "
                    "JOIN person_roles pr ON pr.person_id = p.id AND pr.role_type = 'DRIVER' "
                    "LEFT JOIN driver_profiles dp ON dp.person_id = p.id "
                    "WHERE p.is_active = 1 ORDER BY p.first_name, p.last_name"
                ).fetchall()
                return [
                    {
                        'id': r[0], 'first_name': r[1] or '', 'last_name': r[2] or '',
                        'mobile': r[3] or '', 'vehicle_type': r[4] or '', 'vehicle_plate': r[5] or ''
                    }
                    for r in rows
                ]
        except Exception:
            return []

    def list_pallets(self) -> List[Dict[str, Any]]:
        """لیست همه پالت‌های فعال"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, code, name FROM pallets WHERE is_active = 1 ORDER BY code"
                ).fetchall()
                return [{'id': r[0], 'code': r[1] or '', 'name': r[2] or ''} for r in rows]
        except Exception:
            return []

    def list_warehouses(self) -> List[Dict[str, Any]]:
        """لیست انبارهای فعال"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY code"
                ).fetchall()
                return [{'id': r[0], 'code': r[1] or '', 'name': r[2] or ''} for r in rows]
        except Exception:
            return []

    def list_open_inbound_references(self) -> List[Dict[str, Any]]:
        """لیست مراجع بار باز (OPEN/PARTIAL)"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, reference_no, supplier_id, driver_id, "
                    "       total_load_qty, remaining_qty, waybill_no, "
                    "       source_location, destination_location "
                    "FROM inbound_loads "
                    "WHERE load_status IN ('OPEN','PARTIAL') AND remaining_qty > 0 "
                    "ORDER BY id DESC"
                ).fetchall()
                return [
                    {
                        'id': r[0], 'reference_no': r[1], 'supplier_id': r[2], 'driver_id': r[3],
                        'total_load_qty': r[4], 'remaining_qty': r[5], 'waybill_no': r[6],
                        'source_location': r[7], 'destination_location': r[8]
                    }
                    for r in rows
                ]
        except Exception:
            return []

    # ---------------------------------------------------------------
    # Pallet Filtering
    # ---------------------------------------------------------------

    def get_pallets_for_reference(self, inbound_load_id: int) -> List[Dict[str, Any]]:
        """
        لیست پالت‌های قابل انتخاب — همیشه همه پالت‌های فعال.
        """
        return self.list_pallets()

    # ---------------------------------------------------------------
    # Reference numbers
    # ---------------------------------------------------------------

    def next_reference_no(self, iso_date, conn=None) -> str:
        """شماره مرجع بار ورود - WH-سال-0001 (جدا از رسید)"""
        if conn is None:
            with self.db.connect() as _conn:
                _conn.row_factory = None
                return NumberingService.next('LOAD_IN', _conn, iso_date=iso_date)
        conn.row_factory = None
        return NumberingService.next('LOAD_IN', conn, iso_date=iso_date)

    def next_stage_no(self, inbound_load_id, conn=None) -> int:
        """شماره مرحله بعدی رسید برای یک مرجع بار (MAX stage_no + 1)"""
        def _calc(c):
            row = c.execute(
                "SELECT COALESCE(MAX(CAST(stage_no AS INTEGER)), 0) "
                "FROM warehouse_receipts WHERE inbound_load_id = ?",
                (inbound_load_id,)
            ).fetchone()
            return (int(row[0]) if row and row[0] is not None else 0) + 1

        if conn is None:
            with self.db.connect() as _conn:
                _conn.row_factory = None
                return _calc(_conn)
        return _calc(conn)

    def peek_reference_no(self, iso_date: str, personnel_id: Optional[int] = None) -> str:
        """پیش‌نمایش شماره مرجع بار ورود (WH) - بدون جلو بردن شمارنده"""
        return NumberingService.peek('LOAD_IN', None, iso_date=iso_date)

    def peek_document_no(self, reference_no: str, stage_no: int,
                         personnel_id: Optional[int] = None) -> str:
        """پیش‌نمایش شماره رسید مرحله (بدون جلو بردن شمارنده) - پرسنل‌محور"""
        year = '1405'
        try:
            if '-' in reference_no:
                year = reference_no.split('-')[1]
        except Exception:
            pass
        return NumberingService.peek('RECEIPT', None,
                                     iso_date='20' + year + '-01-01',
                                     person_id=personnel_id)

    def peek_stage_no(self, inbound_load_id: int) -> int:
        """پیش‌نمایش شماره مرحله بعدی (بدون جلو بردن)"""
        with self.db.connect() as _conn:
            _conn.row_factory = None
            row = _conn.execute(
                "SELECT COALESCE(MAX(CAST(stage_no AS INTEGER)), 0) "
                "FROM warehouse_receipts WHERE inbound_load_id = ?",
                (inbound_load_id,)
            ).fetchone()
            return (int(row[0]) if row and row[0] is not None else 0) + 1

    def build_document_no(self, reference_no: str, stage_no: int, conn=None,
                          personnel_id: Optional[int] = None) -> str:
        """شماره رسید مرحله - از کلاس مرکزی (پرسنل‌محور)"""
        year = '1405'
        try:
            if '-' in reference_no:
                year = reference_no.split('-')[1]
        except Exception:
            pass
        return NumberingService.next('RECEIPT', conn,
                                     iso_date='20' + year + '-01-01',
                                     person_id=personnel_id)


    def _get_company_info(self) -> Dict[str, Any]:
        try:
            from app.core.letterhead import get_filtered_company
            return get_filtered_company(self.db)
        except Exception:
            return {}


    def create_inbound_receipt(self, payload: Dict[str, Any],
                               user_id: Optional[int] = None) -> Dict[str, Any]:
        """ثبت رسید انبار جدید"""
        inbound_load_id = payload.get('inbound_load_id')
        operation_date = payload.get('operation_date', today_iso_date())
        supplier_id = payload.get('supplier_person_id')
        driver_id = payload.get('driver_person_id')
        total_declared = self._safe_int(payload.get('total_declared_qty', '0'))
        stage_declared = self._safe_int(payload.get('stage_declared_qty', '0'))
        stage_received = self._safe_int(payload.get('stage_received_qty', '0'))
        freight_amount = self._safe_int(payload.get('freight_amount', '0'))
        vat_enabled = bool(payload.get('vat_enabled', False))
        vat_amount = self._safe_int(payload.get('vat_amount', '0'))
        extra_costs = self._safe_int(payload.get('extra_costs', '0'))

        waybill_no = payload.get('waybill_no', '') or ''
        source_location = payload.get('source_location', '') or ''
        destination_location = payload.get('destination_location', '') or ''
        warehouse_keeper = payload.get('warehouse_keeper_name', '') or ''
        receiver_name = payload.get('receiver_name', '') or ''
        notes = payload.get('notes', '') or ''
        lines = payload.get('lines', [])

        if not lines:
            raise ValidationError("حداقل یک ردیف پالت الزامی است")

        # کنترل قیمت ردیف‌ها قبل از هر چیز
        for idx, line in enumerate(lines, start=1):
            q = self._safe_int(line.get('quantity', 0))
            u = self._safe_int(line.get('unit_price', '0'))
            if not line.get('pallet_id'):
                raise ValidationError("ردیف {}: پالت انتخاب نشده".format(idx))
            if q > 0 and u <= 0:
                raise ValidationError(
                    "ردیف {}: قیمت واحد باید بزرگ‌تر از صفر باشد (مقدار فعلی: {} ریال).\n"
                    "لطفاً قیمت را بررسی کنید.".format(idx, u)
                )

        received_qty_total = sum(self._safe_int(line.get('quantity', 0)) for line in lines)

        # محاسبه مبلغ از qty × unit_price
        total_amount = sum(
            self._safe_int(line.get('quantity', 0)) * self._safe_int(line.get('unit_price', '0'))
            for line in lines
        )

        # قیمت نهایی = جمع ردیف‌ها + ارزش افزوده + مخارج
        lines_total_amount = total_amount
        if vat_enabled:
            vat_amount = int(lines_total_amount * 9 / 100)
        total_amount = lines_total_amount + vat_amount + extra_costs

        discrepancy = max(stage_declared - stage_received, 0)

        with self.db.connect() as conn:
            conn.row_factory = None
            if inbound_load_id:
                try:
                    remaining_row = conn.execute(
                        "SELECT remaining_qty FROM inbound_loads WHERE id = ?",
                        (inbound_load_id,)
                    ).fetchone()
                    if remaining_row and received_qty_total > int(remaining_row[0] or 0):
                        raise ValidationError(
                            "تعداد تحویل ({:,}) از مانده حواله ({:,}) بیشتر است!".format(
                                received_qty_total, int(remaining_row[0] or 0)))
                except ValidationError:
                    raise
                except Exception:
                    pass

            # Create or reuse inbound_loads
            if not inbound_load_id:
                ref_no = self.next_reference_no(operation_date, conn)
                conn.execute(
                    "INSERT INTO inbound_loads "
                    "(reference_no, supplier_id, driver_id, total_load_qty, "
                    " received_qty_total, remaining_qty, load_status, "
                    " waybill_no, source_location, destination_location, register_date) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (ref_no, supplier_id, driver_id, total_declared,
                     0, total_declared, 'OPEN',
                     waybill_no, source_location, destination_location, operation_date)
                )
                inbound_load_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for _i, _ln in enumerate(lines, start=1):
                try:
                    conn.execute(
                        "INSERT INTO inbound_load_items (inbound_load_id, row_no, pallet_id, qty) "
                        "VALUES (?,?,?,?)",
                        (inbound_load_id, _i, _ln.get('pallet_id'), self._safe_int(_ln.get('quantity', 0))))
                except Exception:
                    pass

            else:
                ref_no = conn.execute(
                    "SELECT reference_no FROM inbound_loads WHERE id = ?",
                    (inbound_load_id,)
                ).fetchone()[0]

            stage_no = self.next_stage_no(inbound_load_id, conn)
            receipt_no = self.build_document_no(ref_no, stage_no, conn, personnel_id=supplier_id)
            now_iso = datetime.now().isoformat()

            vehicle_type_i, vehicle_plate_i = '', ''
            if driver_id:
                try:
                    vr = conn.execute(
                        "SELECT COALESCE(vehicle_type, ''), COALESCE(vehicle_plate, '') "
                        "FROM driver_profiles WHERE person_id = ?", (driver_id,)
                    ).fetchone()
                    if vr:
                        vehicle_type_i, vehicle_plate_i = vr[0] or '', vr[1] or ''
                except Exception:
                    pass
            # Insert warehouse_receipts
                conn.execute(
                    "INSERT INTO warehouse_receipts "
                    "(inbound_load_id, receipt_no, stage_no, receipt_date, jalali_date_text, "
                    " waybill_no, supplier_id, driver_id, vehicle_type, vehicle_plate, "
                    " stage_load_qty, delivered_qty, discrepancy_qty, freight_amount, "
                    " source_location, destination_location, warehouse_keeper_name, receiver_name, "
                    " receipt_status, description, print_html, created_by, created_at, total_qty, vat_amount, extra_costs) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (inbound_load_id, receipt_no, stage_no, operation_date,
                     jalali_date_display_from_iso(operation_date),
                     waybill_no, supplier_id, driver_id, vehicle_type_i, vehicle_plate_i,
                     stage_declared, stage_received, discrepancy, freight_amount,
                     source_location, destination_location, warehouse_keeper, receiver_name,
                     'CONFIRMED', notes, '', user_id, now_iso, total_amount, vat_amount, extra_costs)
                )
                receipt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Insert warehouse_receipt_items
                for idx, line in enumerate(lines, start=1):
                    pallet_id = line.get('pallet_id')
                    qty = self._safe_int(line.get('quantity', 0))
                    unit_price = self._safe_int(line.get('unit_price', '0'))
                    line_total = qty * unit_price
                    warehouse_id = line.get('warehouse_id')
                    if not warehouse_id:
                        default_wh = conn.execute(
                            "SELECT id FROM warehouses WHERE is_active = 1 LIMIT 1"
                        ).fetchone()
                        warehouse_id = default_wh[0] if default_wh else 1
                    conn.execute(
                        "INSERT INTO warehouse_receipt_items "
                        "(receipt_id, pallet_id, row_no, qty, unit_price, total_price, "
                        " warehouse_id, defect_description) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (receipt_id, pallet_id, idx, qty, unit_price, line_total,
                         warehouse_id, line.get('defect_notes', '') or '')
                    )

                # Insert inventory_transactions
                for line in lines:
                    pallet_id = line.get('pallet_id')
                    qty = self._safe_int(line.get('quantity', 0))
                    unit_price = self._safe_int(line.get('unit_price', '0'))
                    line_total = qty * unit_price
                    warehouse_id = line.get('warehouse_id')
                    if not warehouse_id:
                        default_wh = conn.execute(
                            "SELECT id FROM warehouses WHERE is_active = 1 LIMIT 1"
                        ).fetchone()
                        warehouse_id = default_wh[0] if default_wh else 1
                    conn.execute(
                        "INSERT INTO inventory_transactions "
                        "(transaction_date, transaction_type, reference_type, reference_id, "
                        " pallet_id, warehouse_id, qty_in, qty_out, "
                        " unit_price, total_price, description, created_at) "
                        "VALUES (?, 'IN','RECEIPT',?,?,?,?,?,?,?,?,?)",
                        (operation_date, receipt_id, pallet_id, warehouse_id, qty, 0,
                         unit_price, line_total, f'Receipt {receipt_no}', now_iso)
                    )

                # Update inbound_loads remaining
                current_remaining = conn.execute(
                    "SELECT remaining_qty FROM inbound_loads WHERE id = ?",
                    (inbound_load_id,)
                ).fetchone()[0]
                new_remaining = int(current_remaining) - received_qty_total
                new_status = 'COMPLETE' if new_remaining <= 0 else 'PARTIAL'
                conn.execute(
                    "UPDATE inbound_loads SET remaining_qty = ?, "
                    "       received_qty_total = COALESCE(received_qty_total,0) + ?, "
                    "       load_status = ? "
                    "WHERE id = ?",
                    (max(new_remaining, 0), received_qty_total, new_status, inbound_load_id)
                )

                # سند مالی رسید
                if total_amount > 0:
                    conn.execute(
                        "INSERT INTO financial_documents "
                        "(finance_no, operation_type, direction, "
                        " inbound_load_id, receipt_id, counterparty_person_id, "
                        " finance_date, total_amount, settled_amount, "
                        " status, description, created_at, created_by) "
                        "VALUES (?, 'INBOUND_RECEIPT', 'PAYABLE', ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)",
                        (receipt_no, inbound_load_id, receipt_id, supplier_id,
                         operation_date, total_amount, notes, now_iso, user_id)
                    )

                # سند مالی پس‌کرایه
                if freight_amount > 0:
                    freight_doc_no = f"{receipt_no}-FREIGHT"
                    conn.execute(
                        "INSERT INTO financial_documents "
                        "(finance_no, operation_type, direction, "
                        " inbound_load_id, receipt_id, counterparty_person_id, "
                        " finance_date, total_amount, settled_amount, "
                        " status, description, created_at, created_by) "
                        "VALUES (?, 'INBOUND_FREIGHT', 'PAYABLE', ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)",
                        (freight_doc_no, inbound_load_id, receipt_id, supplier_id,
                         operation_date, freight_amount, f'پس‌کرایه رسید {receipt_no}', now_iso, user_id)
                    )

                conn.commit()

                # تولید HTML برای پرینت
                lines_for_preview = []
                for idx, line in enumerate(lines, 1):
                    pallet_id = line.get('pallet_id')
                    qty = self._safe_int(line.get('quantity', 0))
                    unit_price = self._safe_int(line.get('unit_price', '0'))
                    line_total = qty * unit_price
                    warehouse_id = line.get('warehouse_id')
                    pallet_name = '-'
                    pallet_code = '-'
                    try:
                        pallet_row = conn.execute(
                            "SELECT code, name FROM pallets WHERE id = ?",
                            (pallet_id,)
                        ).fetchone()
                        if pallet_row:
                            pallet_code = pallet_row[0] or '-'
                            pallet_name = pallet_row[1] or '-'
                    except Exception:
                        pass
                    warehouse_name = '-'
                    try:
                        wh_row = conn.execute(
                            "SELECT name FROM warehouses WHERE id = ?",
                            (warehouse_id,)
                        ).fetchone()
                        if wh_row:
                            warehouse_name = wh_row[0] or '-'
                    except Exception:
                        pass
                    lines_for_preview.append({
                        'row_no': idx,
                        'pallet_code': pallet_code,
                        'pallet_name': pallet_name,
                        'quantity': qty,
                        'unit_price': unit_price,
                        'total_amount': line_total,
                        'warehouse_name': warehouse_name,
                        'defect_description': line.get('defect_notes', '-') or '-',
                    })

                # گرفتن اطلاعات خودرو از راننده
                vehicle_type = '-'
                vehicle_plate = '-'
                if driver_id:
                    try:
                        vehicle_row = conn.execute(
                            "SELECT COALESCE(vehicle_type, ''), COALESCE(vehicle_plate, '') "
                            "FROM driver_profiles WHERE person_id = ?",
                            (driver_id,)
                        ).fetchone()
                        if vehicle_row:
                            vehicle_type = vehicle_row[0] or '-'
                            vehicle_plate = vehicle_row[1] or '-'
                    except Exception:
                        pass

                _cum = _cumulative_receipt_delivered(conn, inbound_load_id, receipt_no, stage_no, stage_received)  # CUMDEL2
                _disc = int(total_declared or 0) - _cum  # CUMDEL2
                print_html = self.render_receipt_html({
                    'reference_no': ref_no,
                    'receipt_no': receipt_no,
                    'stage_no': stage_no,
                    'operation_date_iso': operation_date,
                    'operation_date_jalali': jalali_date_display_from_iso(operation_date),
                    'waybill_no': waybill_no or '-',
                    'supplier_name': self._supplier_name(supplier_id),
                    'driver_name': self._driver_name(driver_id),
                    'vehicle_type': vehicle_type,
                    'vehicle_plate': vehicle_plate,
                    'source_location': source_location or '-',
                    'destination_location': destination_location or '-',
                    'total_declared_qty': total_declared,
                    'stage_load_qty': stage_declared,
                    'delivered_qty': _cum,  # CUMDEL2
                    'discrepancy_qty': _disc,  # CUMDEL2
                    'freight_amount': freight_amount,
                    'lines_total_amount': lines_total_amount,
                    'vat_amount': vat_amount,
                    'extra_costs': extra_costs,
                    'warehouse_keeper_name': warehouse_keeper or '-',
                    'receiver_name': receiver_name or '-',
                    'notes': notes or '-',
                    'lines': lines_for_preview
                })

                # ذخیره HTML در دیتابیس
                try:
                    conn.execute(
                        "UPDATE warehouse_receipts SET print_html = ? WHERE id = ?",
                        (print_html, receipt_id),
                    )
                    conn.commit()
                except Exception:
                    pass

                return {
                    'receipt_id': receipt_id,
                    'receipt_no': receipt_no,
                    'reference_no': ref_no,
                    'print_html': print_html
                }

        # ---------------------------------------------------------------
        # List recent receipts
        # ---------------------------------------------------------------

    def list_receipt_tree(self):  # RECEIPT-TREE
        query = (
            "SELECT il.id, il.reference_no, COALESCE(il.total_load_qty,0), "
            "COALESCE((SELECT SUM(wri.qty) FROM warehouse_receipt_items wri "
            " JOIN warehouse_receipts wr0 ON wr0.id=wri.receipt_id "
            " WHERE wr0.inbound_load_id=il.id AND wr0.receipt_status!='CANCELLED'),0), "
            "wr.id, wr.receipt_no, wr.receipt_date, wr.receipt_status, "
            "COALESCE((SELECT SUM(wri.qty) FROM warehouse_receipt_items wri WHERE wri.receipt_id=wr.id),0), "
            "COALESCE(p.first_name||' '||p.last_name,'-'), COALESCE(d.first_name||' '||d.last_name,'-'), "
            "(SELECT GROUP_CONCAT(DISTINCT w.name) FROM warehouse_receipt_items wri2 "
            " LEFT JOIN warehouses w ON w.id=wri2.warehouse_id WHERE wri2.receipt_id=wr.id), "
            "il.register_date "
            "FROM inbound_loads il "
            "LEFT JOIN warehouse_receipts wr ON wr.inbound_load_id=il.id "
            "LEFT JOIN persons p ON p.id=il.supplier_id "
            "LEFT JOIN persons d ON d.id=il.driver_id "
            "ORDER BY il.reference_no, wr.receipt_date, wr.id"
        )
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(query).fetchall()
        return [{
            'load_id': r[0], 'mother_no': r[1], 'mother_total': int(r[2] or 0), 'mother_drawn': int(r[3] or 0),
            'receipt_id': r[4], 'receipt_no': r[5], 'receipt_date': r[6], 'receipt_status': r[7],
            'receipt_qty': int(r[8] or 0), 'supplier': r[9], 'driver': r[10], 'warehouses': r[11],
            'register_date': r[12],
        } for r in rows]

    def list_recent_receipts(self) -> List[Dict[str, Any]]:
        """لیست آخرین حواله‌ها"""
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT il.id, il.reference_no, "
                "       COALESCE(p1.first_name || ' ' || p1.last_name, '-') AS supplier_name, "
                "       COALESCE(p2.first_name || ' ' || p2.last_name, '-') AS driver_name, "
                "       il.total_load_qty, "
                "       COALESCE(il.received_qty_total, 0) AS delivered_qty, "
                "       il.remaining_qty, "
                "       COALESCE(il.waybill_no, '-') AS waybill_no "
                "FROM inbound_loads il "
                "LEFT JOIN persons p1 ON il.supplier_id = p1.id "
                "LEFT JOIN persons p2 ON il.driver_id = p2.id "
                "ORDER BY il.id DESC "
                "LIMIT 50"
            ).fetchall()
            return [
                {
                    'id': r[0], 'reference_no': r[1] or '-',
                    'supplier_name': r[2] or '-', 'driver_name': r[3] or '-',
                    'total_load_qty': r[4] or 0, 'delivered_qty': r[5] or 0,
                    'remaining_qty': r[6] or 0, 'waybill_no': r[7] or '-'
                }
                for r in rows
            ]

    def list_completed_receipts(self) -> List[Dict[str, Any]]:
        """لیست حواله‌های تکمیل‌شده"""
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT il.id, il.reference_no, il.total_load_qty, il.remaining_qty, "
                "       il.load_status, "
                "       COALESCE(p1.first_name || ' ' || p1.last_name, '-') AS supplier_name, "
                "       COALESCE(p2.first_name || ' ' || p2.last_name, '-') AS driver_name, "
                "       COALESCE((SELECT SUM(wri.qty) FROM warehouse_receipt_items wri "
                "                 JOIN warehouse_receipts wr ON wr.id = wri.receipt_id "
                "                 WHERE wr.inbound_load_id = il.id "
                "                 AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED'), 0) AS total_received, "
                "       COALESCE((SELECT SUM(wri.total_price) FROM warehouse_receipt_items wri "
                "                 JOIN warehouse_receipts wr ON wr.id = wri.receipt_id "
                "                 WHERE wr.inbound_load_id = il.id "
                "                 AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED'), 0) AS total_amount "
                "FROM inbound_loads il "
                "LEFT JOIN persons p1 ON il.supplier_id = p1.id "
                "LEFT JOIN persons p2 ON il.driver_id = p2.id "
                "WHERE il.remaining_qty <= 0 "
                "ORDER BY il.id DESC"
            ).fetchall()
            return [
                {
                    'id': r[0], 'reference_no': r[1] or '-',
                    'total_load_qty': r[2] or 0, 'remaining_qty': r[3] or 0,
                    'load_status': r[4] or '-', 'supplier_name': r[5] or '-',
                    'driver_name': r[6] or '-', 'total_received': r[7] or 0,
                    'total_amount': r[8] or 0
                }
                for r in rows
            ]

    # ---------------------------------------------------------------
    # Get receipt details
    # ---------------------------------------------------------------

    def get_receipt_items(self, receipt_id: int) -> List[Dict[str, Any]]:
        """آیتم‌های یک رسید"""
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT wri.row_no, p.code, p.name, wri.qty, wri.unit_price, "
                "       wri.total_price, COALESCE(w.name,'') AS warehouse_name, "
                "       COALESCE(wri.defect_description,'') AS defect_description "
                "FROM warehouse_receipt_items wri "
                "JOIN pallets p ON p.id = wri.pallet_id "
                "LEFT JOIN warehouses w ON w.id = wri.warehouse_id "
                "WHERE wri.receipt_id = ? ORDER BY wri.row_no",
                (receipt_id,)
            ).fetchall()
            return [
                {
                    'row_no': r[0], 'pallet_code': r[1] or '-', 'pallet_name': r[2] or '-',
                    'quantity': r[3] or 0, 'unit_price': r[4] or 0,
                    'total_amount': r[5] or 0, 'warehouse_name': r[6] or '-',
                    'defect_description': r[7] or '-'
                }
                for r in rows
            ]

    def get_completed_receipt_details(self, inbound_load_id: int) -> Optional[Dict[str, Any]]:
        """جزئیات کامل حواله (با ارزش افزوده و مخارج هر مرحله)"""
        with self.db.connect() as conn:
            conn.row_factory = None
            row = conn.execute(
                "SELECT il.id, il.reference_no, il.total_load_qty, il.remaining_qty, "
                "       COALESCE(p1.first_name || ' ' || p1.last_name, '-') AS supplier_name, "
                "       COALESCE(p2.first_name || ' ' || p2.last_name, '-') AS driver_name, "
                "       COALESCE(il.waybill_no, '-') AS waybill_no, "
                "       COALESCE(il.source_location, '-') AS source_location, "
                "       COALESCE(il.destination_location, '-') AS destination_location "
                "FROM inbound_loads il "
                "LEFT JOIN persons p1 ON il.supplier_id = p1.id "
                "LEFT JOIN persons p2 ON il.driver_id = p2.id "
                "WHERE il.id = ?",
                (inbound_load_id,)
            ).fetchone()
            if not row:
                return None

            receipts = conn.execute(
                "SELECT wr.id, wr.receipt_no, wr.stage_no, wr.receipt_date, "
                "       COALESCE(wr.jalali_date_text, '') AS jalali_date_text, "
                "       COALESCE(wr.delivered_qty, 0) AS delivered_qty, "
                "       COALESCE(wr.total_qty, 0) AS total_amount, "
                "       COALESCE(wr.vat_amount, 0) AS vat_amount, "
                "       COALESCE(wr.extra_costs, 0) AS extra_costs, "
                "       wr.print_html, "
                "       COALESCE(wr.receipt_status, 'CONFIRMED') AS receipt_status "
                "FROM warehouse_receipts wr "
                "WHERE wr.inbound_load_id = ? "
                "ORDER BY wr.stage_no",
                (inbound_load_id,)
            ).fetchall()

            all_items = conn.execute(
                "SELECT wri.row_no, p.code, p.name, wri.qty, wri.unit_price, "
                "       wri.total_price, COALESCE(w.name,'') AS warehouse_name, "
                "       COALESCE(wri.defect_description,'') AS defect_description, "
                "       wr.receipt_no, wr.stage_no "
                "FROM warehouse_receipt_items wri "
                "JOIN pallets p ON p.id = wri.pallet_id "
                "LEFT JOIN warehouses w ON w.id = wri.warehouse_id "
                "JOIN warehouse_receipts wr ON wr.id = wri.receipt_id "
                "WHERE wr.inbound_load_id = ? "
                "AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED' "
                "ORDER BY wr.stage_no, wri.row_no",
                (inbound_load_id,)
            ).fetchall()

            items = [
                {
                    'row_no': r[0], 'pallet_code': r[1] or '-', 'pallet_name': r[2] or '-',
                    'quantity': r[3] or 0, 'unit_price': r[4] or 0,
                    'total_amount': r[5] or 0, 'warehouse_name': r[6] or '-',
                    'defect_description': r[7] or '-', 'receipt_no': r[8] or '-',
                    'stage_no': r[9] or 0
                }
                for r in all_items
            ]

            return {
                'id': row[0], 'reference_no': row[1] or '-',
                'total_load_qty': row[2] or 0, 'remaining_qty': row[3] or 0,
                'supplier_name': row[4] or '-', 'driver_name': row[5] or '-',
                'waybill_no': row[6] or '-', 'source_location': row[7] or '-',
                'destination_location': row[8] or '-',
                'stages': [
                    {'id': r[0], 'receipt_no': r[1], 'stage_no': r[2],
                     'receipt_date': r[3], 'jalali_date_text': r[4] or '',
                     'delivered_qty': r[5] or 0, 'total_amount': r[6] or 0,
                     'vat_amount': r[7] or 0, 'extra_costs': r[8] or 0,
                     'print_html': r[9] or '', 'receipt_status': r[10] or 'CONFIRMED'}
                    for r in receipts
                ],
                'items': items
            }

    def get_receipt(self, receipt_id: int) -> Optional[Dict[str, Any]]:
        """دریافت یک رسید"""
        with self.db.connect() as conn:
            conn.row_factory = None
            row = conn.execute(
                "SELECT wr.id, wr.receipt_no, "
                "       COALESCE(il.reference_no, '') AS reference_no, "
                "       wr.stage_no, wr.receipt_date, "
                "       wr.jalali_date_text, wr.supplier_id, wr.driver_id, "
                "       COALESCE(wr.vehicle_type, '') AS vehicle_type, "
                "       COALESCE(wr.vehicle_plate, '') AS vehicle_plate, "
                "       COALESCE(wr.source_location, '') AS source_location, "
                "       COALESCE(wr.destination_location, '') AS destination_location, "
                "       COALESCE(il.total_load_qty, 0) AS total_load_qty, "
                "       COALESCE(wr.delivered_qty, 0) AS delivered_qty, "
                "       COALESCE(wr.stage_load_qty, 0) AS stage_load_qty, "
                "       COALESCE(wr.receipt_status, 'CONFIRMED') AS receipt_status, "
                "       COALESCE(wr.description, '') AS description, "
                "       COALESCE(wr.print_html, '') AS print_html, "
                "       wr.created_by, "
                "       COALESCE(wr.total_qty, 0) AS total_qty, "
                "       COALESCE(wr.vat_amount, 0) AS vat_amount, "
                "       COALESCE(wr.extra_costs, 0) AS extra_costs, "
                "       COALESCE(il.remaining_qty, 0) AS inbound_remaining_qty, "
                "       COALESCE(il.id, 0) AS inbound_load_id "
                "FROM warehouse_receipts wr "
                "LEFT JOIN inbound_loads il ON wr.inbound_load_id = il.id "
                "WHERE wr.id = ?",
                (receipt_id,)
            ).fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'receipt_no': row[1], 'reference_no': row[2],
                'stage_no': row[3], 'receipt_date': row[4],
                'jalali_date_text': row[5], 'supplier_id': row[6],
                'driver_id': row[7], 'vehicle_type': row[8] or '',
                'vehicle_plate': row[9] or '', 'source_location': row[10] or '',
                'destination_location': row[11] or '',
                'total_load_qty': row[12], 'delivered_qty': row[13],
                'stage_load_qty': row[14], 'receipt_status': row[15],
                'description': row[16], 'print_html': row[17] or '',
                'created_by': row[18], 'total_qty': row[19],
                'vat_amount': row[20], 'extra_costs': row[21],
                'inbound_remaining_qty': row[22], 'inbound_load_id': row[23],
                'received_qty_total': row[13],
                'supplier_name': self._supplier_name(row[6]),
                'driver_name': self._driver_name(row[7])
            }

    # ---------------------------------------------------------------
    # Rollback (نسخه امن و اتمیک)
    # ---------------------------------------------------------------

    def _precheck_receipt_payments(self, conn, receipt_id: int) -> None:
        """اگر رسید (یا اسناد مالی‌اش) پرداخت وصول‌شده داشته باشد، خطا می‌دهد."""
        fin_docs = conn.execute(
            "SELECT id FROM financial_documents WHERE receipt_id = ? AND status <> 'CANCELLED'",
            (receipt_id,)
        ).fetchall()
        cleared_payments = []
        for fd in fin_docs:
            cleared = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM payment_entries "
                "WHERE financial_document_id = ? AND status = 'CLEARED'",
                (fd[0],)
            ).fetchone()
            if cleared and cleared[0] > 0:
                cleared_payments.append({'count': cleared[0], 'amount': cleared[1]})
        
        if cleared_payments:
            total_cleared = sum(p['amount'] for p in cleared_payments)
            total_count = sum(p['count'] for p in cleared_payments)
            raise ValidationError(
                f'این رسید دارای {total_count} پرداخت وصول‌شده '
                f'به مبلغ {total_cleared:,} ریال است.\n'
                f'ابتدا تسویه‌های سند مالی را برگردانید، سپس ابطال کنید.'
            )

    def _sync_inventory_levels_for_receipt(self, conn, receipt_id: int) -> None:
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
                    SELECT 1 FROM warehouse_receipt_items wri
                    WHERE wri.receipt_id = ?
                      AND wri.pallet_id   = inventory_levels.pallet_id
                      AND wri.warehouse_id = inventory_levels.warehouse_id
                )
            """, (receipt_id,))
        except Exception as e:
            print('[rollback] inventory_levels sync skipped:', str(e))

    def _mark_receipt_cancelled(self, conn, receipt_id: int,
                                user_id: Optional[int], reason: str) -> None:
        """علامت‌گذاری رسید به‌عنوان ابطال‌شده + ثبت زمان و کاربر (در صورت وجود فیلد)."""
        now_iso_str = datetime.now().isoformat()

        # ابطال وضعیت رسید
        conn.execute(
            "UPDATE warehouse_receipts SET receipt_status = 'CANCELLED' WHERE id = ?",
            (receipt_id,)
        )

        # تلاش برای ثبت cancelled_by / cancelled_at / cancel_reason (اگر ستون‌ها موجود باشند)
        for column, value in [
            ('cancelled_by', user_id),
            ('cancelled_at', now_iso_str),
            ('cancel_reason', reason or ''),
        ]:
            try:
                conn.execute(
                    f"UPDATE warehouse_receipts SET {column} = ? WHERE id = ?",
                    (value, receipt_id)
                )
            except Exception:
                pass  # ستون وجود ندارد؛ مشکلی نیست

    def _reverse_journals_for_docs(self, conn, doc_ids, user_id, reason):
        """ثبت سند برگشتی روزنامه (با تاریخ امروز) برای هر سند مالی"""
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


    def rollback_receipt(self, receipt_id: int, user_id: Optional[int] = None,
                         reason: str = '') -> Dict[str, Any]:
        """ابطال یک رسید (امن + اتمیک + سند برگشتی روزنامه + sync موجودی)"""
        with self.db.connect() as conn:
            conn.row_factory = None

            receipt = self.get_receipt(receipt_id)
            if not receipt:
                raise ValueError("رسید یافت نشد")
            if (receipt.get('receipt_status') or 'CONFIRMED') == 'CANCELLED':
                raise ValueError("این رسید قبلاً ابطال شده است")

            receipt_no = receipt['receipt_no']
            inbound_load_id = receipt.get('inbound_load_id')
            received_qty = int(receipt.get('received_qty_total') or receipt.get('delivered_qty') or 0)

            # 1) Pre-flight: بررسی پرداخت‌های وصول‌شده
            self._precheck_receipt_payments(conn, receipt_id)

            conn.execute("BEGIN IMMEDIATE")

            # 2) ثبت سند برگشتی روزنامه + ابطال اسناد مالی
            doc_ids = [r[0] for r in conn.execute(
                "SELECT id FROM financial_documents WHERE receipt_id = ? AND status <> 'CANCELLED'",
                (receipt_id,)
            ).fetchall()]
            self._reverse_journals_for_docs(conn, doc_ids, user_id, reason or f'ابطال امن رسید {receipt_no}')
            conn.execute(
                "UPDATE financial_documents SET status = 'CANCELLED' "
                "WHERE receipt_id = ? AND status <> 'CANCELLED'",
                (receipt_id,)
            )
            conn.execute(
                "UPDATE financial_documents SET status = 'CANCELLED' "
                "WHERE inbound_load_id = ? AND status <> 'CANCELLED'",
                (inbound_load_id,),
            )

            # 3) Void کردن تراکنش‌های ورودی
            conn.execute(
                "UPDATE inventory_transactions SET is_void = 1 "
                "WHERE reference_id = ? AND reference_type = 'RECEIPT' "
                "  AND transaction_type = 'IN' AND COALESCE(is_void, 0) = 0",
                (receipt_id,)
            )

            # 4) sync موجودی
            self._sync_inventory_levels_for_receipt(conn, receipt_id)

            # 5) ابطال رسید + audit
            rollback_reason = reason or f'ابطال امن رسید {receipt_no}'
            self._mark_receipt_cancelled(conn, receipt_id, user_id, rollback_reason)

            # 6) بازگشت مانده مرجع
            if inbound_load_id and received_qty > 0:
                row = conn.execute(
                    "SELECT total_load_qty, remaining_qty, received_qty_total "
                    "FROM inbound_loads WHERE id = ?",
                    (inbound_load_id,)
                ).fetchone()
                if row:
                    total_load = int(row[0] or 0)
                    current_remaining = int(row[1] or 0)
                    current_received = int(row[2] or 0)
                    new_remaining = current_remaining + received_qty
                    new_received = max(0, current_received - received_qty)
                    if new_remaining >= total_load:
                        new_status = 'OPEN'
                    elif new_remaining > 0:
                        new_status = 'PARTIAL'
                    else:
                        new_status = 'COMPLETE'
                    conn.execute(
                        "UPDATE inbound_loads SET remaining_qty = ?, received_qty_total = ?, load_status = ? WHERE id = ?",
                        (new_remaining, new_received, new_status, inbound_load_id)
                    )

            conn.commit()
            return {'receipt_no': receipt_no}

    def rollback_inbound_load(self, inbound_load_id: int,
                              user_id: Optional[int] = None,
                              reason: str = '') -> Dict[str, Any]:
        """ابطال کل حواله مادر (امن + اتمیک + pre-flight کامل + سند برگشتی)"""
        with self.db.connect() as conn:
            conn.row_factory = None

            receipts = conn.execute(
                "SELECT id, receipt_no, delivered_qty FROM warehouse_receipts "
                "WHERE inbound_load_id = ? AND COALESCE(receipt_status, 'CONFIRMED') <> 'CANCELLED'",
                (inbound_load_id,)
            ).fetchall()
            if not receipts:
                raise ValueError("هیچ رسید فعالی برای ابطال یافت نشد")

            # 1) Pre-flight کامل
            for receipt in receipts:
                self._precheck_receipt_payments(conn, receipt[0])

            conn.execute("BEGIN IMMEDIATE")

            rollback_reason = reason or f'ابطال امن حواله مادر {inbound_load_id}'

            # 2) حلقه ابطال
            for receipt in receipts:
                receipt_id = receipt[0]

                doc_ids = [r[0] for r in conn.execute(
                    "SELECT id FROM financial_documents WHERE receipt_id = ? AND status <> 'CANCELLED'",
                    (receipt_id,)
                ).fetchall()]
                self._reverse_journals_for_docs(conn, doc_ids, user_id, rollback_reason)
                conn.execute(
                    "UPDATE financial_documents SET status = 'CANCELLED' "
                    "WHERE receipt_id = ? AND status <> 'CANCELLED'",
                    (receipt_id,)
                )

                conn.execute(
                    "UPDATE inventory_transactions SET is_void = 1 "
                    "WHERE reference_id = ? AND reference_type = 'RECEIPT' "
                    "  AND transaction_type = 'IN' AND COALESCE(is_void, 0) = 0",
                    (receipt_id,)
                )

                self._sync_inventory_levels_for_receipt(conn, receipt_id)
                self._mark_receipt_cancelled(conn, receipt_id, user_id, rollback_reason)

            # 3) بازنشانی مرجع بار ورود
            conn.execute(
                "UPDATE inbound_loads SET remaining_qty = total_load_qty, "
                "   received_qty_total = 0, load_status = 'OPEN' WHERE id = ?",
                (inbound_load_id,)
            )

            conn.commit()
            return {'inbound_load_id': inbound_load_id, 'receipts_count': len(receipts)}

    # ---------------------------------------------------------------
    # ترمیم print_html برای رسیدهای قدیمی
    # ---------------------------------------------------------------

    def rebuild_print_html(self, receipt_id: int) -> bool:
        """ساخت مجدد print_html از داده‌های ذخیره‌شده (با ارزش افزوده و مخارج)"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT wr.id, wr.receipt_no, wr.stage_no, wr.receipt_date, "
                    "       COALESCE(wr.waybill_no, '-'), wr.supplier_id, wr.driver_id, "
                    "       COALESCE(wr.source_location, '-'), COALESCE(wr.destination_location, '-'), "
                    "       COALESCE(wr.stage_load_qty, 0), COALESCE(wr.delivered_qty, 0), "
                    "       COALESCE(wr.discrepancy_qty, 0), COALESCE(wr.freight_amount, 0), "
                    "       COALESCE(wr.warehouse_keeper_name, '-'), COALESCE(wr.receiver_name, '-'), "
                    "       COALESCE(wr.description, '-'), COALESCE(wr.total_qty, 0), "
                    "       COALESCE(wr.vat_amount, 0), COALESCE(wr.extra_costs, 0), "
                    "       COALESCE(il.reference_no, '-'), COALESCE(il.total_load_qty, 0) "
                    "FROM warehouse_receipts wr "
                    "LEFT JOIN inbound_loads il ON il.id = wr.inbound_load_id "
                    "WHERE wr.id = ?",
                    (receipt_id,),
                ).fetchone()
                if not row:
                    return False

                (rid, receipt_no, stage_no, receipt_date, waybill_no, supplier_id, driver_id,
                 source_location, destination_location, stage_load_qty, delivered_qty,
                 discrepancy_qty, freight_amount, warehouse_keeper, receiver_name, notes,
                 total_amount, vat_amount, extra_costs, reference_no, total_load_qty) = row

                vehicle_type, vehicle_plate = '-', '-'
                if driver_id:
                    vrow = conn.execute(
                        "SELECT COALESCE(vehicle_type, ''), COALESCE(vehicle_plate, '') "
                        "FROM driver_profiles WHERE person_id = ?", (driver_id,)
                    ).fetchone()
                    if vrow:
                        vehicle_type = vrow[0] or '-'
                        vehicle_plate = vrow[1] or '-'

                items = conn.execute(
                    "SELECT wri.row_no, p.code, p.name, wri.qty, wri.unit_price, "
                    "       wri.total_price, COALESCE(w.name, '-'), "
                    "       COALESCE(wri.defect_description, '-') "
                    "FROM warehouse_receipt_items wri "
                    "JOIN pallets p ON p.id = wri.pallet_id "
                    "LEFT JOIN warehouses w ON w.id = wri.warehouse_id "
                    "WHERE wri.receipt_id = ? ORDER BY wri.row_no",
                    (receipt_id,),
                ).fetchall()

                lines_for_preview = [
                    {
                        'row_no': it[0], 'pallet_code': it[1] or '-', 'pallet_name': it[2] or '-',
                        'quantity': it[3] or 0, 'unit_price': it[4] or 0, 'total_amount': it[5] or 0,
                        'warehouse_name': it[6] or '-', 'defect_description': it[7] or '-',
                    }
                    for it in items
                ]

                html = self.render_receipt_html({
                    'reference_no': reference_no,
                    'receipt_no': receipt_no,
                    'stage_no': stage_no,
                    'operation_date_iso': receipt_date,
                    'operation_date_jalali': jalali_date_display_from_iso(receipt_date) if receipt_date else '-',
                    'waybill_no': waybill_no or '-',
                    'supplier_name': self._supplier_name(supplier_id),
                    'driver_name': self._driver_name(driver_id),
                    'vehicle_type': vehicle_type,
                    'vehicle_plate': vehicle_plate,
                    'source_location': source_location or '-',
                    'destination_location': destination_location or '-',
                    'total_declared_qty': total_load_qty,
                    'stage_load_qty': stage_load_qty,
                    'delivered_qty': delivered_qty,
                    'discrepancy_qty': discrepancy_qty,
                    'freight_amount': freight_amount,
                    'lines_total_amount': total_amount,
                    'vat_amount': int(vat_amount or 0),
                    'extra_costs': int(extra_costs or 0),
                    'warehouse_keeper_name': warehouse_keeper or '-',
                    'receiver_name': receiver_name or '-',
                    'notes': notes or '-',
                    'lines': lines_for_preview,
                })
            # ─────────────────────────────────────────────────────────

                conn.execute(
                    "UPDATE warehouse_receipts SET print_html = ? WHERE id = ?",
                    (html, receipt_id),
                )
                conn.commit()
                return True
        except Exception:
            return False

    def backfill_print_html_for_load(self, inbound_load_id: int) -> int:
        """ترمیم print_html برای همه رسیدهای یک مرجع بار که HTML ندارند"""
        count = 0
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id FROM warehouse_receipts "
                    "WHERE inbound_load_id = ? AND (print_html IS NULL OR print_html = '') "
                    "AND COALESCE(receipt_status, 'CONFIRMED') <> 'CANCELLED'",
                    (inbound_load_id,),
                ).fetchall()
            for r in rows:
                if self.rebuild_print_html(r[0]):
                    count += 1
        except Exception:
            pass
        return count

    # ---------------------------------------------------------------
    # Render HTML
    # ---------------------------------------------------------------

    def render_receipt_html(self, context: Dict[str, Any]) -> str:
        try:  # COMPANY-FILTER
            from app.core.letterhead import get_filtered_company
            company = get_filtered_company(self.db)
        except Exception:
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
<html><head><meta charset="utf-8"><title>رسید ورودی انبار {receipt_no}</title></head>
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
<font size="4" color="#9333ea"><b>رسید ورودی انبار</b></font><br>
<font size="2" color="#334155">
<b>شماره:</b> {receipt_no}<br>
<b>مرجع بار:</b> {reference_no}<br>
<b>تاریخ:</b> {operation_date_jalali}<br>
<b>مرحله:</b> {stage_no}
</font></td></tr></table>
</td></tr></table>
<hr color="#9333ea" size="2">
<table dir="rtl" width="100%" cellspacing="0" cellpadding="8" border="1"><tr><td bgcolor="#fef3c7">
<font size="2">
<b>تأمین‌کننده:</b> {supplier_name} &nbsp;|&nbsp;
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
<td><font size="2">تعداد این مرحله: <b>{stage_load_qty:,}</b></font></td>
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
<td align="center"><br><br>____________________<br><font size="2">مهر و امضای تأمین‌کننده</font></td>
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
            receipt_no=context.get('receipt_no', '-'), reference_no=context.get('reference_no', '-'),
            stage_no=context.get('stage_no', 1),
            operation_date_jalali=context.get('operation_date_jalali', '-'),
            supplier_name=context.get('supplier_name', '-'), driver_name=context.get('driver_name', '-'),
            vehicle_type=context.get('vehicle_type', '-'), vehicle_plate=context.get('vehicle_plate', '-'),
            waybill_no=context.get('waybill_no', '-'), source_location=context.get('source_location', '-'),
            destination_location=context.get('destination_location', '-'), lines_html=lines_html,
            delivered_qty=int(context.get('delivered_qty', 0) or 0), lines_total_amount=lines_total_amount,
            vat_amount=vat_amount, extra_costs=extra_costs, final_total=total_amount,
            amount_words=amount_words, total_declared_qty=int(context.get('total_declared_qty', 0) or 0),
            stage_load_qty=int(context.get('stage_load_qty', 0) or 0),
            discrepancy_qty=int(context.get('discrepancy_qty', 0) or 0),
            freight_amount=int(context.get('freight_amount', 0) or 0),
            warehouse_keeper_name=context.get('warehouse_keeper_name', '-'),
            receiver_name=context.get('receiver_name', '-'), defect_table=defect_table, notes_box=notes_box)

    def render_completed_receipt_html(self, details) -> str:  # RECEIPT-RENDER-CLEAN
        items = details.get('items', []) or []
        stages = details.get('stages', []) or []
        rows = ''
        for i, it in enumerate(items, 1):
            rows += ('<tr><td>{}</td><td>{}</td><td>{}</td><td>{:,}</td><td>{:,}</td><td>{:,}</td><td>{}</td></tr>').format(
                i, it.get('pallet_code', '') or '-', it.get('pallet_name', '') or '-',
                int(it.get('quantity', 0) or 0), int(it.get('unit_price', 0) or 0),
                int(it.get('total_amount', 0) or 0), it.get('warehouse_name', '') or '-')
        from app.core.jalali import jalali_date_display_from_iso as _j
        srows = ''
        for st in stages:
            _d = st.get('receipt_date', '') or ''
            if _d and '-' in _d and '/' not in _d:
                try:
                    _d = _j(_d)
                except Exception:
                    pass
            _q = int(st.get('delivered_qty', 0) or st.get('quantity', 0) or 0)
            _a = int(st.get('total_amount', 0) or st.get('amount', 0) or 0)
            srows += ('<p style="margin:4px 0;">مرحله <b>{}</b>: {} | تاریخ: {} | تعداد: {:,} | مبلغ: {:,} ریال | {}</p>').format(
                st.get('stage_no', '') or '-', st.get('receipt_no', '') or '-', _d or '-', _q, _a,
                st.get('status', '') or '-')
        total_amount = sum(int(it.get('total_amount', 0) or 0) for it in items)
        total_qty = sum(int(it.get('quantity', 0) or 0) for it in items)
        return (
            '<h2>رسید مرحله‌ای بار</h2>'
            '<p>مرجع: <b>{ref}</b> | تأمین‌کننده: <b>{sup}</b> | راننده: <b>{drv}</b><br>'
            'بارنامه: <b>{way}</b> | مبدأ: <b>{src}</b> | مقصد: <b>{dst}</b><br>'
            'کل حواله: <b>{tq:,}</b></p>'
            '<h3>مراحل</h3>'
            '{srows}'
            '<h3>ردیف‌های پالت</h3>'
            '<table border="1" cellspacing="0" cellpadding="6" style="width:100%;border-collapse:collapse;">'
            '<thead><tr><th>ردیف</th><th>کد</th><th>نام</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ</th><th>انبار</th></tr></thead>'
            '<tbody>{rows}</tbody></table>'
            '<p style="margin-top:12px;"><b>تعداد کل: {tq:,} پالت</b> | <b>مبلغ کل: {ta:,} ریال</b></p>'
            '<p style="color:#888;font-size:11px;">این سند به صورت سیستمی تولید شده است</p>'
        ).format(ref=details.get('reference_no', '') or '-', sup=details.get('supplier_name', '') or '-',
                 drv=details.get('driver_name', '') or '-', way=details.get('waybill_no', '') or '-',
                 src=details.get('source_location', '') or '-', dst=details.get('destination_location', '') or '-',
                 tq=total_qty, ta=total_amount, rows=rows, srows=srows)


    @staticmethod
    def _safe_int(value: Any) -> int:
        """تبدیل امن به عدد"""
        try:
            return int(str(value).replace(',', '').replace(' ', ''))
        except (ValueError, TypeError):
            return 0

    def _supplier_name(self, supplier_id: Optional[int]) -> str:
        """نام تأمین‌کننده"""
        if not supplier_id:
            return '-'
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT first_name || ' ' || last_name FROM persons WHERE id = ?",
                    (supplier_id,)
                ).fetchone()
                return (row[0] or '-').strip() if row else '-'
        except Exception:
            return '-'

    def _driver_name(self, driver_id: Optional[int]) -> str:
        """نام راننده"""
        if not driver_id:
            return '-'
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT first_name || ' ' || last_name FROM persons WHERE id = ?",
                    (driver_id,)
                ).fetchone()
                return (row[0] or '-').strip() if row else '-'
        except Exception:
            return '-'

    def get_company_info(self) -> Dict[str, Any]:
        """اطلاعات شرکت برای سربرگ پرینت"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT company_name, phone, address, national_id, economic_code, "
                    "registration_number, ceo_name, website, email, mobile FROM company_profile LIMIT 1"
                ).fetchone()
                if row:
                    return {'company_name': row[0] or '', 'phone': row[1] or '', 'address': row[2] or '',
                            'national_id': row[3] or '', 'economic_code': row[4] or '',
                            'registration_number': row[5] or '', 'ceo_name': row[6] or '',
                            'website': row[7] or '', 'email': row[8] or '', 'mobile': row[9] or ''}
        except Exception:
            pass
        return {'company_name': 'نام شرکت', 'phone': '', 'address': '',
                'national_id': '', 'economic_code': '', 'registration_number': '',
                'ceo_name': '', 'website': '', 'email': '', 'mobile': ''}

    @staticmethod
    def _number_to_persian_words(number: int) -> str:
        """تبدیل عدد به حروف فارسی"""
        if number == 0:
            return 'صفر'

        ones = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه',
                'ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
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
            return 'منفی ' + ReceiptRepository._number_to_persian_words(-number)

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
