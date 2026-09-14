# -*- coding: utf-8 -*-
"""Report Repository - نسخه نهایی (افتتاحیه + موجودی لحظه‌ای + فیلتر is_void + دفتر روزنامه)"""

import sqlite3
from typing import Any, Dict, List, Optional
from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso


class ReportRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def list_active_warehouses(self) -> List[Dict[str, Any]]:
        query = '''
            SELECT id, code, name, capacity_count, address
            FROM warehouses
            WHERE is_active = 1
            ORDER BY code
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def list_active_pallets(self) -> List[Dict[str, Any]]:
        query = '''
            SELECT id, code, name, material_type, length_cm, width_cm, height_cm
            FROM pallets
            WHERE is_active = 1
            ORDER BY code
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query).fetchall()
            return [self._row_to_dict(row) for row in rows]

    # ================================================================
    # ارزش ریالی انبار (افتتاحیه + موجودی لحظه‌ای + فیلتر is_void)
    # ================================================================
    def get_warehouse_stock_value_report(self, warehouse_id: int) -> Dict[str, Any]:
        with self.db.connect() as connection:
            warehouse = connection.execute(
                'SELECT id, code, name FROM warehouses WHERE id = ? LIMIT 1',
                (warehouse_id,),
            ).fetchone()
            if not warehouse:
                raise ValueError('انبار یافت نشد')
            warehouse_info = self._row_to_dict(warehouse)

            query = '''
                SELECT
                    p.id AS pallet_id,
                    p.code AS pallet_code,
                    p.name AS pallet_name,
                    p.material_type,
                    p.length_cm,
                    p.width_cm,
                    p.height_cm,
                    COALESCE(SUM(it.qty_in), 0) AS total_in_qty,
                    COALESCE(SUM(it.qty_out), 0) AS total_out_qty,
                    COALESCE(
                        COALESCE(SUM(it.qty_in), 0) - COALESCE(SUM(it.qty_out), 0) + COALESCE(op.qty, 0)
                    , 0) AS current_qty,
                    COALESCE(SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END), 0) AS total_in_value,
                    COALESCE(SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END), 0) AS total_out_value,
                    COALESCE(
                        SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END)
                        - SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END)
                        + COALESCE(op.value, 0)
                    , 0) AS current_value,
                    MAX(it.transaction_date) AS last_transaction_date
                FROM pallets p
                LEFT JOIN inventory_transactions it
                    ON it.pallet_id = p.id
                    AND it.warehouse_id = ?
                    AND COALESCE(it.is_void, 0) = 0
                LEFT JOIN (
                    SELECT
                        oii.pallet_id,
                        SUM(oii.qty) AS qty,
                        CAST(SUM(CAST(oii.qty AS REAL) * CAST(oii.unit_price AS REAL)) AS REAL) AS value
                    FROM opening_inventory_items oii
                    JOIN opening_inventory_documents oid ON oii.opening_document_id = oid.id
                    WHERE oid.warehouse_id = ?
                    GROUP BY oii.pallet_id
                ) op ON op.pallet_id = p.id
                WHERE p.is_active = 1
                GROUP BY p.id
                HAVING
                    COALESCE(op.qty, 0) > 0
                    OR COALESCE(SUM(it.qty_in), 0) > 0
                    OR COALESCE(SUM(it.qty_out), 0) > 0
                    OR (COALESCE(SUM(it.qty_in), 0) - COALESCE(SUM(it.qty_out), 0) + COALESCE(op.qty, 0)) <> 0
                    OR (COALESCE(
                            SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END)
                            - SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END)
                        , 0) + COALESCE(op.value, 0)) <> 0
                ORDER BY p.name
            '''
            rows = connection.execute(query, (warehouse_id, warehouse_id)).fetchall()

        items: List[Dict[str, Any]] = []
        total_qty = 0
        total_value = 0
        pallet_type_count = 0
        for row in rows:
            item = self._row_to_dict(row)
            item['dimensions'] = f"{item['length_cm']} × {item['width_cm']} × {item['height_cm']}"
            items.append(item)
            current_qty = int(item.get('current_qty') or 0)
            current_value = int(item.get('current_value') or 0)
            total_qty += current_qty
            total_value += current_value
            if current_qty > 0 or current_value > 0:
                pallet_type_count += 1

        items.sort(key=lambda it: (it.get('pallet_code') or ''))
        return {
            'warehouse': warehouse_info,
            'items': items,
            'summary': {
                'total_qty': total_qty,
                'total_value': total_value,
                'pallet_type_count': pallet_type_count,
            },
        }

    # ================================================================
    # کاردکس انبار (با فیلتر is_void)
    # ================================================================
    def get_inventory_kardex_report(self, warehouse_id: int, pallet_id: Optional[int] = None) -> Dict[str, Any]:
        with self.db.connect() as connection:
            warehouse = connection.execute(
                'SELECT id, code, name, capacity_count, address FROM warehouses WHERE id = ? LIMIT 1',
                (warehouse_id,),
            ).fetchone()
            if not warehouse:
                raise ValueError('انبار یافت نشد')
            warehouse_info = self._row_to_dict(warehouse)

            pallet_info: Optional[Dict[str, Any]] = None
            params: List[Any] = [warehouse_id]
            pallet_filter_sql = ''
            if pallet_id is not None:
                pallet_row = connection.execute(
                    'SELECT id, code, name, material_type, length_cm, width_cm, height_cm FROM pallets WHERE id = ? LIMIT 1',
                    (pallet_id,),
                ).fetchone()
                if not pallet_row:
                    raise ValueError('پالت یافت نشد')
                pallet_info = self._row_to_dict(pallet_row)
                pallet_info['dimensions'] = f"{pallet_info['length_cm']} × {pallet_info['width_cm']} × {pallet_info['height_cm']}"
                pallet_filter_sql = ' AND it.pallet_id = ? '
                params.append(pallet_id)

            query = f'''
                SELECT
                    it.id,
                    it.transaction_date,
                    it.transaction_type,
                    it.reference_type,
                    it.reference_id,
                    it.pallet_id,
                    p.code AS pallet_code,
                    p.name AS pallet_name,
                    p.material_type,
                    it.warehouse_id,
                    w.code AS warehouse_code,
                    w.name AS warehouse_name,
                    it.qty_in,
                    it.qty_out,
                    it.unit_price,
                    it.total_price,
                    it.description,
                    wr.receipt_no,
                    wi.issue_no,
                    ir.reference_no AS inbound_reference_no,
                    ol.reference_no AS outbound_reference_no
                FROM inventory_transactions it
                JOIN pallets p ON p.id = it.pallet_id
                JOIN warehouses w ON w.id = it.warehouse_id
                LEFT JOIN warehouse_receipts wr ON it.reference_type = 'RECEIPT' AND wr.id = it.reference_id
                LEFT JOIN inbound_loads ir ON ir.id = wr.inbound_load_id
                LEFT JOIN warehouse_issues wi ON it.reference_type = 'ISSUE' AND wi.id = it.reference_id
                LEFT JOIN outbound_loads ol ON ol.id = wi.outbound_load_id
                WHERE it.warehouse_id = ?
                  AND COALESCE(it.is_void, 0) = 0
                {pallet_filter_sql}
                ORDER BY it.transaction_date, it.id
            '''
            rows = connection.execute(query, params).fetchall()

            opening_params: List[Any] = [warehouse_id]
            opening_filter_sql = ''
            if pallet_id is not None:
                opening_filter_sql = ' AND oii.pallet_id = ? '
                opening_params.append(pallet_id)
            opening_rows = connection.execute(f'''
                SELECT
                    oii.pallet_id,
                    oii.qty AS qty_in,
                    oii.unit_price,
                    oii.total_price,
                    p.code AS pallet_code,
                    p.name AS pallet_name
                FROM opening_inventory_items oii
                JOIN opening_inventory_documents oid ON oii.opening_document_id = oid.id
                JOIN pallets p ON p.id = oii.pallet_id
                WHERE oid.warehouse_id = ?
                 {opening_filter_sql}
                ORDER BY p.name
            ''', opening_params).fetchall()

        items: List[Dict[str, Any]] = []
        running_qty_per_pallet: Dict[int, int] = {}
        running_value_per_pallet: Dict[int, int] = {}

        for idx, row in enumerate(opening_rows, start=1):
            item = self._row_to_dict(row)
            item['transaction_type'] = 'OPENING'
            item['transaction_date'] = 'افتتاحیه'
            item['description'] = 'موجودی افتتاحیه'
            item['qty_out'] = 0
            item['reference_no'] = ''
            item['main_reference_no'] = ''
            item['row_no'] = idx
            pid = item.get('pallet_id')
            q_in = int(item.get('qty_in') or 0)
            v_in = int(item.get('total_price') or 0)
            running_qty_per_pallet[pid] = running_qty_per_pallet.get(pid, 0) + q_in
            running_value_per_pallet[pid] = running_value_per_pallet.get(pid, 0) + v_in
            item['running_qty'] = running_qty_per_pallet.get(pid, 0)
            item['running_value'] = running_value_per_pallet.get(pid, 0)
            items.append(item)

        for idx, row in enumerate(rows, start=len(items) + 1):
            item = self._row_to_dict(row)
            if item.get('transaction_date'):
                item['transaction_date'] = jalali_date_display_from_iso(item['transaction_date'])

            qty_in = int(item.get('qty_in') or 0)
            qty_out = int(item.get('qty_out') or 0)
            total_price = int(item.get('total_price') or 0)
            delta_qty = qty_in - qty_out
            delta_value = total_price if item.get('transaction_type') == 'IN' else -total_price

            pid = item.get('pallet_id')
            if pid is not None:
                running_qty_per_pallet[pid] = running_qty_per_pallet.get(pid, 0) + delta_qty
                running_value_per_pallet[pid] = running_value_per_pallet.get(pid, 0) + delta_value

            item['row_no'] = idx
            item['reference_no'] = item.get('receipt_no') or item.get('issue_no') or item.get('reference_no') or ''
            item['main_reference_no'] = item.get('inbound_reference_no') or item.get('outbound_reference_no') or item.get('reference_no') or ''
            item['running_qty'] = running_qty_per_pallet.get(pid, 0) if pid else 0
            item['running_value'] = running_value_per_pallet.get(pid, 0) if pid else 0
            items.append(item)

        # جابجایی/اصلاحیه = انتقال خنثی؛ فقط ورود/خروج واقعی شمارش می‌شود
        real = [i for i in items if (i.get('reference_type') or '') not in ('TRANSFER', 'ADJUST')]
        total_in_qty = sum(int(i.get('qty_in') or 0) for i in real)
        total_out_qty = sum(int(i.get('qty_out') or 0) for i in real)
        total_in_value = sum(int(i.get('total_price') or 0) for i in real if i.get('transaction_type') in ('IN', 'OPENING'))
        total_out_value = sum(int(i.get('total_price') or 0) for i in real if i.get('transaction_type') == 'OUT')
        current_qty_final = sum(running_qty_per_pallet.values())
        current_value_final = sum(running_value_per_pallet.values())

        summary = {
            'total_in_qty': total_in_qty,
            'total_out_qty': total_out_qty,
            'current_qty': current_qty_final,
            'total_in_value': total_in_value,
            'total_out_value': total_out_value,
            'current_value': current_value_final,
            'transaction_count': len(items),
        }
        items.sort(key=lambda it: (
            it.get('pallet_code') or '',
            0 if it.get('transaction_type') == 'OPENING' else 1,
            it.get('transaction_date') or '',
        ))
        for i, it in enumerate(items, 1):
            it['row_no'] = i
        return {
            'warehouse': warehouse_info,
            'pallet': pallet_info,
            'items': items,
            'summary': summary,
        }

    # ================================================================
    # ارزش ریالی همه انبارها (تجمیعی + فیلتر is_void)
    # ================================================================
    def get_all_warehouses_stock_value_report(self) -> Dict[str, Any]:
        with self.db.connect() as connection:
            warehouse_rows = connection.execute('''
                SELECT
                    w.id, w.code, w.name, w.capacity_count, w.address,
                    COALESCE(SUM(it.qty_in), 0) AS total_in_qty,
                    COALESCE(SUM(it.qty_out), 0) AS total_out_qty,
                    COALESCE(
                        COALESCE(SUM(it.qty_in), 0) - COALESCE(SUM(it.qty_out), 0) + COALESCE(op.qty, 0)
                    , 0) AS current_qty,
                    COALESCE(SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END), 0) AS total_in_value,
                    COALESCE(SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END), 0) AS total_out_value,
                    COALESCE(
                        SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END)
                        - SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END)
                        + COALESCE(op.value, 0)
                    , 0) AS current_value,
                    COUNT(DISTINCT CASE WHEN it.id IS NOT NULL THEN it.pallet_id END) AS pallet_type_count,
                    MAX(it.transaction_date) AS last_transaction_date
                FROM warehouses w
                LEFT JOIN inventory_transactions it
                    ON it.warehouse_id = w.id AND COALESCE(it.is_void, 0) = 0
                LEFT JOIN (
                    SELECT
                        oid.warehouse_id, oii.pallet_id,
                        SUM(oii.qty) AS qty,
                        CAST(SUM(CAST(oii.qty AS REAL) * CAST(oii.unit_price AS REAL)) AS REAL) AS value
                    FROM opening_inventory_items oii
                    JOIN opening_inventory_documents oid ON oii.opening_document_id = oid.id
                    GROUP BY oid.warehouse_id
                ) op ON op.warehouse_id = w.id
                WHERE w.is_active = 1
                GROUP BY w.id
                ORDER BY w.code
            ''').fetchall()

            pallet_rows = connection.execute('''
                SELECT
                    p.id AS pallet_id, p.code AS pallet_code, p.name AS pallet_name,
                    p.material_type, p.length_cm, p.width_cm, p.height_cm,
                    COALESCE(SUM(it.qty_in), 0) AS total_in_qty,
                    COALESCE(SUM(it.qty_out), 0) AS total_out_qty,
                    COALESCE(
                        COALESCE(SUM(it.qty_in), 0) - COALESCE(SUM(it.qty_out), 0) + COALESCE(oii.qty, 0)
                    , 0) AS current_qty,
                    COALESCE(SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END), 0) AS total_in_value,
                    COALESCE(SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END), 0) AS total_out_value,
                    COALESCE(
                        SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END)
                        - SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END)
                        + COALESCE(oii.value, 0)
                    , 0) AS current_value,
                    MAX(it.transaction_date) AS last_transaction_date
                FROM pallets p
                LEFT JOIN inventory_transactions it
                    ON it.pallet_id = p.id AND COALESCE(it.is_void, 0) = 0
                LEFT JOIN (
                    SELECT
                        oii.pallet_id,
                        SUM(oii.qty) AS qty,
                        CAST(SUM(CAST(oii.qty AS REAL) * CAST(oii.unit_price AS REAL)) AS REAL) AS value
                    FROM opening_inventory_items oii
                    GROUP BY oii.pallet_id
                ) oii ON oii.pallet_id = p.id
                WHERE p.is_active = 1
                GROUP BY p.id
                HAVING
                    COALESCE(oii.qty, 0) > 0
                    OR COALESCE(SUM(it.qty_in), 0) > 0
                    OR COALESCE(SUM(it.qty_out), 0) > 0
                    OR (COALESCE(SUM(it.qty_in), 0) - COALESCE(SUM(it.qty_out), 0) + COALESCE(oii.qty, 0)) <> 0
                    OR (COALESCE(
                            SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE 0 END)
                            - SUM(CASE WHEN it.transaction_type = 'OUT' THEN it.total_price ELSE 0 END)
                        , 0) + COALESCE(oii.value, 0)) <> 0
                ORDER BY p.name
            ''').fetchall()

        warehouses: List[Dict[str, Any]] = []
        total_qty = 0
        total_value = 0
        active_pallet_type_count = 0
        for row in warehouse_rows:
            item = self._row_to_dict(row)
            warehouses.append(item)
            total_qty += int(item.get('current_qty') or 0)
            total_value += int(item.get('current_value') or 0)
            active_pallet_type_count += int(item.get('pallet_type_count') or 0)

        pallets: List[Dict[str, Any]] = []
        for row in pallet_rows:
            item = self._row_to_dict(row)
            item['dimensions'] = f"{item['length_cm']} × {item['width_cm']} × {item['height_cm']}"
            pallets.append(item)

        return {
            'warehouses': warehouses,
            'pallets': pallets,
            'summary': {
                'warehouse_count': len(warehouses),
                'total_qty': total_qty,
                'total_value': total_value,
                'pallet_type_count': len(pallets),
            },
        }

    # ================================================================
    # 📔 دفتر روزنامه (جدید)
    # ================================================================
    def get_journal_report(self, date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           search_text: str = '') -> Dict[str, Any]:
        """خواندن اسناد دفتر روزنامه به همراه خطوط بدهکار/بستانکار"""
        with self.db.connect() as connection:
            filters: List[str] = []
            params: List[Any] = []
            if date_from:
                filters.append("je.entry_date >= ?"); params.append(date_from)
            if date_to:
                filters.append("je.entry_date <= ?"); params.append(date_to)
            if search_text:
                filters.append("(je.entry_no LIKE ? OR je.description LIKE ?)")
                params.extend([f'%{search_text}%'] * 2)
            where = f"WHERE {' AND '.join(filters)}" if filters else ''

            rows = connection.execute(f'''
                SELECT je.id, je.entry_no, je.entry_date, je.reference_type, je.description
                FROM journal_entries je
                {where}
                ORDER BY je.id DESC
            ''', params).fetchall()

            entries: List[Dict[str, Any]] = []
            total_debit = 0
            total_credit = 0
            for r in rows:
                lines = connection.execute('''
                    SELECT jl.line_no, COALESCE(la.code,'-'), COALESCE(la.name,'-'),
                           jl.debit_amount, jl.credit_amount, jl.description
                    FROM journal_lines jl
                    LEFT JOIN ledger_accounts la ON la.id = jl.account_id
                    WHERE jl.journal_entry_id = ?
                    ORDER BY jl.line_no
                ''', (r[0],)).fetchall()

                line_dicts = [
                    {'line_no': L[0], 'account_code': L[1], 'account_name': L[2],
                     'debit': int(L[3] or 0), 'credit': int(L[4] or 0), 'description': L[5] or ''}
                    for L in lines
                ]
                for L in line_dicts:
                    total_debit += L['debit']
                    total_credit += L['credit']

                entries.append({
                    'id': r[0], 'entry_no': r[1], 'entry_date': r[2],
                    'reference_type': r[3], 'description': r[4] or '', 'lines': line_dicts,
                })

            return {
                'entries': entries,
                'summary': {'count': len(entries), 'total_debit': total_debit, 'total_credit': total_credit},
            }