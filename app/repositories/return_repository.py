# -*- coding: utf-8 -*-
"""Return Repository - نسخه با ذخیره ریز اقلام و پشتیبانی گزارش"""

import sqlite3
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from app.core.jalali import now_iso, today_iso_date, jalali_date_display_from_iso
from app.core.validators import ValidationError
from app.repositories.company_repository import CompanyRepository


class ReturnRepository:

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.company_repository = CompanyRepository(db)
        self._ensure_return_items_table()

    # ------------------------------------------------------------------
    # 🆕 ساخت جدول ریز اقلام سند برگشتی (اگر نبود)
    # ------------------------------------------------------------------
    def _ensure_return_items_table(self) -> None:
        try:
            with self.db.connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS return_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        financial_document_id INTEGER NOT NULL,
                        smart_no TEXT NOT NULL,
                        return_type TEXT NOT NULL,           -- 'RECEIPT' یا 'ISSUE'
                        source_doc_id INTEGER NOT NULL,      -- شناسه سند مبدأ
                        source_doc_no TEXT,                  -- شماره سند مبدأ
                        row_no INTEGER NOT NULL,
                        pallet_id INTEGER NOT NULL,
                        pallet_code TEXT,
                        pallet_name TEXT,
                        qty INTEGER NOT NULL,
                        unit_price INTEGER NOT NULL DEFAULT 0,
                        total_price INTEGER NOT NULL DEFAULT 0,
                        warehouse_id INTEGER,
                        warehouse_name TEXT,
                        reason TEXT,
                        return_date TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (financial_document_id) REFERENCES financial_documents(id) ON DELETE CASCADE
                    )
                """)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_return_items_fd "
                    "ON return_items(financial_document_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_return_items_smart_no "
                    "ON return_items(smart_no)"
                )
                conn.commit()
        except Exception as exc:
            print(f'ensure return_items table error: {exc}')

    # ------------------------------------------------------------------
    # ثبت سند برگشتی
    # ------------------------------------------------------------------
    def register_return(self, doc_id: int, doc_type: str, items: List[Dict[str, Any]],
                        user_id: int, reason: str):
        now = now_iso()
        today = today_iso_date()

        # 🔒 قفل دورهٔ مالی
        from app.repositories.fiscal_period_repository import FiscalPeriodRepository
        locked = FiscalPeriodRepository(self.db).locked_period(today)
        if locked:
            raise ValidationError(
                f'تاریخ داخل دورهٔ بستهٔ «{locked["name"]}» است؛ ابتدا از تنظیمات، دوره را بازگشایی کنید.')

        with self.db.connect() as conn:
            # ۱. استخراج اطلاعات سند اصلی
            if doc_type == 'RECEIPT':
                orig = conn.execute(
                    'SELECT receipt_no as no, supplier_id as p_id '
                    'FROM warehouse_receipts WHERE id = ?',
                    (doc_id,)
                ).fetchone()
                prefix, op_type, direction = "BR-", "INBOUND_RECEIPT", "RECEIVABLE"
            else:
                orig = conn.execute(
                    'SELECT issue_no as no, customer_id as p_id '
                    'FROM warehouse_issues WHERE id = ?',
                    (doc_id,)
                ).fetchone()
                prefix, op_type, direction = "BS-", "OUTBOUND_ISSUE", "PAYABLE"

                        # ساخت شماره بر اساس پرسنل (مثل رسید/حواله): BR-1405-001-0001
            from app.core.sequence_utils import next_sequence_no
            person_id = orig['p_id']
            smart_no = next_sequence_no(
                conn, prefix.rstrip('-'), iso_date=today, personnel_id=person_id)
            total_amount = 0
            print_items = []
            enriched_items = []   # 🆕 برای ذخیره در return_items

            for item in items:
                table = "warehouse_receipt_items" if doc_type == 'RECEIPT' else "warehouse_issue_items"
                link_col = "receipt_id" if doc_type == 'RECEIPT' else "issue_id"

                orig_item = conn.execute(
                    f'SELECT unit_price FROM {table} WHERE {link_col} = ? AND pallet_id = ?',
                    (doc_id, item['pallet_id'])
                ).fetchone()

                unit_price = (orig_item['unit_price'] if orig_item and orig_item['unit_price'] is not None else 0)
                line_total = item['qty'] * unit_price
                total_amount += line_total

                t_type = 'IN' if doc_type == 'ISSUE' else 'OUT'
                qty_in = item['qty'] if t_type == 'IN' else 0
                qty_out = item['qty'] if t_type == 'OUT' else 0

                # ثبت در inventory_transactions
                conn.execute('''
                    INSERT INTO inventory_transactions (
                        transaction_date, transaction_type, reference_type, reference_id,
                        pallet_id, warehouse_id, qty_in, qty_out, unit_price, total_price,
                        description, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (today, t_type, doc_type, doc_id, item['pallet_id'],
                      item['warehouse_id'], qty_in, qty_out, unit_price, line_total,
                      f"برگشتی هوشمند مرجع {orig['no']}", now))

                # به‌روزرسانی inventory_levels
                qty_diff = item['qty'] if t_type == 'IN' else -item['qty']
                existing_level = conn.execute(
                    'SELECT id FROM inventory_levels WHERE pallet_id = ? AND warehouse_id = ?',
                    (item['pallet_id'], item['warehouse_id'])
                ).fetchone()

                if existing_level:
                    conn.execute(
                        'UPDATE inventory_levels SET quantity = quantity + ?, updated_at = ? '
                        'WHERE pallet_id = ? AND warehouse_id = ?',
                        (qty_diff, now, item['pallet_id'], item['warehouse_id'])
                    )
                else:
                    conn.execute(
                        'INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at) '
                        'VALUES (?, ?, ?, ?)',
                        (item['pallet_id'], item['warehouse_id'], qty_diff, now)
                    )

                pallet = conn.execute(
                    'SELECT name, code FROM pallets WHERE id = ?', (item['pallet_id'],)
                ).fetchone()

                # نام انبار
                wh_row = conn.execute(
                    'SELECT name FROM warehouses WHERE id = ?', (item['warehouse_id'],)
                ).fetchone()
                warehouse_name = wh_row['name'] if wh_row else '-'

                print_items.append({
                    'name': pallet['name'], 'code': pallet['code'],
                    'qty': item['qty'], 'price': unit_price, 'total': line_total
                })
                enriched_items.append({
                    'pallet_id': item['pallet_id'],
                    'pallet_code': pallet['code'],
                    'pallet_name': pallet['name'],
                    'qty': item['qty'],
                    'unit_price': unit_price,
                    'total_price': line_total,
                    'warehouse_id': item['warehouse_id'],
                    'warehouse_name': warehouse_name,
                })

            # ثبت سند مالی
            cur = conn.execute('''
                INSERT INTO financial_documents (
                    finance_no, operation_type, direction, receipt_id, issue_id,
                    counterparty_person_id, finance_date, total_amount, settled_amount,
                    status, description, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)
            ''', (smart_no, op_type, direction,
                  doc_id if doc_type == 'RECEIPT' else None,
                  doc_id if doc_type == 'ISSUE' else None,
                  orig['p_id'], today, total_amount, reason, now, user_id))
            financial_document_id = cur.lastrowid

            # 🆕 ذخیره ریز اقلام سند برگشتی
            for idx, it in enumerate(enriched_items, start=1):
                conn.execute('''
                    INSERT INTO return_items (
                        financial_document_id, smart_no, return_type, source_doc_id, source_doc_no,
                        row_no, pallet_id, pallet_code, pallet_name, qty, unit_price, total_price,
                        warehouse_id, warehouse_name, reason, return_date, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (financial_document_id, smart_no, doc_type, doc_id, orig['no'],
                      idx, it['pallet_id'], it['pallet_code'], it['pallet_name'],
                      it['qty'], it['unit_price'], it['total_price'],
                      it['warehouse_id'], it['warehouse_name'],
                      reason, today, now))

            # ── [ADD-FIX] مبلغ سند مالی برگشت = جمع اقلام ──
            try:
                if doc_type == 'ISSUE':
                    conn.execute("UPDATE financial_documents SET total_amount = ? "
                                 "WHERE issue_id = ? AND status = 'OPEN' AND finance_no NOT LIKE 'FN-%'",
                                 (total_amount, doc_id))
                else:
                    conn.execute("UPDATE financial_documents SET total_amount = ? "
                                 "WHERE receipt_id = ? AND status = 'OPEN' AND finance_no NOT LIKE 'FN-%'",
                                 (total_amount, doc_id))
            except Exception:
                pass
            # ── [ADD-NET] خالص‌سازی سند اصلی در برگشت از فروش ──
                if doc_type == 'ISSUE':
                    try:
                        total_return_qty = sum(int(it['qty'] or 0) for it in items)
                        for item in items:
                            conn.execute(
                                "UPDATE warehouse_issue_items SET qty = MAX(COALESCE(qty,0) - ?, 0) "
                                "WHERE issue_id = ? AND pallet_id = ?",
                                (int(item['qty'] or 0), doc_id, item['pallet_id']))
                            conn.execute(
                                "UPDATE warehouse_issues SET delivered_qty = MAX(COALESCE(delivered_qty,0) - ?, 0), "
                                "stage_load_qty = MAX(COALESCE(stage_load_qty,0) - ?, 0) WHERE id = ?",
                                (total_return_qty, total_return_qty, doc_id))
                            conn.execute(
                                "UPDATE financial_documents SET total_amount = MAX(COALESCE(total_amount,0) - ?, 0) "
                                "WHERE issue_id = ? AND operation_type = 'OUTBOUND_ISSUE' AND status <> 'CANCELLED'",
                                (total_amount, doc_id))
                            ol = conn.execute("SELECT outbound_load_id FROM warehouse_issues WHERE id = ?", (doc_id,)).fetchone()
                            if ol and ol[0]:
                                row = conn.execute("SELECT total_load_qty FROM outbound_loads WHERE id = ?", (ol[0],)).fetchone()
                                if row:
                                    dsum = conn.execute(
                                        "SELECT COALESCE(SUM(delivered_qty),0) FROM warehouse_issues "
                                        "WHERE outbound_load_id = ? AND issue_status != 'CANCELLED'", (ol[0],)).fetchone()[0]
                                    conn.execute(
                                        "UPDATE outbound_loads SET remaining_qty = MAX(? - ?, 0) WHERE id = ?",
                                        (int(row[0] or 0), int(dsum or 0), ol[0]))
                    except Exception as e:
                        print('[net] skipped:', str(e)[:120])
            conn.commit()

        person_name = '-'
        try:
            with self.db.connect() as _c2:
                _c2.row_factory = None
                _p = _c2.execute(
                    "SELECT first_name || ' ' || last_name FROM persons WHERE id = ?",
                    (orig['p_id'],)
                ).fetchone()
                if _p:
                    person_name = (_p[0] or '-').strip()
        except Exception:
            pass

        company_profile = {}
        try:
            company_profile = self.company_repository.get_company_profile()
        except Exception:
            try:
                company_profile = self.get_company_info()
            except Exception:
                company_profile = {}

        return {
            'smart_no': smart_no,
            'financial_document_id': financial_document_id,
            'orig_no': orig['no'],
            'type_label': "برگشت از فروش" if doc_type == 'ISSUE' else "برگشت از خرید",
            'person_name': person_name,
            'date': jalali_date_display_from_iso(today),
            'items': print_items,
            'total_amount': total_amount,
            'reason': reason,
            'company_profile': company_profile,
        }
    def get_return_items(self, financial_document_id: int) -> List[Dict[str, Any]]:
        """اقلام یک سند برگشتی از جدول return_items (اول)، fallback به inventory_transactions"""
        rows_out: List[Dict[str, Any]] = []
        try:
            with self.db.connect() as conn:
                rows = conn.execute("""
                    SELECT row_no, pallet_code, pallet_name, qty, unit_price,
                           total_price, warehouse_name
                    FROM return_items
                    WHERE financial_document_id = ?
                    ORDER BY row_no
                """, (financial_document_id,)).fetchall()

                if rows:
                    return [
                        {
                            'row_no': r['row_no'],
                            'pallet_code': r['pallet_code'] or '-',
                            'pallet_name': r['pallet_name'] or '-',
                            'qty': int(r['qty'] or 0),
                            'unit_price': int(r['unit_price'] or 0),
                            'total_price': int(r['total_price'] or 0),
                            'warehouse_name': r['warehouse_name'] or '-',
                        }
                        for r in rows
                    ]

                # ---------- Fallback برای اسناد قدیمی ----------
                fd = conn.execute(
                    "SELECT operation_type, receipt_id, issue_id, finance_no "
                    "FROM financial_documents WHERE id = ?",
                    (financial_document_id,)
                ).fetchone()
                if not fd:
                    return []

                is_receipt = fd['operation_type'] == 'INBOUND_RECEIPT'
                src_id = fd['receipt_id'] if is_receipt else fd['issue_id']
                ref_type = 'RECEIPT' if is_receipt else 'ISSUE'
                if not src_id:
                    return []

                # شماره سند مبدأ برای فیلتر description
                if is_receipt:
                    src_row = conn.execute(
                        "SELECT receipt_no FROM warehouse_receipts WHERE id = ?", (src_id,)
                    ).fetchone()
                else:
                    src_row = conn.execute(
                        "SELECT issue_no FROM warehouse_issues WHERE id = ?", (src_id,)
                    ).fetchone()
                src_no = src_row[0] if src_row else ''

                inv_rows = conn.execute("""
                    SELECT it.id, p.code AS pallet_code, p.name AS pallet_name,
                           (it.qty_in + it.qty_out) AS qty,
                           it.unit_price, it.total_price,
                           COALESCE(w.name, '-') AS warehouse_name
                    FROM inventory_transactions it
                    JOIN pallets p ON p.id = it.pallet_id
                    LEFT JOIN warehouses w ON w.id = it.warehouse_id
                    WHERE it.reference_type = ? AND it.reference_id = ?
                      AND it.description LIKE ?
                    ORDER BY it.id
                """, (ref_type, src_id, f'%{src_no}%')).fetchall()

                for idx, r in enumerate(inv_rows, start=1):
                    rows_out.append({
                        'row_no': idx,
                        'pallet_code': r['pallet_code'] or '-',
                        'pallet_name': r['pallet_name'] or '-',
                        'qty': int(r['qty'] or 0),
                        'unit_price': int(r['unit_price'] or 0),
                        'total_price': int(r['total_price'] or 0),
                        'warehouse_name': r['warehouse_name'] or '-',
                    })
        except Exception as exc:
            print(f'get_return_items error: {exc}')
        return rows_out

    # ------------------------------------------------------------------
    # 🆕 لیست اسناد برگشتی + خلاصه
    # ------------------------------------------------------------------
    def _source_doc_no_for(self, fd_id):
        """شماره سند مرجع (حواله فروش/رسید خرید) برای یک سند برگشت"""
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                row = conn.execute(
                    "SELECT source_doc_no FROM return_items "
                    "WHERE financial_document_id = ? LIMIT 1",
                    (fd_id,)
                ).fetchone()
                return row[0] if row and row[0] else "-"
        except Exception:
            return '-'

    def list_returns(self, date_from: Optional[str] = None, date_to: Optional[str] = None,
                     return_type: str = 'ALL', person_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        return_type: 'ALL' | 'PURCHASE' | 'SALE'
          PURCHASE  = برگشت از خرید (INBOUND_RECEIPT + direction=RECEIVABLE + finance_no LIKE 'PR-%')
          SALE      = برگشت از فروش (OUTBOUND_ISSUE + direction=PAYABLE + finance_no LIKE 'SR-%')
        """
        filters = ["(fd.finance_no LIKE 'BR-%' OR fd.finance_no LIKE 'BS-%')",
                   "fd.status <> 'CANCELLED'"]
        params: List[Any] = []

        if date_from and date_to:
            filters.append("fd.finance_date BETWEEN ? AND ?")
            params.extend([date_from, date_to])
        if return_type == 'PURCHASE':
            filters.append("fd.finance_no LIKE 'BR-%'")
        elif return_type == 'SALE':
            filters.append("fd.finance_no LIKE 'BS-%'")
        if person_id:
            filters.append("fd.counterparty_person_id = ?")
            params.append(person_id)

        query = f"""
            SELECT fd.id, fd.finance_no, fd.finance_date, fd.total_amount,
                   fd.description AS reason, fd.operation_type,
                   COALESCE(p.first_name || ' ' || p.last_name, '-') AS person_name
            FROM financial_documents fd
            LEFT JOIN persons p ON p.id = fd.counterparty_person_id
            WHERE {' AND '.join(filters)}
            ORDER BY fd.id DESC
        """
        rows_out: List[Dict[str, Any]] = []
        try:
            with self.db.connect() as conn:
                rows = conn.execute(query, params).fetchall()
                for r in rows:
                    is_purchase = (r['finance_no'] or '').startswith('BR-')
                    rows_out.append({
                        'id': r['id'],
                        'finance_no': r['finance_no'],
                        'finance_date': r['finance_date'],
                        'finance_date_jalali': jalali_date_display_from_iso(r['finance_date']) if r['finance_date'] else '',
                        'total_amount': int(r['total_amount'] or 0),
                        'reason': r['reason'] or '',
                        'person_name': r['person_name'] or '-',
                        'type_code': 'PURCHASE' if is_purchase else 'SALE',
                        'type_label': 'برگشت از خرید' if is_purchase else 'برگشت از فروش',
                        'source_doc_no': self._source_doc_no_for(r['id']),
                    })
        except Exception as exc:
            print(f'list_returns error: {exc}')
        return rows_out

    def get_returns_summary(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        purchase_count = sum(1 for r in rows if r['type_code'] == 'PURCHASE')
        sale_count = sum(1 for r in rows if r['type_code'] == 'SALE')
        total_amount = sum(int(r['total_amount'] or 0) for r in rows)
        return {
            'total_count': len(rows),
            'purchase_count': purchase_count,
            'sale_count': sale_count,
            'total_amount': total_amount,
        }

    def get_returns_daily_trend(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """گروه‌بندی بر اساس تاریخ برای نمودار روند"""
        buckets: Dict[str, Dict[str, int]] = {}
        for r in rows:
            key = r.get('finance_date') or ''
            if not key:
                continue
            bucket = buckets.setdefault(key, {'total': 0, 'purchase': 0, 'sale': 0, 'count': 0})
            amount = int(r['total_amount'] or 0)
            bucket['total'] += amount
            bucket['count'] += 1
            if r['type_code'] == 'PURCHASE':
                bucket['purchase'] += amount
            else:
                bucket['sale'] += amount
        return [
            {
                'date_iso': k,
                'date_jalali': jalali_date_display_from_iso(k),
                'total': v['total'],
                'purchase': v['purchase'],
                'sale': v['sale'],
                'count': v['count'],
            }
            for k, v in sorted(buckets.items())
        ]

    # ------------------------------------------------------------------
    # ساخت HTML سند برگشتی
    # ------------------------------------------------------------------
    def render_return_html(self, ctx: Dict[str, Any]) -> str:
        company = ctx.get('company_profile') or {}
        header_html = f"<h1>{company.get('company_name')}</h1>" if company.get('show_company_name') else ""
        details = []
        if company.get('show_phone'): details.append(f"تلفن: {company.get('phone')}")
        if company.get('show_address'): details.append(f"آدرس: {company.get('address')}")
        details_html = f"<div style='font-size:12px;'>{' | '.join(details)}</div>"

        line_rows = "".join([
            f"<tr><td>{i+1}</td><td>{item['code']}</td><td>{item['name']}</td>"
            f"<td>{item['qty']:,}</td><td>{item['price']:,}</td><td>{item['total']:,}</td></tr>"
            for i, item in enumerate(ctx['items'])
        ])

        return f"""
        <html lang='fa' dir='rtl'><head><meta charset='utf-8'>
        <style>
            body {{ font-family: Tahoma; direction: rtl; padding: 20px; }}
            .header {{ text-align: center; border-bottom: 2px solid #333; margin-bottom: 20px; padding-bottom:10px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #999; padding: 8px; text-align: center; font-size:12px; }}
            th {{ background: #eee; }}
        </style></head>
        <body>
            <div class='header'>{header_html}{details_html}<h3>سند اصلاحیه (برگشت کالا)</h3></div>
            <div style='display:flex; justify-content: space-between; margin-bottom:20px;'>
                <b>شماره: {ctx['smart_no']}</b>
                <b>تاریخ: {ctx['date']}</b>
            </div>
            <p>نوع: {ctx['type_label']} | طرف حساب: {ctx['person_name']}</p>
            <table>
                <thead><tr><th>ردیف</th><th>کد</th><th>نام پالت</th><th>تعداد</th><th>قیمت</th><th>جمع کل</th></tr></thead>
                <tbody>{line_rows}</tbody>
                <tfoot><tr><td colspan='5'>جمع کل (ریال)</td><td>{ctx['total_amount']:,}</td></tr></tfoot>
            </table>
            <p><b>علت:</b> {ctx['reason']}</p>
        </body>
        </html>
        """

    # ------------------------------------------------------------------
    # 🆕 ترمیم return_items برای اسناد برگشتی قدیمی (یک‌بار اجرا می‌شود)
    # ------------------------------------------------------------------
    def backfill_return_items(self) -> int:
        """برای اسناد برگشتی قدیمی که در return_items نیستند، از inventory_transactions می‌سازد"""
        count = 0
        try:
            with self.db.connect() as conn:
                docs = conn.execute("""
                    SELECT fd.id, fd.finance_no, fd.operation_type, fd.receipt_id, fd.issue_id,
                           fd.finance_date, fd.description
                    FROM financial_documents fd
                    WHERE (fd.finance_no LIKE 'BR-%' OR fd.finance_no LIKE 'BS-%')
                      AND NOT EXISTS (
                          SELECT 1 FROM return_items ri WHERE ri.financial_document_id = fd.id
                      )
                """).fetchall()

                for d in docs:
                    items = self.get_return_items(d['id'])   # از fallback می‌آید
                    if not items:
                        continue
                    is_receipt = d['operation_type'] == 'INBOUND_RECEIPT'
                    src_id = d['receipt_id'] if is_receipt else d['issue_id']
                    if is_receipt:
                        src_row = conn.execute(
                            "SELECT receipt_no FROM warehouse_receipts WHERE id = ?", (src_id,)
                        ).fetchone()
                    else:
                        src_row = conn.execute(
                            "SELECT issue_no FROM warehouse_issues WHERE id = ?", (src_id,)
                        ).fetchone()
                    src_no = src_row[0] if src_row else ''
                    now = now_iso()
                    for it in items:
                        # پیدا کردن pallet_id و warehouse_id از روی نام
                        pallet_row = conn.execute(
                            "SELECT id FROM pallets WHERE code = ? LIMIT 1", (it['pallet_code'],)
                        ).fetchone()
                        wh_row = conn.execute(
                            "SELECT id FROM warehouses WHERE name = ? LIMIT 1", (it['warehouse_name'],)
                        ).fetchone()
                        conn.execute("""
                            INSERT INTO return_items (
                                financial_document_id, smart_no, return_type, source_doc_id, source_doc_no,
                                row_no, pallet_id, pallet_code, pallet_name, qty, unit_price, total_price,
                                warehouse_id, warehouse_name, reason, return_date, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (d['id'], d['finance_no'], 'RECEIPT' if is_receipt else 'ISSUE',
                              src_id, src_no, it['row_no'],
                              pallet_row[0] if pallet_row else 0, it['pallet_code'], it['pallet_name'],
                              it['qty'], it['unit_price'], it['total_price'],
                              wh_row[0] if wh_row else None, it['warehouse_name'],
                              d['description'] or '', d['finance_date'], now))
                    count += 1
                conn.commit()
        except Exception as exc:
            print(f'backfill_return_items error: {exc}')
        return count