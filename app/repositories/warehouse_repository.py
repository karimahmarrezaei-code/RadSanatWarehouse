import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import DatabaseManager
from app.core.jalali import now_iso
from app.core.validators import ValidationError, validate_warehouse_payload


class WarehouseRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        query = 'SELECT id FROM warehouses WHERE code = ?'
        params: List[Any] = [code]
        if exclude_id is not None:
            query += ' AND id <> ?'
            params.append(exclude_id)
        query += ' LIMIT 1'
        with self.db.connect() as connection:
            return connection.execute(query, params).fetchone() is not None

    def list_warehouses(self, search_text: str = '', active_filter: str = 'ALL') -> List[Dict[str, Any]]:
        filters = []
        params: List[Any] = []
        search_text = search_text.strip()

        if search_text:
            filters.append('(code LIKE ? OR name LIKE ? OR address LIKE ?)')
            like_value = f'%{search_text}%'
            params.extend([like_value, like_value, like_value])

        if active_filter == 'ACTIVE':
            filters.append('is_active = 1')
        elif active_filter == 'INACTIVE':
            filters.append('is_active = 0')

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''
        query = f'''
            SELECT id, code, name, capacity_count, address, is_active, created_at, updated_at
            FROM warehouses
            {where_clause}
            ORDER BY id DESC
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_warehouse(self, warehouse_id: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as connection:
            row = connection.execute('SELECT * FROM warehouses WHERE id = ?', (warehouse_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def create_warehouse(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        data = validate_warehouse_payload(payload)
        if self.code_exists(data['code']):
            raise ValidationError('کد انبار تکراری است.')

        now = now_iso()
        with self.db.connect() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO warehouses (
                    code, name, capacity_count, address, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    data['code'],
                    data['name'],
                    data['capacity_count'],
                    data['address'],
                    data['is_active'],
                    now,
                    now,
                ),
            )
            warehouse_id = int(cursor.lastrowid)
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='warehouses',
                entity_id=str(warehouse_id),
                action_name='CREATE',
                old_values=None,
                new_values=data,
            )
            connection.commit()
        return self.get_warehouse(warehouse_id) or {}

    def update_warehouse(self, warehouse_id: int, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        current = self.get_warehouse(warehouse_id)
        if not current:
            raise ValidationError('رکورد انتخاب شده پیدا نشد.')

        data = validate_warehouse_payload(payload)
        if self.code_exists(data['code'], exclude_id=warehouse_id):
            raise ValidationError('کد انبار تکراری است.')

        now = now_iso()
        with self.db.connect() as connection:
            connection.execute(
                '''
                UPDATE warehouses
                SET code = ?, name = ?, capacity_count = ?, address = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                ''',
                (
                    data['code'],
                    data['name'],
                    data['capacity_count'],
                    data['address'],
                    data['is_active'],
                    now,
                    warehouse_id,
                ),
            )
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='warehouses',
                entity_id=str(warehouse_id),
                action_name='UPDATE',
                old_values=current,
                new_values=data,
            )
            connection.commit()
        return self.get_warehouse(warehouse_id) or {}

    def delete_warehouse(self, warehouse_id: int, user_id: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        current = self.get_warehouse(warehouse_id)
        if not current:
            raise ValidationError('رکورد انتخاب شده پیدا نشد.')

        with self.db.connect() as connection:
            if self._has_references(connection, warehouse_id):
                updated_at = now_iso()
                connection.execute(
                    'UPDATE warehouses SET is_active = 0, updated_at = ? WHERE id = ?',
                    (updated_at, warehouse_id),
                )
                updated = {**current, 'is_active': 0, 'updated_at': updated_at}
                self.db.log_audit(
                    connection=connection,
                    user_id=user_id,
                    entity_name='warehouses',
                    entity_id=str(warehouse_id),
                    action_name='DEACTIVATE',
                    old_values=current,
                    new_values=updated,
                )
                connection.commit()
                return 'deactivated', updated

            try:
                connection.execute('DELETE FROM warehouses WHERE id = ?', (warehouse_id,))
                self.db.log_audit(
                    connection=connection,
                    user_id=user_id,
                    entity_name='warehouses',
                    entity_id=str(warehouse_id),
                    action_name='DELETE',
                    old_values=current,
                    new_values=None,
                )
                connection.commit()
                return 'deleted', current
            except sqlite3.IntegrityError as exc:
                raise ValidationError('حذف انبار به علت وابستگی سیستمی ممکن نیست.') from exc

    def _has_references(self, connection: sqlite3.Connection, warehouse_id: int) -> bool:
        checks = [
            'SELECT 1 FROM inventory_levels WHERE warehouse_id = ? LIMIT 1',
            'SELECT 1 FROM stock_document_lines WHERE warehouse_id = ? LIMIT 1',
            'SELECT 1 FROM stock_movements WHERE warehouse_id = ? LIMIT 1',
        ]
        for query in checks:
            if connection.execute(query, (warehouse_id,)).fetchone() is not None:
                return True
        return False
