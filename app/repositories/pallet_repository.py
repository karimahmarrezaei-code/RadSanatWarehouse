import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import DatabaseManager
from app.core.jalali import now_iso
from app.core.validators import ValidationError, validate_pallet_payload


class PalletRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        query = 'SELECT id FROM pallets WHERE code = ?'
        params: List[Any] = [code]
        if exclude_id is not None:
            query += ' AND id <> ?'
            params.append(exclude_id)
        query += ' LIMIT 1'
        with self.db.connect() as connection:
            row = connection.execute(query, params).fetchone()
            return row is not None

    def list_pallets(self, search_text: str = '', active_filter: str = 'ALL') -> List[Dict[str, Any]]:
        filters = []
        params: List[Any] = []
        search_text = search_text.strip()

        if search_text:
            filters.append('(code LIKE ? OR name LIKE ? OR material_type LIKE ?)')
            like_value = f'%{search_text}%'
            params.extend([like_value, like_value, like_value])

        if active_filter == 'ACTIVE':
            filters.append('is_active = 1')
        elif active_filter == 'INACTIVE':
            filters.append('is_active = 0')

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''
        query = f'''
            SELECT
                id,
                code,
                name,
                material_type,
                length_cm,
                width_cm,
                height_cm,
                opening_stock,
                low_stock_threshold,
                image_path,
                description,
                is_active,
                created_at,
                updated_at
            FROM pallets
            {where_clause}
            ORDER BY id DESC
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_pallet(self, pallet_id: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as connection:
            row = connection.execute('SELECT * FROM pallets WHERE id = ?', (pallet_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def create_pallet(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        data = validate_pallet_payload(payload)
        if self.code_exists(data['code']):
            raise ValidationError('کد پالت تکراری است.')

        now = now_iso()
        with self.db.connect() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO pallets (
                    code, name, material_type, length_cm, width_cm, height_cm,
                    opening_stock, low_stock_threshold, image_path, description,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    data['code'],
                    data['name'],
                    data['material_type'],
                    data['length_cm'],
                    data['width_cm'],
                    data['height_cm'],
                    data['opening_stock'],
                    data['low_stock_threshold'],
                    data['image_path'],
                    data['description'],
                    data['is_active'],
                    now,
                    now,
                ),
            )
            pallet_id = cursor.lastrowid
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='pallets',
                entity_id=str(pallet_id),
                action_name='CREATE',
                old_values=None,
                new_values=data,
            )
            connection.commit()
        return self.get_pallet(int(pallet_id)) or {}

    def update_pallet(self, pallet_id: int, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        current = self.get_pallet(pallet_id)
        if not current:
            raise ValidationError('رکورد انتخاب شده پیدا نشد.')

        data = validate_pallet_payload(payload)
        if self.code_exists(data['code'], exclude_id=pallet_id):
            raise ValidationError('کد پالت تکراری است.')

        now = now_iso()
        with self.db.connect() as connection:
            connection.execute(
                '''
                UPDATE pallets
                SET code = ?, name = ?, material_type = ?, length_cm = ?, width_cm = ?,
                    height_cm = ?, opening_stock = ?, low_stock_threshold = ?, image_path = ?,
                    description = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                ''',
                (
                    data['code'],
                    data['name'],
                    data['material_type'],
                    data['length_cm'],
                    data['width_cm'],
                    data['height_cm'],
                    data['opening_stock'],
                    data['low_stock_threshold'],
                    data['image_path'],
                    data['description'],
                    data['is_active'],
                    now,
                    pallet_id,
                ),
            )
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='pallets',
                entity_id=str(pallet_id),
                action_name='UPDATE',
                old_values=current,
                new_values=data,
            )
            connection.commit()
        return self.get_pallet(pallet_id) or {}

    def delete_pallet(self, pallet_id: int, user_id: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        current = self.get_pallet(pallet_id)
        if not current:
            raise ValidationError('رکورد انتخاب شده پیدا نشد.')

        with self.db.connect() as connection:
            try:
                connection.execute('DELETE FROM pallets WHERE id = ?', (pallet_id,))
                self.db.log_audit(
                    connection=connection,
                    user_id=user_id,
                    entity_name='pallets',
                    entity_id=str(pallet_id),
                    action_name='DELETE',
                    old_values=current,
                    new_values=None,
                )
                connection.commit()
                return 'deleted', current
            except sqlite3.IntegrityError:
                updated_at = now_iso()
                connection.execute(
                    'UPDATE pallets SET is_active = 0, updated_at = ? WHERE id = ?',
                    (updated_at, pallet_id),
                )
                updated = {**current, 'is_active': 0, 'updated_at': updated_at}
                self.db.log_audit(
                    connection=connection,
                    user_id=user_id,
                    entity_name='pallets',
                    entity_id=str(pallet_id),
                    action_name='DEACTIVATE',
                    old_values=current,
                    new_values=updated,
                )
                connection.commit()
                return 'deactivated', updated
