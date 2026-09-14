# -*- coding: utf-8 -*-

"""
Finance Repository - نسخه نهایی با rollback امن

تغییرات اعمال‌شده:
  ✅ BEGIN IMMEDIATE برای جلوگیری از race condition
  ✅ پیام خطای دقیق با تعداد و مبلغ پرداخت‌های وصول‌شده
  ✅ ثبت cancelled_by / cancelled_at / cancel_reason (اگر ستون‌ها موجود باشند)
  ✅ شمارش پرداخت‌های ابطال‌شده در audit log
  ✅ یکپارچه‌سازی کامل روی treasury_accounts (C1)
  ✅ اصلاح باگ بحرانی: total_price → total_amount (C2)
  ✅ قفل چک‌های PENDING در محاسبه مانده (M1)
  ✅ چک با سررسید امروز/گذشته → CLEARED (CHECK-DUE)
"""

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from app.core.jalali import now_iso
from app.core.validators import ValidationError
from app.core.sequence_utils import next_sequence_no


class FinanceRepository:

    OPERATION_ACCOUNT_MAP = {
        'INBOUND_RECEIPT': ('1300', '2100'),
        'INBOUND_FREIGHT': ('5000', '2300'),
        'OUTBOUND_ISSUE': ('2200', '4000'),
        'OUTBOUND_FREIGHT': ('5000', '2300'),
    }

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def list_financial_documents(
        self,
        search_text: str = '',
        status_filter: str = 'ALL',
        direction_filter: str = 'ALL',
    ) -> List[Dict[str, Any]]:
        filters = []
        params: List[Any] = []
        search_text = search_text.strip()
        if search_text:
            filters.append(
                "(fd.finance_no LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR ir.reference_no LIKE ? OR orf.reference_no LIKE ? OR wr.receipt_no LIKE ? OR wi.issue_no LIKE ?)"
            )
            like = f'%{search_text}%'
            params.extend([like, like, like, like, like, like, like])
        if status_filter != 'ALL':
            filters.append('fd.status = ?')
            params.append(status_filter)
        if direction_filter != 'ALL':
            filters.append('fd.direction = ?')
            params.append(direction_filter)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''

        query = f'''
            SELECT fd.*, p.first_name || ' ' || p.last_name AS counterparty_name,
                   ir.reference_no AS inbound_reference_no,
                   orf.reference_no AS outbound_reference_no,
                   wr.receipt_no,
                   wi.issue_no
            FROM financial_documents fd
            LEFT JOIN persons p ON p.id = fd.counterparty_person_id
            LEFT JOIN inbound_loads ir ON ir.id = fd.inbound_load_id
            LEFT JOIN outbound_loads orf ON orf.id = fd.outbound_load_id
            LEFT JOIN warehouse_receipts wr ON wr.id = fd.receipt_id
            LEFT JOIN warehouse_issues wi ON wi.id = fd.issue_id
            {where_clause}
            ORDER BY fd.id DESC
        '''
        with self.db.connect() as connection:
            return [self._row_to_dict(row) for row in connection.execute(query, params).fetchall()]

    def get_financial_document(self, finance_id: int) -> Optional[Dict[str, Any]]:
        query = '''
            SELECT fd.*, p.first_name || ' ' || p.last_name AS counterparty_name,
                   ir.reference_no AS inbound_reference_no,
                   orf.reference_no AS outbound_reference_no,
                   wr.receipt_no,
                   wi.issue_no
            FROM financial_documents fd
            LEFT JOIN persons p ON p.id = fd.counterparty_person_id
            LEFT JOIN inbound_loads ir ON ir.id = fd.inbound_load_id
            LEFT JOIN outbound_loads orf ON orf.id = fd.outbound_load_id
            LEFT JOIN warehouse_receipts wr ON wr.id = fd.receipt_id
            LEFT JOIN warehouse_issues wi ON wi.id = fd.issue_id
            WHERE fd.id = ?
        '''
        with self.db.connect() as connection:
            row = connection.execute(query, (finance_id,)).fetchone()
            if not row:
                return None
            result = self._row_to_dict(row)
            payments = connection.execute(
                '''
                SELECT pe.*, pm.name AS payment_method_name, pm.code AS payment_method_code,
                       ca.name AS treasury_account_name
                FROM payment_entries pe
                JOIN payment_methods pm ON pm.id = pe.payment_method_id
                LEFT JOIN treasury_accounts ca ON ca.id = pe.treasury_account_id
                WHERE pe.financial_document_id = ?
                ORDER BY pe.id DESC
                ''',
                (finance_id,),
            ).fetchall()
            result['payments'] = [self._row_to_dict(item) for item in payments]
            return result

    def list_payment_methods(self) -> List[Dict[str, Any]]:
        with self.db.connect() as connection:
            rows = connection.execute('SELECT * FROM payment_methods ORDER BY id').fetchall()
            return [self._row_to_dict(row) for row in rows]

    def list_active_treasury_accounts(self) -> List[Dict[str, Any]]:
        """بارگذاری از treasury_accounts (یکپارچه‌سازی C1)"""
        with self.db.connect() as connection:
            rows = connection.execute(
                '''
                SELECT id, code, name, account_type, bank_name, account_number, current_balance, is_active
                FROM treasury_accounts
                WHERE is_active = 1
                ORDER BY account_type, name
                '''
            ).fetchall()
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'code': r[1],
                    'name': r[2],
                    'account_type': r[3],
                    'bank_name': r[4] or '',
                    'account_number': r[5] or '',
                    'current_balance': r[6] or 0,
                    'is_active': r[7],
                })
            return result

    def fetch_financial_overview(self) -> Dict[str, int]:
        query = '''
            SELECT
                COALESCE(SUM(CASE WHEN direction = 'RECEIVABLE' AND status <> 'CANCELLED' THEN total_amount ELSE 0 END), 0) AS receivable_total,
                COALESCE(SUM(CASE WHEN direction = 'RECEIVABLE' AND status <> 'CANCELLED' THEN settled_amount ELSE 0 END), 0) AS receivable_settled,
                COALESCE(SUM(CASE WHEN direction = 'PAYABLE' AND status <> 'CANCELLED' THEN total_amount ELSE 0 END), 0) AS payable_total,
                COALESCE(SUM(CASE WHEN direction = 'PAYABLE' AND status <> 'CANCELLED' THEN settled_amount ELSE 0 END), 0) AS payable_settled,
                COALESCE(SUM(CASE WHEN status IN ('OPEN', 'PARTIAL') THEN 1 ELSE 0 END), 0) AS open_docs,
                COALESCE(SUM(CASE WHEN status = 'SETTLED' THEN 1 ELSE 0 END), 0) AS settled_docs,
                COALESCE(COUNT(*), 0) AS total_docs
            FROM financial_documents
        '''
        with self.db.connect() as connection:
            row = connection.execute(query).fetchone()
            receivable_total = int(row['receivable_total']) if row else 0
            receivable_settled = int(row['receivable_settled']) if row else 0
            payable_total = int(row['payable_total']) if row else 0
            payable_settled = int(row['payable_settled']) if row else 0
            return {
                'receivable_total': receivable_total,
                'receivable_settled': receivable_settled,
                'receivable_balance': receivable_total - receivable_settled,
                'payable_total': payable_total,
                'payable_settled': payable_settled,
                'payable_balance': payable_total - payable_settled,
                'open_docs': int(row['open_docs']) if row else 0,
                'settled_docs': int(row['settled_docs']) if row else 0,
                'total_docs': int(row['total_docs']) if row else 0,
            }

    def list_person_financial_summaries(self, search_text: str = '') -> List[Dict[str, Any]]:
        filters = []
        params: List[Any] = []
        search_text = search_text.strip()
        if search_text:
            filters.append('(p.first_name LIKE ? OR p.last_name LIKE ? OR p.mobile LIKE ? OR p.national_id LIKE ?)')
            like = f'%{search_text}%'
            params.extend([like, like, like, like])
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''

        query = f'''
            SELECT
                p.id,
                p.first_name,
                p.last_name,
                p.mobile,
                p.national_id,
                (SELECT GROUP_CONCAT(role_type) FROM person_roles pr WHERE pr.person_id = p.id) AS roles_csv,
                COUNT(fd.id) AS docs_count,
                COALESCE(SUM(CASE WHEN fd.direction = 'RECEIVABLE' AND fd.status <> 'CANCELLED' THEN fd.total_amount ELSE 0 END), 0) AS receivable_total,
                COALESCE(SUM(CASE WHEN fd.direction = 'RECEIVABLE' AND fd.status <> 'CANCELLED' THEN fd.settled_amount ELSE 0 END), 0) AS receivable_settled,
                COALESCE(SUM(CASE WHEN fd.direction = 'PAYABLE' AND fd.status <> 'CANCELLED' THEN fd.total_amount ELSE 0 END), 0) AS payable_total,
                COALESCE(SUM(CASE WHEN fd.direction = 'PAYABLE' AND fd.status <> 'CANCELLED' THEN fd.settled_amount ELSE 0 END), 0) AS payable_settled
            FROM persons p
            LEFT JOIN financial_documents fd ON fd.counterparty_person_id = p.id
            {where_clause}
            GROUP BY p.id
            HAVING docs_count > 0
            ORDER BY p.first_name, p.last_name
        '''
        with self.db.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                item = self._row_to_dict(row)
                receivable_total = int(item['receivable_total'])
                receivable_settled = int(item['receivable_settled'])
                payable_total = int(item['payable_total'])
                payable_settled = int(item['payable_settled'])
                item['roles'] = [role for role in (item.get('roles_csv') or '').split(',') if role]
                item['receivable_balance'] = receivable_total - receivable_settled
                item['payable_balance'] = payable_total - payable_settled
                item['net_balance'] = item['receivable_balance'] - item['payable_balance']
                result.append(item)
            return result

    def get_person_statement(self, person_id: int) -> Dict[str, Any]:
        with self.db.connect() as connection:
            person_row = connection.execute(
                'SELECT id, first_name, last_name, mobile, national_id FROM persons WHERE id = ? LIMIT 1',
                (person_id,),
            ).fetchone()
            if not person_row:
                raise ValidationError('شخص انتخاب شده یافت نشد.')
            person = self._row_to_dict(person_row)

            docs = connection.execute(
                '''
                SELECT id, finance_no, operation_type, direction, finance_date, total_amount, settled_amount,
                       description
                FROM financial_documents
                WHERE counterparty_person_id = ? AND status <> 'CANCELLED'
                ORDER BY finance_date, id
                ''',
                (person_id,),
            ).fetchall()

            payments = connection.execute(
                '''
                SELECT pe.id, pe.financial_document_id, pe.amount, pe.created_at, pe.due_date, pe.status,
                       pe.description, pe.check_no, pm.name AS payment_method_name,
                       fd.finance_no, fd.operation_type, fd.direction
                FROM payment_entries pe
                JOIN financial_documents fd ON fd.id = pe.financial_document_id
                JOIN payment_methods pm ON pm.id = pe.payment_method_id
                WHERE fd.counterparty_person_id = ?
                ORDER BY COALESCE(pe.due_date, substr(pe.created_at, 1, 10)), pe.id
                ''',
                (person_id,),
            ).fetchall()

        events: List[Dict[str, Any]] = []
        for row in docs:
            item = self._row_to_dict(row)
            events.append(
                {
                    'event_date': item['finance_date'],
                    'sort_order': 1,
                    'row_type': 'FINANCE_DOC',
                    'reference_no': item['finance_no'],
                    'operation_type': item['operation_type'],
                    'description': item.get('description') or '',
                    'debit_amount': int(item['total_amount']) if item['direction'] == 'RECEIVABLE' else 0,
                    'credit_amount': int(item['total_amount']) if item['direction'] == 'PAYABLE' else 0,
                }
            )
        for row in payments:
            item = self._row_to_dict(row)
            payment_desc = item.get('description') or item.get('payment_method_name') or 'تسویه'
            status = item.get('status') or 'PENDING'
            if item.get('check_no'):
                payment_desc = f"{payment_desc} | چک: {item['check_no']} | وضعیت: {status}"
            elif status != 'CLEARED':
                payment_desc = f"{payment_desc} | وضعیت: {status}"
            debit = int(item['amount']) if item['direction'] == 'PAYABLE' and status == 'CLEARED' else 0
            credit = int(item['amount']) if item['direction'] == 'RECEIVABLE' and status == 'CLEARED' else 0
            events.append(
                {
                    'event_date': item.get('due_date') or str(item['created_at'])[:10],
                    'sort_order': 2,
                    'row_type': 'PAYMENT',
                    'reference_no': item['finance_no'],
                    'operation_type': item['operation_type'],
                    'description': payment_desc,
                    'debit_amount': debit,
                    'credit_amount': credit,
                }
            )
        events.sort(key=lambda x: (x['event_date'], x['sort_order'], x['reference_no']))

        running_balance = 0
        rows_out: List[Dict[str, Any]] = []
        for event in events:
            running_balance += int(event['debit_amount']) - int(event['credit_amount'])
            rows_out.append({**event, 'running_balance': running_balance})
        return {
            'person': person,
            'summary': {
                'receivable_total': sum(row['debit_amount'] for row in rows_out if row['row_type'] == 'FINANCE_DOC'),
                'payable_total': sum(row['credit_amount'] for row in rows_out if row['row_type'] == 'FINANCE_DOC'),
                'net_balance': running_balance,
            },
            'rows': rows_out,
        }

    def fetch_check_overview(self) -> Dict[str, int]:
        today_text = date.today().isoformat()
        query = '''
            SELECT
                COALESCE(COUNT(*), 0) AS total_checks,
                COALESCE(SUM(CASE WHEN pe.status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count,
                COALESCE(SUM(CASE WHEN pe.status = 'PENDING' THEN pe.amount ELSE 0 END), 0) AS pending_amount,
                COALESCE(SUM(CASE WHEN pe.status = 'PENDING' AND pe.due_date < ? THEN 1 ELSE 0 END), 0) AS overdue_count,
                COALESCE(SUM(CASE WHEN pe.status = 'PENDING' AND pe.due_date < ? THEN pe.amount ELSE 0 END), 0) AS overdue_amount,
                COALESCE(SUM(CASE WHEN pe.status = 'PENDING' AND pe.due_date = ? THEN pe.amount ELSE 0 END), 0) AS due_today_amount,
                COALESCE(SUM(CASE WHEN pe.status = 'CLEARED' THEN 1 ELSE 0 END), 0) AS cleared_count,
                COALESCE(SUM(CASE WHEN pe.status = 'BOUNCED' THEN 1 ELSE 0 END), 0) AS bounced_count
            FROM payment_entries pe
            JOIN payment_methods pm ON pm.id = pe.payment_method_id
            WHERE pm.code = 'CHECK'
        '''
        with self.db.connect() as connection:
            row = connection.execute(query, (today_text, today_text, today_text)).fetchone()
            return {key: int(row[key]) for key in row.keys()} if row else {
                'total_checks': 0,
                'pending_count': 0,
                'pending_amount': 0,
                'overdue_count': 0,
                'overdue_amount': 0,
                'due_today_amount': 0,
                'cleared_count': 0,
                'bounced_count': 0,
            }

    def list_check_entries(
        self,
        search_text: str = '',
        status_filter: str = 'ALL',
        due_scope: str = 'ALL',
    ) -> List[Dict[str, Any]]:
        filters = ["pm.code = 'CHECK'"]
        params: List[Any] = []
        search_text = search_text.strip()
        if search_text:
            filters.append(
                "(fd.finance_no LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR pe.check_no LIKE ? OR pe.check_serial LIKE ? OR pe.check_bank_name LIKE ? OR ir.reference_no LIKE ? OR orf.reference_no LIKE ? OR wr.receipt_no LIKE ? OR wi.issue_no LIKE ?)"
            )
            like = f'%{search_text}%'
            params.extend([like] * 10)
        if status_filter != 'ALL':
            filters.append('pe.status = ?')
            params.append(status_filter)

        today_text = date.today().isoformat()
        if due_scope == 'OVERDUE':
            filters.append("pe.status = 'PENDING' AND pe.due_date IS NOT NULL AND pe.due_date < ?")
            params.append(today_text)
        elif due_scope == 'TODAY':
            filters.append("pe.status = 'PENDING' AND pe.due_date = ?")
            params.append(today_text)
        elif due_scope == 'UPCOMING':
            filters.append("pe.status = 'PENDING' AND pe.due_date > ?")
            params.append(today_text)
        elif due_scope == 'NO_DUE_DATE':
            filters.append('(pe.due_date IS NULL OR pe.due_date = "")')

        where_clause = f"WHERE {' AND '.join(filters)}"
        query = f'''
            SELECT pe.*, pm.name AS payment_method_name, pm.code AS payment_method_code,
                   fd.finance_no, fd.operation_type, fd.direction, fd.counterparty_person_id,
                   p.first_name || ' ' || p.last_name AS counterparty_name,
                   ir.reference_no AS inbound_reference_no,
                   orf.reference_no AS outbound_reference_no,
                   wr.receipt_no,
                   wi.issue_no
            FROM payment_entries pe
            JOIN payment_methods pm ON pm.id = pe.payment_method_id
            JOIN financial_documents fd ON fd.id = pe.financial_document_id
            LEFT JOIN persons p ON p.id = fd.counterparty_person_id
            LEFT JOIN inbound_loads ir ON ir.id = fd.inbound_load_id
            LEFT JOIN outbound_loads orf ON orf.id = fd.outbound_load_id
            LEFT JOIN warehouse_receipts wr ON wr.id = fd.receipt_id
            LEFT JOIN warehouse_issues wi ON wi.id = fd.issue_id
            {where_clause}
            ORDER BY COALESCE(pe.due_date, substr(pe.created_at, 1, 10)), pe.id DESC
        '''
        with self.db.connect() as connection:
            return [self._row_to_dict(row) for row in connection.execute(query, params).fetchall()]

    def get_check_entry(self, payment_entry_id: int) -> Optional[Dict[str, Any]]:
        rows = self.list_check_entries()
        for row in rows:
            if row['id'] == payment_entry_id:
                return row
        return None

    # ============================================================
    # یکپارچه‌سازی C1: همه‌چیز روی treasury_accounts
    # ============================================================
    def register_payment(
        self,
        finance_id: int,
        payment_method_id: int,
        amount: int,
        user_id: Optional[int] = None,
        due_date: Optional[str] = None,
        check_no: Optional[str] = None,
        check_serial: Optional[str] = None,
        check_bank_name: Optional[str] = None,
        check_branch_name: Optional[str] = None,
        description: Optional[str] = None,
        treasury_account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if payment_method_id <= 0:
            raise ValidationError('روش پرداخت را انتخاب کنید.')
        if amount <= 0:
            raise ValidationError('مبلغ پرداخت/دریافت باید بیشتر از صفر باشد.')

        with self.db.connect() as connection:
            document = connection.execute('SELECT * FROM financial_documents WHERE id = ? LIMIT 1', (finance_id,)).fetchone()
            if not document:
                raise ValidationError('سند مالی انتخاب شده یافت نشد.')
            document_dict = self._row_to_dict(document)

            # [M1] مانده سند = کل − تسویه‌شده − چک‌های در انتظار (PENDING)
            pending_amount = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payment_entries "
                "WHERE financial_document_id = ? AND status = 'PENDING'",
                (finance_id,),
            ).fetchone()[0]
            remaining = (
                int(document_dict['total_amount'])
                - int(document_dict['settled_amount'])
                - int(pending_amount or 0)
            )
            if amount > remaining:
                raise ValidationError('مبلغ ثبت‌شده از مانده سند مالی بیشتر است.')

            method = connection.execute('SELECT * FROM payment_methods WHERE id = ? LIMIT 1', (payment_method_id,)).fetchone()
            if not method:
                raise ValidationError('روش پرداخت معتبر نیست.')
            method_dict = self._row_to_dict(method)

            if method_dict['code'] == 'CHECK' and not check_no and not check_serial:
                raise ValidationError('برای ثبت چک، حداقل شماره چک یا سریال چک را وارد کنید.')
            if method_dict['code'] == 'CHECK' and not due_date:
                raise ValidationError('برای ثبت چک، تاریخ سررسید الزامی است.')

            treasury_account = self._get_treasury_account(connection, treasury_account_id) if treasury_account_id else None
            if method_dict['code'] in {'CASH', 'BANK_TRANSFER', 'OTHER'} and not treasury_account:
                raise ValidationError('برای این روش تسویه، انتخاب صندوق / بانک تفصیلی الزامی است.')
            if method_dict['code'] == 'CHECK' and treasury_account and treasury_account['account_type'] != 'BANK':
                raise ValidationError('برای چک باید یک حساب بانکی از بخش صندوق / بانک انتخاب شود.')

            # [CHECK-DUE] چک با سررسید امروز/گذشته → وصول (CLEARED)؛ چک آینده → در انتظار (PENDING)
            today_text = date.today().isoformat()
            if method_dict['code'] == 'CHECK':
                if due_date and due_date <= today_text:
                    status = 'CLEARED'
                else:
                    status = 'PENDING'
            else:
                status = 'CLEARED'

            if method_dict['code'] == 'CHECK' and status == 'CLEARED' and not treasury_account:
                raise ValidationError('برای چک سررسیدشده (امروز یا گذشته)، انتخاب حساب بانکی الزامی است.')
            cursor = connection.execute(
                '''
                INSERT INTO payment_entries (
                    financial_document_id, payment_method_id, payer_payee_person_id, bank_account_id,
                    treasury_account_id, amount, due_date, check_no, check_serial, check_bank_name, check_branch_name,
                    status, description, created_at
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    finance_id,
                    payment_method_id,
                    document_dict['counterparty_person_id'],
                    treasury_account['id'] if treasury_account else None,
                    amount,
                    due_date,
                    check_no,
                    check_serial,
                    check_bank_name,
                    check_branch_name,
                    status,
                    description,
                    now_iso(),
                ),
            )
            payment_entry_id = int(cursor.lastrowid)

            if status == 'CLEARED':
                self._create_settlement_journal(
                    connection=connection,
                    document=document_dict,
                    method_code=method_dict['code'],
                    amount=amount,
                    user_id=user_id,
                    payment_entry_id=payment_entry_id,
                )
                if treasury_account is not None:
                    self._create_treasury_transaction(
                        connection=connection,
                        treasury_account_id=int(treasury_account['id']),
                        finance_date=document_dict['finance_date'],
                        direction=document_dict['direction'],
                        amount=amount,
                        description=f"تسویه سند مالی {document_dict['finance_no']}",
                        source_id=payment_entry_id,
                    )

            self._recalculate_financial_document(connection, finance_id)
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='payment_entries',
                entity_id=str(payment_entry_id),
                action_name='CREATE_PAYMENT',
                old_values=None,
                new_values={
                    'financial_document_id': finance_id,
                    'amount': amount,
                    'payment_method': method_dict['code'],
                    'status': status,
                    'treasury_account_id': treasury_account['id'] if treasury_account else None,
                },
            )
            connection.commit()
        return self.get_financial_document(finance_id) or {}

    def update_check_status(
        self,
        payment_entry_id: int,
        new_status: str,
        user_id: Optional[int] = None,
        note: Optional[str] = None,
        treasury_account_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if new_status not in {'CLEARED', 'BOUNCED', 'CANCELLED', 'PENDING'}:
            raise ValidationError('وضعیت جدید چک معتبر نیست.')
        with self.db.connect() as connection:
            row = connection.execute(
                '''
                SELECT pe.*, pm.code AS payment_method_code, fd.id AS finance_id, fd.finance_no,
                       fd.direction, fd.counterparty_person_id, fd.finance_date, fd.operation_type,
                       ca.account_type AS treasury_account_type
                FROM payment_entries pe
                JOIN payment_methods pm ON pm.id = pe.payment_method_id
                JOIN financial_documents fd ON fd.id = pe.financial_document_id
                LEFT JOIN treasury_accounts ca ON ca.id = pe.treasury_account_id
                WHERE pe.id = ? LIMIT 1
                ''',
                (payment_entry_id,),
            ).fetchone()
            if not row:
                raise ValidationError('رکورد چک یافت نشد.')
            payment = self._row_to_dict(row)
            if payment['payment_method_code'] != 'CHECK':
                raise ValidationError('این رکورد از نوع چک نیست.')
            if payment['status'] == 'CLEARED' and new_status != 'CLEARED':
                raise ValidationError('چک وصول‌شده را نمی‌توان به وضعیت دیگر تغییر داد.')
            if payment['status'] != 'PENDING' and payment['status'] != new_status and not (payment['status'] == 'CLEARED' and new_status in ('PENDING', 'BOUNCED', 'CANCELLED')):
                raise ValidationError('فقط چک‌های در انتظار قابل تغییر وضعیت هستند.')

            old_values = {'status': payment['status'], 'description': payment.get('description')}
            new_description = self._append_note(payment.get('description'), note) if note else payment.get('description')
            treasury_account = None
            treasury_account_id_to_set = payment.get('treasury_account_id')
            if payment['status'] != 'CLEARED' and new_status == 'CLEARED':
                if treasury_account_id is not None:
                    treasury_account = self._get_treasury_account(connection, treasury_account_id)
                    if treasury_account['account_type'] != 'BANK':
                        raise ValidationError('برای وصول چک باید یک حساب بانکی انتخاب شود.')
                    treasury_account_id_to_set = treasury_account['id']
                elif payment.get('treasury_account_id'):
                    treasury_account = self._get_treasury_account(connection, int(payment['treasury_account_id']))
                else:
                    raise ValidationError('برای وصول چک، انتخاب صندوق / بانک بانکی الزامی است.')

            if payment['status'] == 'CLEARED' and new_status != 'CLEARED':
                if payment.get('treasury_account_id'):
                    connection.execute('UPDATE treasury_accounts SET current_balance = COALESCE(current_balance,0) - ? WHERE id = ?',
                                         (int(payment['amount']), int(payment['treasury_account_id'])))
                treasury_account_id_to_set = None
            connection.execute(
                'UPDATE payment_entries SET status = ?, description = ?, treasury_account_id = ? WHERE id = ?',
                (new_status, new_description, treasury_account_id_to_set, payment_entry_id),
            )
            if payment['status'] != 'CLEARED' and new_status == 'CLEARED':
                self._create_settlement_journal(
                    connection=connection,
                    document={
                        'id': payment['finance_id'],
                        'finance_no': payment['finance_no'],
                        'direction': payment['direction'],
                        'counterparty_person_id': payment['counterparty_person_id'],
                        'finance_date': payment['finance_date'],
                        'operation_type': payment['operation_type'],
                    },
                    method_code='CHECK',
                    amount=int(payment['amount']),
                    user_id=user_id,
                    payment_entry_id=payment_entry_id,
                )
                if treasury_account is not None:
                    self._create_treasury_transaction(
                        connection=connection,
                        treasury_account_id=int(treasury_account['id']),
                        finance_date=payment['finance_date'],
                        direction=payment['direction'],
                        amount=int(payment['amount']),
                        description=f"وصول چک سند مالی {payment['finance_no']}",
                        source_id=payment_entry_id,
                    )
            self._recalculate_financial_document(connection, int(payment['finance_id']))
            self.db.log_audit(
                connection=connection,
                user_id=user_id,
                entity_name='payment_entries',
                entity_id=str(payment_entry_id),
                action_name='UPDATE_CHECK_STATUS',
                old_values=old_values,
                new_values={'status': new_status, 'description': new_description},
            )
            connection.commit()
        return self.get_check_entry(payment_entry_id) or {}

    def cancel_financial_document(self, finance_id: int, user_id: Optional[int] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        """ابطال سند مالی (نقطه ورود اصلی)"""
        with self.db.connect() as connection:
            self._cancel_financial_document_in_connection(connection, finance_id, user_id=user_id, reason=reason)
            connection.commit()
        return self.get_financial_document(finance_id) or {}

    def cancel_related_documents_for_receipt(
        self,
        connection: sqlite3.Connection,
        receipt_id: int,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> int:
        """ابطال همه اسناد مالی مرتبط با یک رسید (قبل از ابطال رسید)"""
        rows = connection.execute(
            "SELECT id FROM financial_documents WHERE receipt_id = ? AND status <> 'CANCELLED' ORDER BY id DESC",
            (receipt_id,),
        ).fetchall()
        for row in rows:
            self._cancel_financial_document_in_connection(connection, int(row['id']), user_id=user_id, reason=reason)
        return len(rows)

    def cancel_related_documents_for_issue(
        self,
        connection: sqlite3.Connection,
        issue_id: int,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> int:
        """ابطال همه اسناد مالی مرتبط با یک حواله (قبل از ابطال حواله)"""
        rows = connection.execute(
            "SELECT id FROM financial_documents WHERE issue_id = ? AND status <> 'CANCELLED' ORDER BY id DESC",
            (issue_id,),
        ).fetchall()
        for row in rows:
            self._cancel_financial_document_in_connection(connection, int(row['id']), user_id=user_id, reason=reason)
        return len(rows)

    def _cancel_financial_document_in_connection(
        self,
        connection: sqlite3.Connection,
        finance_id: int,
        user_id: Optional[int],
        reason: Optional[str],
    ) -> None:
        """ابطال امن سند مالی با چک‌های جامع و ثبت audit"""
        # شروع تراکنش با BEGIN IMMEDIATE برای جلوگیری از race condition
        connection.execute("BEGIN IMMEDIATE")
        
        row = connection.execute('SELECT * FROM financial_documents WHERE id = ? LIMIT 1', (finance_id,)).fetchone()
        if not row:
            raise ValidationError('سند مالی یافت نشد.')
        document = self._row_to_dict(row)
        if document['status'] == 'CANCELLED':
            return  # قبلاً ابطال شده

        # چک جامع: هم CLEARED و هم PENDING
        cleared_payments = connection.execute(
            "SELECT id, amount, status FROM payment_entries "
            "WHERE financial_document_id = ? AND status = 'CLEARED'",
            (finance_id,),
        ).fetchall()
        
        if cleared_payments:
            total_cleared = sum(int(p['amount']) for p in cleared_payments)
            raise ValidationError(
                f'این سند مالی دارای {len(cleared_payments)} پرداخت وصول‌شده '
                f'به مبلغ {total_cleared:,} ریال است.\n'
                f'ابتدا تسویه‌ها را برگردانید، سپس ابطال کنید.'
            )

        # چک settled_amount
        if int(document.get('settled_amount') or 0) > 0:
            raise ValidationError(
                f'این سند مالی دارای تسویه به مبلغ {document["settled_amount"]:,} ریال است.\n'
                f'ابتدا تسویه‌ها را برگردانید، سپس ابطال کنید.'
            )

        # ابطال پرداخت‌های PENDING
        pending_payments = connection.execute(
            'SELECT id, status, description FROM payment_entries WHERE financial_document_id = ?',
            (finance_id,),
        ).fetchall()
        
        rollback_reason = reason or f'ابطال امن سند مالی {document["finance_no"]}'
        cancelled_payments = 0
        
        for payment in pending_payments:
            payment_dict = self._row_to_dict(payment)
            if payment_dict['status'] == 'CANCELLED':
                continue
            new_desc = self._append_note(payment_dict.get('description'), rollback_reason)
            connection.execute(
                'UPDATE payment_entries SET status = ?, description = ? WHERE id = ?',
                ('CANCELLED', new_desc, payment_dict['id']),
            )
            cancelled_payments += 1

        # ثبت سند برگشت در دفتر روزنامه
        self._create_reversal_journal_for_finance_doc(connection, document, user_id=user_id, reason=rollback_reason)
        
        # ابطال سند مالی با ثبت زمان و کاربر (اگر ستون‌ها موجود باشند)
        new_description = self._append_note(document.get('description'), rollback_reason)
        now_iso_str = now_iso()
        
        # تلاش برای ثبت cancelled_by / cancelled_at / cancel_reason
        connection.execute(
            'UPDATE financial_documents SET settled_amount = 0, status = ?, description = ? WHERE id = ?',
            ('CANCELLED', new_description, finance_id)
        )
        
        # تلاش برای پر کردن ستون‌های audit (اگر موجود باشند)
        for column, value in [
            ('cancelled_by', user_id),
            ('cancelled_at', now_iso_str),
            ('cancel_reason', rollback_reason),
        ]:
            try:
                connection.execute(
                    f'UPDATE financial_documents SET {column} = ? WHERE id = ?',
                    (value, finance_id)
                )
            except Exception:
                pass  # ستون وجود ندارد

        # Audit log
        self.db.log_audit(
            connection=connection,
            user_id=user_id,
            entity_name='financial_documents',
            entity_id=str(finance_id),
            action_name='CANCEL',
            old_values=document,
            new_values={
                **document,
                'status': 'CANCELLED',
                'settled_amount': 0,
                'description': new_description,
                'cancelled_payments': cancelled_payments,
            },
        )

    def _recalculate_financial_document(self, connection: sqlite3.Connection, finance_id: int) -> None:
        """محاسبه مجدد مانده و وضعیت سند مالی"""
        # [C2] اصلاح باگ بحرانی: ستون واقعی 'total_amount' است
        document = connection.execute(
            'SELECT total_amount, status FROM financial_documents WHERE id = ? LIMIT 1',
            (finance_id,),
        ).fetchone()
        if not document or document['status'] == 'CANCELLED':
            return
        total_amount = int(document['total_amount'])
        cleared_amount = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payment_entries WHERE financial_document_id = ? AND status = 'CLEARED'",
            (finance_id,),
        ).fetchone()[0]
        cleared_amount = int(cleared_amount or 0)
        status = 'SETTLED' if cleared_amount >= total_amount and total_amount > 0 else 'PARTIAL' if cleared_amount > 0 else 'OPEN'
        connection.execute(
            'UPDATE financial_documents SET settled_amount = ?, status = ? WHERE id = ?',
            (cleared_amount, status, finance_id),
        )

    def _create_settlement_journal(
        self,
        connection: sqlite3.Connection,
        document: Dict[str, Any],
        method_code: str,
        amount: int,
        user_id: Optional[int],
        payment_entry_id: Optional[int] = None,
    ) -> None:
        bank_or_cash_code = '1100' if method_code == 'CASH' else '1200'
        if document['direction'] == 'RECEIVABLE':
            debit_code = bank_or_cash_code
            credit_code = '2200'
        else:
            debit_code = self._payable_account_code(document['operation_type'])
            credit_code = bank_or_cash_code
        description = f"تسویه سند مالی {document['finance_no']}"
        if payment_entry_id:
            description += f" | پرداخت #{payment_entry_id}"
        self._create_journal_entry(
            connection=connection,
            entry_date=document['finance_date'],
            reference_type='FINANCE_SETTLEMENT',
            reference_id=int(document['id']),
            description=description,
            debit_account_code=debit_code,
            credit_account_code=credit_code,
            amount=amount,
            person_id=document.get('counterparty_person_id'),
            user_id=user_id,
        )

    def _create_reversal_journal_for_finance_doc(
        self,
        connection: sqlite3.Connection,
        document: Dict[str, Any],
        user_id: Optional[int],
        reason: Optional[str],
    ) -> None:
        amount = int(document.get('total_amount') or 0)
        if amount <= 0:
            return
        original_accounts = self.OPERATION_ACCOUNT_MAP.get(document['operation_type'])
        if not original_accounts:
            return
        debit_code, credit_code = original_accounts
        description = f"برگشت سند مالی {document['finance_no']}"
        if reason:
            description += f" | {reason}"
        self._create_journal_entry(
            connection=connection,
            entry_date=now_iso()[:10],
            reference_type='FINANCE_DOC_CANCEL',
            reference_id=int(document['id']),
            description=description,
            debit_account_code=credit_code,
            credit_account_code=debit_code,
            amount=amount,
            person_id=document.get('counterparty_person_id'),
            user_id=user_id,
        )

    def _create_journal_entry(
        self,
        connection: sqlite3.Connection,
        entry_date: str,
        reference_type: str,
        reference_id: int,
        description: str,
        debit_account_code: str,
        credit_account_code: str,
        amount: int,
        person_id: Optional[int],
        user_id: Optional[int],
    ) -> None:
        if amount <= 0:
            return
        entry_no = self.db.next_sequence_value(connection, 'journal_entry')
        cursor = connection.execute(
            '''
            INSERT INTO journal_entries (
                entry_no, entry_date, reference_type, reference_id, description, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (entry_no, entry_date, reference_type, reference_id, description, now_iso(), user_id),
        )
        journal_entry_id = int(cursor.lastrowid)
        debit_account_id = self._account_id_by_code(connection, debit_account_code)
        credit_account_id = self._account_id_by_code(connection, credit_account_code)
        connection.execute(
            '''
            INSERT INTO journal_lines (
                journal_entry_id, line_no, account_id, person_id, bank_account_id,
                debit_amount, credit_amount, description
            ) VALUES (?, 1, ?, ?, NULL, ?, 0, ?)
            ''',
            (journal_entry_id, debit_account_id, person_id, amount, description),
        )
        connection.execute(
            '''
            INSERT INTO journal_lines (
                journal_entry_id, line_no, account_id, person_id, bank_account_id,
                debit_amount, credit_amount, description
            ) VALUES (?, 2, ?, ?, NULL, 0, ?, ?)
            ''',
            (journal_entry_id, credit_account_id, person_id, amount, description),
        )

    def _append_note(self, current: Optional[str], note: str) -> str:
        current_text = (current or '').strip()
        return f'{current_text} | {note}' if current_text else note

    # ============================================================
    # ✅ یکپارچه‌سازی C1: کار با treasury_accounts
    # ============================================================
    def _get_treasury_account(self, connection: sqlite3.Connection, treasury_account_id: Optional[int]) -> Dict[str, Any]:
        if not treasury_account_id:
            raise ValidationError('صندوق / بانک تفصیلی انتخاب نشده است.')
        # اول حساب را (بدون فیلتر فعال) پیدا کن تا پیام دقیق‌تری بدهیم
        row = connection.execute(
            'SELECT id, code, name, account_type, bank_name, account_number, current_balance, is_active '
            'FROM treasury_accounts WHERE id = ? LIMIT 1',
            (treasury_account_id,),
        ).fetchone()
        if not row:
            raise ValidationError('صندوق / بانک تفصیلی یافت نشد.')
        if not row[7]:
            raise ValidationError(
                "حساب «{0}» غیرفعال است؛ لطفاً از بخش مدیریت صندوق/بانک آن را فعال کنید.".format(row[2])
            )
        return {
            'id': row[0],
            'code': row[1],
            'name': row[2],
            'account_type': row[3],       # CASHBOX یا BANK
            'bank_name': row[4] or '',
            'account_number': row[5] or '',
            'current_balance': row[6] or 0,
            'is_active': row[7],
        }

    # ============================================================
    # ✅ آپدیت treasury_accounts.current_balance
    # ============================================================
    def _create_treasury_transaction(
        self,
        connection: sqlite3.Connection,
        treasury_account_id: int,
        finance_date: str,
        direction: str,
        amount: int,
        description: str,
        source_id: Optional[int],
    ) -> None:
        account = self._get_treasury_account(connection, treasury_account_id)
        current_balance = int(account.get('current_balance') or 0)
        if direction == 'RECEIVABLE':
            transaction_type = 'IN'
            new_balance = current_balance + amount
        else:
            if current_balance < amount:
                raise ValidationError(f"موجودی صندوق / بانک «{account['name']}» برای این پرداخت کافی نیست.")
            transaction_type = 'OUT'
            new_balance = current_balance - amount

        # ✅ آپدیت treasury_accounts
        connection.execute(
            'UPDATE treasury_accounts SET current_balance = ? WHERE id = ?',
            (new_balance, treasury_account_id),
        )

        # ثبت در treasury_transactions (این جدول برای لاگ گردش استفاده میشه)
        connection.execute(
            '''
            INSERT INTO treasury_transactions (
                treasury_account_id, transaction_date, transaction_type, source_type, source_id,
                amount, balance_after, description, created_at
            ) VALUES (?, ?, ?, 'PAYMENT_ENTRY', ?, ?, ?, ?, ?)
            ''',
            (treasury_account_id, finance_date, transaction_type, source_id, amount, new_balance, description, now_iso()),
        )

    def _payable_account_code(self, operation_type: str) -> str:
        return '2300' if operation_type in ('INBOUND_FREIGHT', 'OUTBOUND_FREIGHT') else '2100'

    def _account_id_by_code(self, connection: sqlite3.Connection, code: str) -> int:
        row = connection.execute('SELECT id FROM ledger_accounts WHERE code = ? LIMIT 1', (code,)).fetchone()
        if not row:
            raise RuntimeError(f'Ledger account not found: {code}')
        return int(row['id'])