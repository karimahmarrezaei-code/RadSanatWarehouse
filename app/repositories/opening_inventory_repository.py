import sqlite3
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_compact_from_iso, jalali_date_display_from_iso, now_iso, today_iso_date
from app.core.validators import ValidationError, validate_opening_inventory_payload


class OpeningInventoryRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def list_warehouses(self) -> List[Dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                'SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY name'
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def list_pallets(self) -> List[Dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                'SELECT id, code, name, material_type, length_cm, width_cm, height_cm FROM pallets WHERE is_active = 1 ORDER BY name'
            ).fetchall()
            results = []
            for row in rows:
                item = self._row_to_dict(row)
                item['dimensions'] = f"{item['length_cm']} × {item['width_cm']} × {item['height_cm']}"
                results.append(item)
            return results

    def next_opening_no(self, opening_date: Optional[str] = None) -> str:
        opening_date = opening_date or today_iso_date()
        date_part = jalali_date_compact_from_iso(opening_date)
        prefix = f'OP-{date_part}-'
        with self.db.connect() as connection:
            rows = connection.execute(
                'SELECT opening_no FROM opening_inventory_documents WHERE opening_no LIKE ? ORDER BY id DESC',
                (f'{prefix}%',),
            ).fetchall()
        max_seq = 0
        for row in rows:
            suffix = row['opening_no'].replace(prefix, '')
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))
        return f'{prefix}{max_seq + 1:04d}'

    def list_recent_openings(self, limit: int = 50) -> List[Dict[str, Any]]:
        query = '''
            SELECT oid.id, oid.opening_no, oid.opening_date, oid.document_status,
                   oid.total_types_count, oid.total_qty, oid.total_amount,
                   w.name AS warehouse_name
            FROM opening_inventory_documents oid
            JOIN warehouses w ON w.id = oid.warehouse_id
            ORDER BY oid.id DESC
            LIMIT ?
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query, (limit,)).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_opening_document(self, opening_document_id: int) -> Optional[Dict[str, Any]]:
        query = '''
            SELECT oid.*, w.code AS warehouse_code, w.name AS warehouse_name
            FROM opening_inventory_documents oid
            JOIN warehouses w ON w.id = oid.warehouse_id
            WHERE oid.id = ?
        '''
        with self.db.connect() as connection:
            row = connection.execute(query, (opening_document_id,)).fetchone()
            if not row:
                return None
            result = self._row_to_dict(row)
            items = connection.execute(
                '''
                SELECT oii.*, p.code AS pallet_code, p.name AS pallet_name, p.material_type,
                       p.length_cm, p.width_cm, p.height_cm
                FROM opening_inventory_items oii
                JOIN pallets p ON p.id = oii.pallet_id
                WHERE oii.opening_document_id = ?
                ORDER BY oii.row_no
                ''',
                (opening_document_id,),
            ).fetchall()
            result['items'] = [self._row_to_dict(item) for item in items]
            return result

    def create_opening_document(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        data = validate_opening_inventory_payload(payload)
        opening_no = self.next_opening_no(data['opening_date'])
        now = now_iso()
        with self.db.connect() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO opening_inventory_documents (
                    opening_no, opening_date, jalali_date_text, warehouse_id, document_status,
                    total_types_count, total_qty, total_amount, description,
                    created_by, created_at, confirmed_by, confirmed_at
                ) VALUES (?, ?, ?, ?, 'CONFIRMED', ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    opening_no,
                    data['opening_date'],
                    jalali_date_display_from_iso(data['opening_date']),
                    data['warehouse_id'],
                    data['total_types_count'],
                    data['total_qty'],
                    data['total_amount'],
                    data['description'],
                    user_id,
                    now,
                    user_id,
                    now,
                ),
            )
            opening_id = int(cursor.lastrowid)

            for row_no, line in enumerate(data['lines'], start=1):
                connection.execute(
                    '''
                    INSERT INTO opening_inventory_items (
                        opening_document_id, row_no, pallet_id, qty, unit_price, total_price, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        opening_id,
                        row_no,
                        line['pallet_id'],
                        line['qty'],
                        line['unit_price'],
                        line['total_price'],
                        line['description'],
                    ),
                )
                self._increase_inventory(connection, line['pallet_id'], data['warehouse_id'], line['qty'], now)

            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='opening_inventory_documents',
                entity_id=str(opening_id),
                action_name='CREATE_OPENING',
                old_values=None,
                new_values={'opening_no': opening_no, **data},
            )
            connection.commit()
        return self.get_opening_document(opening_id) or {}

    def _increase_inventory(self, connection: sqlite3.Connection, pallet_id: int, warehouse_id: int, quantity: int, updated_at: str) -> None:
        row = connection.execute(
            'SELECT id, quantity FROM inventory_levels WHERE pallet_id = ? AND warehouse_id = ? LIMIT 1',
            (pallet_id, warehouse_id),
        ).fetchone()
        if row:
            connection.execute(
                'UPDATE inventory_levels SET quantity = ?, updated_at = ? WHERE id = ?',
                (int(row['quantity']) + quantity, updated_at, row['id']),
            )
        else:
            connection.execute(
                'INSERT INTO inventory_levels (pallet_id, warehouse_id, quantity, updated_at) VALUES (?, ?, ?, ?)',
                (pallet_id, warehouse_id, quantity, updated_at),
            )

    def render_opening_html(self, document: Dict[str, Any]) -> str:
        def money(v: int) -> str:
            return f'{int(v):,} ریال'

        rows = ''.join(
            f"""
            <tr>
                <td>{idx}</td>
                <td>{item['pallet_code']}</td>
                <td>{item['pallet_name']}</td>
                <td>{item['material_type']}</td>
                <td>{int(item['qty']):,}</td>
                <td>{money(int(item['unit_price']))}</td>
                <td>{money(int(item['total_price']))}</td>
                <td>{item.get('description') or '-'}</td>
            </tr>
            """
            for idx, item in enumerate(document.get('items', []), start=1)
        )
        return f"""
        <html lang='fa' dir='rtl'>
        <head>
            <meta charset='utf-8'/>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; margin: 24px; direction: rtl; color: #0f172a; }}
                h1 {{ text-align:center; margin:0 0 12px 0; }}
                table {{ width:100%; border-collapse:collapse; margin-top:12px; }}
                th, td {{ border:1px solid #cbd5e1; padding:8px 10px; font-size:12px; text-align:center; }}
                th {{ background:#e2e8f0; }}
                .meta td {{ font-size:13px; }}
                .summary {{ margin-top:14px; }}
            </style>
        </head>
        <body>
            <h1>سند افتتاحیه انبار</h1>
            <table class='meta'>
                <tr><td>شماره سند</td><td>{document.get('opening_no') or '-'}</td><td>تاریخ</td><td>{document.get('jalali_date_text') or document.get('opening_date') or '-'}</td></tr>
                <tr><td>انبار</td><td>{document.get('warehouse_name') or '-'}</td><td>وضعیت</td><td>{document.get('document_status') or '-'}</td></tr>
                <tr><td>جمع انواع</td><td>{int(document.get('total_types_count') or 0)}</td><td>جمع تعداد</td><td>{int(document.get('total_qty') or 0):,}</td></tr>
                <tr><td>جمع مبلغ</td><td>{money(int(document.get('total_amount') or 0))}</td><td>توضیحات</td><td>{document.get('description') or '-'}</td></tr>
            </table>
            <table>
                <thead>
                    <tr><th>ردیف</th><th>کد پالت</th><th>نام پالت</th><th>جنس</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th><th>توضیح</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </body>
        </html>
        """
