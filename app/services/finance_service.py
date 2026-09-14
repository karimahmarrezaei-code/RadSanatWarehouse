import sqlite3
from typing import Any, Dict, Optional

from app.core.database import DatabaseManager
from app.core.jalali import now_iso


class FinanceService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def create_for_inbound_receipt(
        self,
        connection: sqlite3.Connection,
        receipt_data: Dict[str, Any],
        goods_amount: int,
        user_id: Optional[int],
    ) -> None:
        if goods_amount > 0:
            finance_id = self._create_financial_document(
                connection=connection,
                operation_type='INBOUND_RECEIPT',
                direction='PAYABLE',
                inbound_load_id=receipt_data['inbound_load_id'],
                outbound_load_id=None,
                receipt_id=receipt_data['id'],
                issue_id=None,
                counterparty_person_id=receipt_data['supplier_id'],
                finance_date=receipt_data['receipt_date'],
                total_amount=goods_amount,
                description=f"بدهی خرید پالت | {receipt_data['receipt_no']}",
                user_id=user_id,
            )
            self._create_journal_entry(
                connection=connection,
                entry_date=receipt_data['receipt_date'],
                reference_type='FINANCE_DOC',
                reference_id=finance_id,
                description=f"ثبت خرید پالت | {receipt_data['receipt_no']}",
                debit_account_code='1300',
                credit_account_code='2100',
                amount=goods_amount,
                person_id=receipt_data['supplier_id'],
                user_id=user_id,
            )

        freight_amount = int(receipt_data.get('freight_amount') or 0)
        if freight_amount > 0:
            finance_id = self._create_financial_document(
                connection=connection,
                operation_type='INBOUND_FREIGHT',
                direction='PAYABLE',
                inbound_load_id=receipt_data['inbound_load_id'],
                outbound_load_id=None,
                receipt_id=receipt_data['id'],
                issue_id=None,
                counterparty_person_id=receipt_data['driver_id'],
                finance_date=receipt_data['receipt_date'],
                total_amount=freight_amount,
                description=f"بدهی کرایه حمل ورودی | {receipt_data['receipt_no']}",
                user_id=user_id,
            )
            self._create_journal_entry(
                connection=connection,
                entry_date=receipt_data['receipt_date'],
                reference_type='FINANCE_DOC',
                reference_id=finance_id,
                description=f"هزینه حمل ورودی | {receipt_data['receipt_no']}",
                debit_account_code='5000',
                credit_account_code='2300',
                amount=freight_amount,
                person_id=receipt_data['driver_id'],
                user_id=user_id,
            )

    def create_for_outbound_issue(
        self,
        connection: sqlite3.Connection,
        issue_data: Dict[str, Any],
        goods_amount: int,
        user_id: Optional[int],
    ) -> None:
        if goods_amount > 0:
            finance_id = self._create_financial_document(
                connection=connection,
                operation_type='OUTBOUND_ISSUE',
                direction='RECEIVABLE',
                inbound_load_id=None,
                outbound_load_id=issue_data['outbound_load_id'],
                receipt_id=None,
                issue_id=issue_data['id'],
                counterparty_person_id=issue_data['customer_id'],
                finance_date=issue_data['issue_date'],
                total_amount=goods_amount,
                description=f"مطالبه فروش پالت | {issue_data['issue_no']}",
                user_id=user_id,
            )
            self._create_journal_entry(
                connection=connection,
                entry_date=issue_data['issue_date'],
                reference_type='FINANCE_DOC',
                reference_id=finance_id,
                description=f"ثبت فروش پالت | {issue_data['issue_no']}",
                debit_account_code='2200',
                credit_account_code='4000',
                amount=goods_amount,
                person_id=issue_data['customer_id'],
                user_id=user_id,
            )

        freight_amount = int(issue_data.get('freight_amount') or 0)
        if freight_amount > 0:
            finance_id = self._create_financial_document(
                connection=connection,
                operation_type='OUTBOUND_FREIGHT',
                direction='PAYABLE',
                inbound_load_id=None,
                outbound_load_id=issue_data['outbound_load_id'],
                receipt_id=None,
                issue_id=issue_data['id'],
                counterparty_person_id=issue_data['driver_id'],
                finance_date=issue_data['issue_date'],
                total_amount=freight_amount,
                description=f"بدهی کرایه حمل خروجی | {issue_data['issue_no']}",
                user_id=user_id,
            )
            self._create_journal_entry(
                connection=connection,
                entry_date=issue_data['issue_date'],
                reference_type='FINANCE_DOC',
                reference_id=finance_id,
                description=f"هزینه حمل خروجی | {issue_data['issue_no']}",
                debit_account_code='5000',
                credit_account_code='2300',
                amount=freight_amount,
                person_id=issue_data['driver_id'],
                user_id=user_id,
            )

    def _create_financial_document(
        self,
        connection: sqlite3.Connection,
        operation_type: str,
        direction: str,
        inbound_load_id: Optional[int],
        outbound_load_id: Optional[int],
        receipt_id: Optional[int],
        issue_id: Optional[int],
        counterparty_person_id: Optional[int],
        finance_date: str,
        total_amount: int,
        description: str,
        user_id: Optional[int],
    ) -> int:
        finance_no = self.db.next_sequence_value(connection, 'financial_document')
        cursor = connection.execute(
            '''
            INSERT INTO financial_documents (
                finance_no, operation_type, direction, inbound_load_id, outbound_load_id,
                receipt_id, issue_id, counterparty_person_id, finance_date,
                total_amount, settled_amount, status, description, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)
            ''',
            (
                finance_no,
                operation_type,
                direction,
                inbound_load_id,
                outbound_load_id,
                receipt_id,
                issue_id,
                counterparty_person_id,
                finance_date,
                total_amount,
                description,
                now_iso(),
                user_id,
            ),
        )
        finance_id = int(cursor.lastrowid)
        self.db.log_audit(
            connection=connection,
            user_id=user_id,
            entity_name='financial_documents',
            entity_id=str(finance_id),
            action_name='AUTO_CREATE',
            old_values=None,
            new_values={
                'finance_no': finance_no,
                'operation_type': operation_type,
                'direction': direction,
                'total_amount': total_amount,
                'description': description,
            },
        )
        return finance_id

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

    def _account_id_by_code(self, connection: sqlite3.Connection, code: str) -> int:
        row = connection.execute('SELECT id FROM ledger_accounts WHERE code = ? LIMIT 1', (code,)).fetchone()
        if not row:
            raise RuntimeError(f'Ledger account not found: {code}')
        return int(row['id'])
