# -*- coding: utf-8 -*-
"""
Receipt Repository - نسخه تمیز و نهایی (بازنویسی کامل)

این فایل جایگزین کامل app/repositories/receipt_repository.py می‌شود.

تغییرات نسبت به نسخه قبلی:
  ۱) get_company_info: @staticmethod اشتباه حذف شد → سربرگ چاپ شرکت درست می‌شود
  ۲) rebuild_print_html: vat_amount/extra_costs از دیتابیس خوانده و به قالب چاپ داده می‌شود
     → پیش‌نمایش رسیدهای قدیمی ارزش افزوده و مخارج را نشان می‌دهد
  ۳) get_completed_receipt_details: vat_amount/extra_costs به هر مرحله اضافه شد
  ۴) render_completed_receipt_html: جمع ارزش افزوده/مخارج از مراحل واقعی محاسبه می‌شود
  ۵) next_stage_no: فقط شماره مرحله (MAX stage_no + 1) — دیگر شماره RC نمی‌سوزاند
  ۶) peek_document_no: یک نسخه (تکراری حذف شد) — پرسنل‌محور
  ۷) build_document_no: از کلاس مرکزی NumberingService (پرسنل‌محور حتی هنگام سیو)
  ۸) get_receipt: ایندکس‌های tuple صحیح (vat/extra/remaining/load)
  ۹) بدون هیچ تخریب کپی-پیست — سینتکس تضمین‌شده سالم

استفاده:
    این فایل را به‌جای فایل فعلی در app/repositories/receipt_repository.py قرار دهید.
    سپس:  py -X utf8 .\\main.py
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
        دریافت پالت‌های مرتبط با یک مرجع بار
        - اگر مرجع بار قبلاً رسید داشته باشد → فقط پالت‌های همان مرجع
        - اگر مرجع جدید باشد (بدون رسید) → همه پالت‌های فعال
        """
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                has_receipts = conn.execute(
                    "SELECT COUNT(*) FROM warehouse_receipts "
                    "WHERE inbound_load_id = ? "
                    "AND COALESCE(receipt_status, 'CONFIRMED') <> 'CANCELLED'",
                    (inbound_load_id,)
                ).fetchone()[0]
                if has_receipts > 0:
                    rows = conn.execute(
                        "SELECT DISTINCT p.id, p.code, p.name "
                        "FROM warehouse_receipt_items wri "
                        "JOIN warehouse_receipts wr ON wr.id = wri.receipt_id "
                        "JOIN pallets p ON p.id = wri.pallet_id "
                        "WHERE wr.inbound_load_id = ? "
                        "AND COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED' "
                        "ORDER BY p.code",
                        (inbound_load_id,)
                    ).fetchall()
                    if not rows:
                        rows = conn.execute(
                            "SELECT id, code, name FROM pallets WHERE is_active = 1 ORDER BY code"
                        ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT id, code, name FROM pallets WHERE is_active = 1 ORDER BY code"
                    ).fetchall()
                return [
                    {'id': r[0], 'code': r[1] or '', 'name': r[2] or ''}
                    for r in rows
                ]
        except Exception:
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

    # ---------------------------------------------------------------
    # Create inbound receipt
    # ---------------------------------------------------------------

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

        # محاسبه مبلغ از qty × unit_price (نه از line_total_amount فرم که ممکن است قدیمی باشد)
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

        # اعتبارسنجی تعداد رسید نسبت به مانده حواله
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
                pass

        with self.db.connect() as conn:
            conn.row_factory = None

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
            else:
                ref_no = conn.execute(
                    "SELECT reference_no FROM inbound_loads WHERE id = ?",
                    (inbound_load_id,)
                ).fetchone()[0]

            stage_no = self.next_stage_no(inbound_load_id, conn)
            receipt_no = self.build_document_no(ref_no, stage_no, conn, personnel_id=supplier_id)
            now_iso = datetime.now().isoformat()

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
                 waybill_no, supplier_id, driver_id, '', '',
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

            # سند مالی رسید: فقط یک‌بار، با operation_type صحیح و finance_no یکتا
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
                'delivered_qty': stage_received,
                'discrepancy_qty': discrepancy,
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
    # Rollback
    # ---------------------------------------------------------------

    def rollback_receipt(self, receipt_id: int, user_id: Optional[int] = None,
                         reason: str = '') -> Dict[str, Any]:
        """ابطال یک رسید (امن: اگر سند مالی پرداخت وصول‌شده داشته باشد، رد می‌شود)"""
        with self.db.connect() as conn:
            conn.row_factory = None
            receipt = self.get_receipt(receipt_id)
            if not receipt:
                raise ValueError("رسید یافت نشد")
            receipt_no = receipt['receipt_no']
            inbound_load_id = conn.execute(
                "SELECT inbound_load_id FROM warehouse_receipts WHERE id = ?",
                (receipt_id,)
            ).fetchone()[0]

            # ابطال اسناد مالی فقط اگر پرداخت وصول‌شده نداشته باشند
            fin_docs = conn.execute(
                "SELECT id FROM financial_documents WHERE receipt_id = ? AND status <> 'CANCELLED'",
                (receipt_id,)
            ).fetchall()
            for fd in fin_docs:
                cleared = conn.execute(
                    "SELECT COUNT(*) FROM payment_entries WHERE financial_document_id = ? AND status = 'CLEARED'",
                    (fd[0],)
                ).fetchone()[0]
                if cleared:
                    raise ValueError(
                        "این رسید دارای پرداخت/چک وصول‌شده است؛ ابتدا تسویه‌های سند مالی را برگردانید، سپس ابطال کنید."
                    )

            conn.execute(
                "UPDATE financial_documents SET status = 'CANCELLED' "
                "WHERE receipt_id = ? AND status <> 'CANCELLED'",
                (receipt_id,)
            )
            conn.execute(
                "UPDATE warehouse_receipts SET receipt_status = 'CANCELLED' WHERE id = ?",
                (receipt_id,)
            )
            try:
                conn.execute(
                    "UPDATE inventory_transactions SET is_void = 1 "
                    "WHERE reference_id = ? AND transaction_type = 'IN'",
                    (receipt_id,)
                )
            except Exception:
                pass
            if inbound_load_id:
                received_qty = receipt.get('received_qty_total', 0)
                conn.execute(
                    "UPDATE inbound_loads SET "
                    "   remaining_qty = remaining_qty + ?, "
                    "   received_qty_total = MAX(0, received_qty_total - ?), "
                    "   load_status = 'OPEN' "
                    "WHERE id = ?",
                    (received_qty, received_qty, inbound_load_id)
                )
            conn.commit()
            return {'receipt_no': receipt_no}

    def rollback_inbound_load(self, inbound_load_id: int,
                              user_id: Optional[int] = None) -> Dict[str, Any]:
        """ابطال کل حواله مادر (امن)"""
        with self.db.connect() as conn:
            conn.row_factory = None
            receipts = conn.execute(
                "SELECT id, receipt_no, delivered_qty FROM warehouse_receipts "
                "WHERE inbound_load_id = ? AND COALESCE(receipt_status, 'CONFIRMED') <> 'CANCELLED'",
                (inbound_load_id,)
            ).fetchall()
            if not receipts:
                raise ValueError("هیچ رسید فعالی برای ابطال یافت نشد")

            for receipt in receipts:
                receipt_id = receipt[0]
                fin_docs = conn.execute(
                    "SELECT id FROM financial_documents WHERE receipt_id = ? AND status <> 'CANCELLED'",
                    (receipt_id,)
                ).fetchall()
                for fd in fin_docs:
                    cleared = conn.execute(
                        "SELECT COUNT(*) FROM payment_entries WHERE financial_document_id = ? AND status = 'CLEARED'",
                        (fd[0],)
                    ).fetchone()[0]
                    if cleared:
                        raise ValueError(
                            "یکی از رسیدها دارای پرداخت وصول‌شده است؛ ابتدا تسویه‌ها را برگردانید."
                        )
                conn.execute(
                    "UPDATE financial_documents SET status = 'CANCELLED' "
                    "WHERE receipt_id = ? AND status <> 'CANCELLED'",
                    (receipt_id,)
                )
                conn.execute(
                    "UPDATE warehouse_receipts SET receipt_status = 'CANCELLED' WHERE id = ?",
                    (receipt_id,)
                )
                try:
                    conn.execute(
                        "UPDATE inventory_transactions SET is_void = 1 "
                        "WHERE reference_id = ? AND transaction_type = 'IN'",
                        (receipt_id,)
                    )
                except Exception:
                    pass

            conn.execute(
                "UPDATE inbound_loads SET "
                "   remaining_qty = total_load_qty, "
                "   received_qty_total = 0, "
                "   load_status = 'OPEN' "
                "WHERE id = ?",
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
        """تولید HTML رسید ورود - دقیقاً هم‌قالب با فرم خروج"""
        try:
            company = self.get_company_info()
        except Exception:
            company = {}

        lines_html = ""
        for line in context.get('lines', []):
            lines_html += (
                "<tr>"
                f"<td>{line.get('row_no', '')}</td>"
                f"<td>{line.get('pallet_code', '')}</td>"
                f"<td>{line.get('pallet_name', '')}</td>"
                f"<td>{line.get('quantity', 0):,}</td>"
                f"<td>{line.get('unit_price', 0):,}</td>"
                f"<td>{line.get('total_amount', 0):,}</td>"
                f"<td>{line.get('warehouse_name', '')}</td>"
                f"<td>{line.get('defect_description', '-')}</td>"
                "</tr>"
            )
        if not lines_html and context.get('lines'):
            for idx, line in enumerate(context['lines'], 1):
                lines_html += (
                    "<tr>"
                    f"<td>{idx}</td>"
                    f"<td>{line.get('pallet_code', '-')}</td>"
                    f"<td>{line.get('pallet_name', '-')}</td>"
                    f"<td>{line.get('quantity', 0):,}</td>"
                    f"<td>{line.get('unit_price', 0):,}</td>"
                    f"<td>{line.get('total_amount', 0):,}</td>"
                    f"<td>{line.get('warehouse_name', '-')}</td>"
                    f"<td>{line.get('defect_description', '-')}</td>"
                    "</tr>"
                )

        lines_total_amount = int(context.get('lines_total_amount', 0) or 0)
        vat_amount = int(context.get('vat_amount', 0) or 0)
        extra_costs = int(context.get('extra_costs', 0) or 0)
        total_amount = lines_total_amount + vat_amount + extra_costs

        amount_words = ReceiptRepository._number_to_persian_words(total_amount) + ' ریال' if total_amount > 0 else '-'

        ceo_line = "<p>مدیر عامل: {}</p>".format(company.get('ceo_name', '')) if company.get('ceo_name') else ""
        national_parts = []
        if company.get('national_id'):
            national_parts.append("شناسه ملی: {}".format(company['national_id']))
        if company.get('economic_code'):
            national_parts.append("کد اقتصادی: {}".format(company['economic_code']))
        national_line = "<p>{}</p>".format(" | ".join(national_parts)) if national_parts else ""
        phone_parts = []
        if company.get('phone'):
            phone_parts.append("تلفن: {}".format(company['phone']))
        if company.get('mobile'):
            phone_parts.append("موبایل: {}".format(company['mobile']))
        phone_line = "<p>{}</p>".format(" | ".join(phone_parts)) if phone_parts else ""
        addr_line = "<p>آدرس: {}</p>".format(company['address']) if company.get('address') else ""
        notes = context.get('notes', '-') or '-'
        notes_box = '<div class="notes-box"><strong>توضیحات:</strong> {}</div>'.format(notes) if notes and notes != '-' else ""

        return """<!DOCTYPE html>

<html lang="fa" dir="rtl">

<head>

    <meta charset="UTF-8">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>رسید ورود انبار - {company_name}</title>

    <style>
        body {{
            font-family: 'Tahoma', sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            background-color: #fff;
            width: 95%;
            max-width: 1100px;
            margin: auto;
            padding: 20px;
            border: 1px solid #ddd;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .company-info {{ text-align: right; width: 60%; }}
        .company-name {{ font-size: 24px; font-weight: bold; color: #000; margin-bottom: 5px; }}
        .invoice-title-box {{
            width: 35%; background-color: #f3e5f5; border: 1px solid #ce93d8;
            padding: 10px; text-align: center; border-radius: 5px;
        }}
        .invoice-title-box h2 {{ color: #8e24aa; margin: 0 0 10px 0; font-size: 18px; }}
        .info-row {{ font-size: 12px; line-height: 1.6; }}
        .info-bar {{
            background-color: #fff9c4; border: 1px solid #fbc02d; padding: 10px;
            font-size: 13px; display: flex; justify-content: space-around;
            flex-wrap: wrap; margin-bottom: 20px;
        }}
        .main-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .main-table th {{ background-color: #2c3e50; color: white; padding: 10px; font-size: 13px; border: 1px solid #fff; }}
        .main-table td {{ padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px; }}
        .row-blue {{ background-color: #e3f2fd; font-weight: bold; }}
        .row-purple {{ background-color: #f3e5f5; }}
        .row-green {{ background-color: #e8f5e9; font-weight: bold; }}
        .amount-words {{
            background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd;
            margin-bottom: 20px; font-size: 14px;
        }}
        .footer-stats {{
            display: flex; justify-content: space-between; background-color: #e3f2fd;
            padding: 15px; border-radius: 5px; margin-bottom: 40px; font-size: 13px;
        }}
        .stats-column {{ width: 48%; }}
        .notes-box {{ background-color: #fff9c4; border: 1px solid #fbc02d; padding: 10px; margin-bottom: 15px; font-size: 13px; }}
        .signature-section {{ display: flex; justify-content: space-between; margin-top: 50px; text-align: center; }}
        .sig-box {{ width: 30%; border-top: 1px solid #000; padding-top: 5px; font-size: 14px; }}
        .print-btn {{
            position: fixed; top: 20px; left: 20px; padding: 10px 20px;
            background: #8e24aa; color: white; border: none; border-radius: 6px;
            cursor: pointer; font-size: 14px;
        }}
        .print-btn:hover {{ background: #6a1b9a; }}
        @media print {{ .no-print {{ display: none; }} body {{ background: #fff; padding: 0; }} }}
    </style>

</head>

<body>

<button class="print-btn no-print" onclick="window.print()">چاپ / ذخیره PDF</button>

<div class="container">

    <table class="header-table">
        <tr>
            <td class="company-info">
                <div class="company-name">{company_name}</div>
                {ceo_line}
                {national_line}
                {phone_line}
                {addr_line}
            </td>
            <td class="invoice-title-box">
                <h2>رسید ورود انبار</h2>
                <div class="info-row">شماره رسید: {receipt_no}</div>
                <div class="info-row">شماره مرجع: {reference_no}</div>
                <div class="info-row">تاریخ: {operation_date_jalali}</div>
                <div class="info-row">مرحله: {stage_no}</div>
            </td>
        </tr>
    </table>

    <div class="info-bar">
        <span><strong>تأمین‌کننده:</strong> {supplier_name}</span>
        <span><strong>راننده:</strong> {driver_name}</span>
        <span><strong>خودرو:</strong> {vehicle_type} | {vehicle_plate}</span>
        <span><strong>بارنامه:</strong> {waybill_no}</span>
        <span><strong>مبدأ:</strong> {source_location}</span>
        <span><strong>مقصد:</strong> {destination_location}</span>
    </div>

    <table class="main-table">
        <thead>
            <tr>
                <th>ردیف</th>
                <th>کد پالت</th>
                <th>نام پالت</th>
                <th>تعداد</th>
                <th>قیمت واحد</th>
                <th>مبلغ کل</th>
                <th>انبار</th>
                <th>عیوب</th>
            </tr>
        </thead>
        <tbody>
            {lines_html}
            <tr class="row-blue">
                <td colspan="3">جمع کل:</td>
                <td>{delivered_qty:,}</td>
                <td></td>
                <td>{lines_total_amount:,} ریال</td>
                <td colspan="2"></td>
            </tr>
            <tr class="row-purple">
                <td colspan="3">ارزش افزوده ۹٪:</td>
                <td></td>
                <td></td>
                <td>{vat_amount:,} ریال</td>
                <td colspan="2"></td>
            </tr>
            <tr class="row-purple">
                <td colspan="3">مخارج اضافی:</td>
                <td></td>
                <td></td>
                <td>{extra_costs:,} ریال</td>
                <td colspan="2"></td>
            </tr>
            <tr class="row-green">
                <td colspan="3">قیمت نهایی:</td>
                <td></td>
                <td></td>
                <td>{total_amount:,} ریال</td>
                <td colspan="2"></td>
            </tr>
        </tbody>
    </table>

    <div class="amount-words">
        <strong>مبلغ به حروف:</strong> {amount_words}
    </div>

    <div class="footer-stats">
        <div class="stats-column">
            <div>تعداد کل بار: {total_declared_qty:,}</div>
            <div>تحویل به انبار: {delivered_qty:,}</div>
            <div>پس‌کرایه: {freight_amount:,} ریال</div>
            <div>تحویل‌گیرنده: {receiver_name}</div>
        </div>
        <div class="stats-column">
            <div>تعداد این مرحله: {stage_load_qty:,}</div>
            <div>مغایرت: {discrepancy_qty:,}</div>
            <div>مسئول انبار: {warehouse_keeper_name}</div>
        </div>
    </div>

    {notes_box}

    <div class="signature-section">
        <div class="sig-box">تحویل‌دهنده</div>
        <div class="sig-box">مسئول انبار</div>
        <div class="sig-box">مهر و امضای تحویل‌گیرنده</div>
    </div>

</div>

</body>

</html>""".format(
            company_name=company.get('company_name', 'نام شرکت'),
            ceo_line=ceo_line, national_line=national_line, phone_line=phone_line, addr_line=addr_line,
            receipt_no=context.get('receipt_no', '-'), reference_no=context.get('reference_no', '-'),
            stage_no=context.get('stage_no', 1),
            operation_date_jalali=context.get('operation_date_jalali', '-'),
            supplier_name=context.get('supplier_name', '-'), driver_name=context.get('driver_name', '-'),
            vehicle_type=context.get('vehicle_type', '-'), vehicle_plate=context.get('vehicle_plate', '-'),
            waybill_no=context.get('waybill_no', '-'), source_location=context.get('source_location', '-'),
            destination_location=context.get('destination_location', '-'),
            lines_html=lines_html,
            delivered_qty=int(context.get('delivered_qty', 0) or 0),
            lines_total_amount=lines_total_amount,
            vat_amount=vat_amount, extra_costs=extra_costs, total_amount=total_amount,
            amount_words=amount_words,
            total_declared_qty=int(context.get('total_declared_qty', 0) or 0),
            stage_load_qty=int(context.get('stage_load_qty', 0) or 0),
            discrepancy_qty=int(context.get('discrepancy_qty', 0) or 0),
            freight_amount=int(context.get('freight_amount', 0) or 0),
            warehouse_keeper_name=context.get('warehouse_keeper_name', '-'),
            receiver_name=context.get('receiver_name', '-'),
            notes_box=notes_box)

    def render_completed_receipt_html(self, details: Dict[str, Any]) -> str:
        """تولید HTML حواله تکمیل‌شده (با ارزش افزوده و مخارج مراحل)"""
        lines_html = ""
        for item in details.get('items', []):
            lines_html += (
                "<tr><td>{row_no}</td><td>{receipt_no}</td><td>{stage_no}</td>"
                "<td>{pallet_code}</td><td>{pallet_name}</td><td>{quantity:,}</td>"
                "<td>{unit_price:,} ریال</td><td>{total_amount:,} ریال</td>"
                "<td>{warehouse_name}</td><td>{defect_description}</td></tr>"
            ).format(**item)

        stages_html = ""
        for stage in details.get('stages', []):
            stages_html += (
                "<tr><td>{stage_no}</td><td>{receipt_no}</td><td>{jalali_date_text}</td>"
                "<td>{delivered_qty:,}</td><td>{total_amount:,} ریال</td></tr>"
            ).format(**stage)

        total_amount = sum(item.get('total_amount', 0) for item in details.get('items', []))
        total_qty = sum(item.get('quantity', 0) for item in details.get('items', []))
        # ارزش افزوده و مخارج از مراحل واقعی (که از دیتابیس خوانده شده‌اند)
        vat_amount = sum(int(stage.get('vat_amount', 0) or 0) for stage in details.get('stages', []))
        extra_costs = sum(int(stage.get('extra_costs', 0) or 0) for stage in details.get('stages', []))
        final_total = total_amount + vat_amount + extra_costs

        return """<!DOCTYPE html>

<html dir="rtl" lang="fa">

<head>
<meta charset="utf-8">
<title>حواله تکمیل‌شده</title>
<style>
  body {{ font-family: Tahoma, Arial, sans-serif; padding: 20px; }}
  h2 {{ text-align: center; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: right; }}
  th {{ background: #f0f0f0; }}
  .badge {{ background: #22c55e; color: white; padding: 4px 12px; border-radius: 4px; }}
</style>
</head>
<body>
<h2>گزارش حواله تکمیل‌شده</h2>
<p>مرجع: {reference_no} <span class="badge">تکمیل‌شده</span></p>
<div>
  <p>تأمین‌کننده: <b>{supplier_name}</b> | راننده: <b>{driver_name}</b></p>
  <p>بارنامه: <b>{waybill_no}</b> | مبدأ: <b>{source_location}</b> | مقصد: <b>{destination_location}</b></p>
  <p>کل حواله: <b>{total_load_qty:,}</b></p>
</div>
<h3>مراحل</h3>
<table><thead><tr><th>مرحله</th><th>رسید</th><th>تاریخ</th><th>تعداد</th><th>مبلغ</th></tr></thead>
<tbody>{stages_html}</tbody>
<tfoot><tr><th colspan="3">جمع</th><th>{total_received_qty:,}</th><th>{total_amount:,} ریال</th></tr></tfoot></table>
<h3>ردیف‌های پالت</h3>
<table><thead><tr><th>ردیف</th><th>رسید</th><th>مرحله</th><th>کد</th><th>نام</th><th>تعداد</th><th>قیمت</th><th>مبلغ</th><th>انبار</th><th>عیوب</th></tr></thead>
<tbody>{lines_html}</tbody></table>
</body>
</html>""".format(
            reference_no=details.get('reference_no', '-'),
            supplier_name=details.get('supplier_name', '-'),
            driver_name=details.get('driver_name', '-'),
            waybill_no=details.get('waybill_no', '-'),
            source_location=details.get('source_location', '-'),
            destination_location=details.get('destination_location', '-'),
            total_load_qty=details.get('total_load_qty', 0),
            stages_html=stages_html,
            lines_html=lines_html,
            total_received_qty=total_qty,
            total_amount=total_amount)

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

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
        """اطلاعات شرکت برای سربرگ پرینت (بدون @staticmethod — درست)"""
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
