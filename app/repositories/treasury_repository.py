# -*- coding: utf-8 -*-
"""
Treasury Repository - اصلاح‌شده

⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
  [C4]  رفع باگ بحرانی حذف حساب: اگر حساب دارای گردش (treasury_transactions) باشد،
       دیگر DELETE واقعی نمی‌شود (قبلاً CASCADE کل تاریخچه را بی‌صدا پاک می‌کرد)
  [FIX] تعمیر کامل تخریب‌های کپی-پیست (سینتکس): __init__، _row_to_dict، <> و ...
  [NOTE] جدول هدف این ریپازیتوری همچنان treasury_accounts است (سازگار با schema و این UI)
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import DatabaseManager
from app.core.jalali import now_iso
from app.core.validators import ValidationError, validate_treasury_account_payload


class TreasuryRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        query = 'SELECT id FROM treasury_accounts WHERE code = ?'
        params: List[Any] = [code]
        if exclude_id is not None:
            query += ' AND id <> ?'
            params.append(exclude_id)
        query += ' LIMIT 1'
        with self.db.connect() as connection:
            return connection.execute(query, params).fetchone() is not None

    def list_accounts(self, search_text: str = '', active_filter: str = 'ALL') -> List[Dict[str, Any]]:
        filters = []
        params: List[Any] = []
        search_text = search_text.strip()
        if search_text:
            filters.append('(code LIKE ? OR name LIKE ? OR bank_name LIKE ? OR account_number LIKE ? OR iban LIKE ?)')
            like = f'%{search_text}%'
            params.extend([like, like, like, like, like])
        if active_filter == 'ACTIVE':
            filters.append('is_active = 1')
        elif active_filter == 'INACTIVE':
            filters.append('is_active = 0')
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''

        query = f'''
            SELECT id, code, name, account_type, bank_name, account_number, iban, card_number,
                   branch_name, branch_code, opening_balance, current_balance, is_active,
                   description, created_at, updated_at
            FROM treasury_accounts
            {where_clause}
            ORDER BY id DESC
        '''
        with self.db.connect() as connection:
            return [self._row_to_dict(row) for row in connection.execute(query, params).fetchall()]

    def list_active_accounts(self) -> List[Dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute(
                '''
                SELECT id, code, name, account_type, bank_name, current_balance
                FROM treasury_accounts
                WHERE is_active = 1
                ORDER BY account_type, name
                '''
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as connection:
            row = connection.execute('SELECT * FROM treasury_accounts WHERE id = ?', (account_id,)).fetchone()
            if not row:
                return None
            result = self._row_to_dict(row)
            txs = connection.execute(
                '''
                SELECT * FROM treasury_transactions
                WHERE treasury_account_id = ?
                ORDER BY id DESC
                LIMIT 100
                ''',
                (account_id,),
            ).fetchall()
            result['transactions'] = [self._row_to_dict(item) for item in txs]
            return result

    def create_account(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        data = validate_treasury_account_payload(payload)
        if self.code_exists(data['code']):
            raise ValidationError('کد صندوق / بانک تکراری است.')
        now = now_iso()
        with self.db.connect() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO treasury_accounts (
                    code, name, account_type, bank_name, account_number, iban, card_number,
                    branch_name, branch_code, opening_balance, current_balance, is_active,
                    description, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    data['code'], data['name'], data['account_type'], data['bank_name'], data['account_number'],
                    data['iban'], data['card_number'], data['branch_name'], data['branch_code'],
                    data['opening_balance'], data['opening_balance'], data['is_active'], data['description'], now, now,
                ),
            )
            account_id = int(cursor.lastrowid)
            if data['opening_balance'] > 0:
                balance_after = data['opening_balance']
                connection.execute(
                    '''
                    INSERT INTO treasury_transactions (
                        treasury_account_id, transaction_date, transaction_type, source_type, source_id,
                        amount, balance_after, description, created_at
                    ) VALUES (?, ?, 'IN', 'ADJUSTMENT', NULL, ?, ?, ?, ?)
                    ''',
                    (account_id, now[:10], data['opening_balance'], balance_after, 'موجودی اولیه', now),
                )
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='treasury_accounts',
                entity_id=str(account_id),
                action_name='CREATE',
                old_values=None,
                new_values=data,
            )
            connection.commit()
        return self.get_account(account_id) or {}

    def update_account(self, account_id: int, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        current = self.get_account(account_id)
        if not current:
            raise ValidationError('حساب صندوق / بانک یافت نشد.')
        data = validate_treasury_account_payload(payload)
        if self.code_exists(data['code'], exclude_id=account_id):
            raise ValidationError('کد صندوق / بانک تکراری است.')
        if int(data['opening_balance']) != int(current['opening_balance']):
            raise ValidationError('تغییر موجودی اولیه پس از ایجاد حساب مجاز نیست.')
        now = now_iso()
        with self.db.connect() as connection:
            connection.execute(
                '''
                UPDATE treasury_accounts
                SET code = ?, name = ?, account_type = ?, bank_name = ?, account_number = ?, iban = ?,
                    card_number = ?, branch_name = ?, branch_code = ?, is_active = ?, description = ?, updated_at = ?
                WHERE id = ?
                ''',
                (
                    data['code'], data['name'], data['account_type'], data['bank_name'], data['account_number'],
                    data['iban'], data['card_number'], data['branch_name'], data['branch_code'],
                    data['is_active'], data['description'], now, account_id,
                ),
            )
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='treasury_accounts',
                entity_id=str(account_id),
                action_name='UPDATE',
                old_values=current,
                new_values={**current, **data},
            )
            connection.commit()
        return self.get_account(account_id) or {}

    def delete_account(self, account_id: int, user_id: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        current = self.get_account(account_id)
        if not current:
            raise ValidationError('حساب صندوق / بانک یافت نشد.')
        with self.db.connect() as connection:
            has_payment_refs = connection.execute(
                'SELECT 1 FROM payment_entries WHERE treasury_account_id = ? LIMIT 1',
                (account_id,),
            ).fetchone() is not None
            # [C4] بررسی گردش (تراکنش) به‌جای فقط payment_entries
            has_transactions = connection.execute(
                'SELECT 1 FROM treasury_transactions WHERE treasury_account_id = ? LIMIT 1',
                (account_id,),
            ).fetchone() is not None

            # اگر حساب گردش مالی یا ارجاع پرداخت داشته باشد → فقط غیرفعال می‌شود
            # (قبلاً با DELETE واقعی، CASCADE تمام تاریخچهٔ treasury_transactions را پاک می‌کرد)
            if has_payment_refs or has_transactions:
                connection.execute(
                    'UPDATE treasury_accounts SET is_active = 0, updated_at = ? WHERE id = ?',
                    (now_iso(), account_id),
                )
                updated = {**current, 'is_active': 0}
                self.db.log_audit(
                    connection=connection,
                    user_id=user_id,
                    entity_name='treasury_accounts',
                    entity_id=str(account_id),
                    action_name='DEACTIVATE',
                    old_values=current,
                    new_values=updated,
                )
                connection.commit()
                return 'deactivated', updated

            # فقط حسابی که هیچ گردشی و هیچ ارجاعی ندارد واقعاً حذف می‌شود
            connection.execute('DELETE FROM treasury_accounts WHERE id = ?', (account_id,))
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='treasury_accounts',
                entity_id=str(account_id),
                action_name='DELETE',
                old_values=current,
                new_values=None,
            )
            connection.commit()
            return 'deleted', current
