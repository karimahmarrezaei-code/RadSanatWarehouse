from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import DatabaseManager
from app.core.jalali import now_iso
from app.core.validators import ValidationError, validate_person_payload


class PersonRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def national_id_exists(self, national_id: Optional[str], exclude_id: Optional[int] = None) -> bool:
        if not national_id:
            return False
        query = 'SELECT id FROM persons WHERE national_id = ?'
        params: List[Any] = [national_id]
        if exclude_id is not None:
            query += ' AND id <> ?'
            params.append(exclude_id)
        query += ' LIMIT 1'
        with self.db.connect() as connection:
            return connection.execute(query, params).fetchone() is not None

    def list_persons(
        self,
        search_text: str = '',
        role_filter: str = 'ALL',
        active_filter: str = 'ALL',
    ) -> List[Dict[str, Any]]:
        filters = []
        params: List[Any] = []
        search_text = search_text.strip()

        if search_text:
            filters.append(
                '(p.first_name LIKE ? OR p.last_name LIKE ? OR p.mobile LIKE ? OR p.national_id LIKE ? OR p.email LIKE ? OR p.city_name LIKE ? OR p.province_name LIKE ?)'
            )
            like = f'%{search_text}%'
            params.extend([like, like, like, like, like, like, like])

        if role_filter in {'CUSTOMER', 'SUPPLIER', 'DRIVER'}:
            filters.append('EXISTS (SELECT 1 FROM person_roles pr2 WHERE pr2.person_id = p.id AND pr2.role_type = ?)')
            params.append(role_filter)

        if active_filter == 'ACTIVE':
            filters.append('p.is_active = 1')
        elif active_filter == 'INACTIVE':
            filters.append('p.is_active = 0')

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''
        query = f'''
            SELECT
                p.id,
                p.national_id,
                p.first_name,
                p.last_name,
                p.mobile,
                p.email,
                p.province_name,
                p.city_name,
                p.is_active,
                p.created_at,
                p.updated_at,
                GROUP_CONCAT(pr.role_type, ',') AS roles_csv
            FROM persons p
            LEFT JOIN person_roles pr ON pr.person_id = p.id
            {where_clause}
            GROUP BY p.id
            ORDER BY p.id DESC
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                item = self._row_to_dict(row)
                item['roles'] = [role for role in (item.get('roles_csv') or '').split(',') if role]
                results.append(item)
            return results

    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as connection:
            row = connection.execute('SELECT * FROM persons WHERE id = ?', (person_id,)).fetchone()
            if not row:
                return None
            person = self._row_to_dict(row)
            roles = connection.execute(
                'SELECT role_type FROM person_roles WHERE person_id = ? ORDER BY id',
                (person_id,),
            ).fetchall()
            bank_rows = connection.execute(
                'SELECT * FROM bank_accounts WHERE person_id = ? ORDER BY is_default DESC, id ASC',
                (person_id,),
            ).fetchall()
            driver_row = connection.execute(
                'SELECT * FROM driver_profiles WHERE person_id = ? LIMIT 1',
                (person_id,),
            ).fetchone()
            person['roles'] = [role['role_type'] for role in roles]
            person['bank_accounts'] = [self._row_to_dict(item) for item in bank_rows]
            person['driver_profile'] = self._row_to_dict(driver_row) if driver_row else None
            return person

    def create_person(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        data = validate_person_payload(payload)
        if self.national_id_exists(data['national_id']):
            raise ValidationError('کد ملی تکراری است.')

        now = now_iso()
        with self.db.connect() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO persons (
                    national_id, first_name, last_name, mobile, email,
                    province_code, province_name, city_code, city_name,
                    address, notes, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    data['national_id'],
                    data['first_name'],
                    data['last_name'],
                    data['mobile'],
                    data['email'],
                    data['province_code'],
                    data['province_name'],
                    data['city_code'],
                    data['city_name'],
                    data['address'],
                    data['notes'],
                    data['is_active'],
                    now,
                    now,
                ),
            )
            person_id = int(cursor.lastrowid)
            self._save_related(connection, person_id, data, now)
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='persons',
                entity_id=str(person_id),
                action_name='CREATE',
                old_values=None,
                new_values=data,
            )
            connection.commit()
        return self.get_person(person_id) or {}

    def update_person(self, person_id: int, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        current = self.get_person(person_id)
        if not current:
            raise ValidationError('رکورد شخص یافت نشد.')

        data = validate_person_payload(payload)
        if self.national_id_exists(data['national_id'], exclude_id=person_id):
            raise ValidationError('کد ملی تکراری است.')

        now = now_iso()
        with self.db.connect() as connection:
            connection.execute(
                '''
                UPDATE persons
                SET national_id = ?, first_name = ?, last_name = ?, mobile = ?, email = ?,
                    province_code = ?, province_name = ?, city_code = ?, city_name = ?,
                    address = ?, notes = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                ''',
                (
                    data['national_id'],
                    data['first_name'],
                    data['last_name'],
                    data['mobile'],
                    data['email'],
                    data['province_code'],
                    data['province_name'],
                    data['city_code'],
                    data['city_name'],
                    data['address'],
                    data['notes'],
                    data['is_active'],
                    now,
                    person_id,
                ),
            )
            connection.execute('DELETE FROM person_roles WHERE person_id = ?', (person_id,))
            connection.execute('DELETE FROM bank_accounts WHERE person_id = ?', (person_id,))
            connection.execute('DELETE FROM driver_profiles WHERE person_id = ?', (person_id,))
            self._save_related(connection, person_id, data, now)
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='persons',
                entity_id=str(person_id),
                action_name='UPDATE',
                old_values=current,
                new_values=data,
            )
            connection.commit()
        return self.get_person(person_id) or {}

    def delete_person(self, person_id: int, user_id: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        current = self.get_person(person_id)
        if not current:
            raise ValidationError('رکورد شخص یافت نشد.')

        with self.db.connect() as connection:
            if self._has_references(connection, person_id):
                updated_at = now_iso()
                connection.execute(
                    'UPDATE persons SET is_active = 0, updated_at = ? WHERE id = ?',
                    (updated_at, person_id),
                )
                updated = {**current, 'is_active': 0, 'updated_at': updated_at}
                self.db.log_audit(
                    connection=connection,
                    user_id=user_id,
                    entity_name='persons',
                    entity_id=str(person_id),
                    action_name='DEACTIVATE',
                    old_values=current,
                    new_values=updated,
                )
                connection.commit()
                return 'deactivated', updated

            connection.execute('DELETE FROM persons WHERE id = ?', (person_id,))
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='persons',
                entity_id=str(person_id),
                action_name='DELETE',
                old_values=current,
                new_values=None,
            )
            connection.commit()
            return 'deleted', current

    def _save_related(
        self,
        connection: sqlite3.Connection,
        person_id: int,
        data: Dict[str, Any],
        now: str,
    ) -> None:
        for role in data['roles']:
            connection.execute(
                'INSERT INTO person_roles (person_id, role_type, created_at) VALUES (?, ?, ?)',
                (person_id, role, now),
            )

        if data['driver_profile']:
            connection.execute(
                '''
                INSERT INTO driver_profiles (
                    person_id, vehicle_type, vehicle_plate, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    person_id,
                    data['driver_profile']['vehicle_type'],
                    data['driver_profile']['vehicle_plate'],
                    data['driver_profile']['notes'],
                    now,
                ),
            )

        for bank_account in data['bank_accounts']:
            connection.execute(
                '''
                INSERT INTO bank_accounts (
                    person_id, bank_name, account_number, iban, card_number,
                    branch_name, branch_code, is_default, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    person_id,
                    bank_account['bank_name'],
                    bank_account['account_number'],
                    bank_account['iban'],
                    bank_account['card_number'],
                    bank_account['branch_name'],
                    bank_account['branch_code'],
                    bank_account['is_default'],
                    now,
                    now,
                ),
            )

    def _has_references(self, connection: sqlite3.Connection, person_id: int) -> bool:
        checks = [
            ('SELECT 1 FROM shipment_orders WHERE party_person_id = ? LIMIT 1', person_id),
            ('SELECT 1 FROM shipment_orders WHERE driver_person_id = ? LIMIT 1', person_id),
            ('SELECT 1 FROM payment_entries WHERE payer_payee_person_id = ? LIMIT 1', person_id),
            ('SELECT 1 FROM journal_lines WHERE person_id = ? LIMIT 1', person_id),
        ]
        for query, value in checks:
            if connection.execute(query, (value,)).fetchone() is not None:
                return True
        return False
