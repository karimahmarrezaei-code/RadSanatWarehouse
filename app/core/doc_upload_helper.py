# -*- coding: utf-8 -*-
"""
doc_upload_helper.py - باز کردن فرم آپلود عکس بعد از ثبت موفق رسید/حواله

این ماژول بعد از ثبت سند صدا زده می‌شود:
  - ID سند و ID/نام شخص را پیدا می‌کند (اول از `saved`، سپس از دیتابیس)
  - فرم DocumentUploadDialog را باز می‌کند
  - هرگز خطا نمی‌دهد (try/except) تا ثبت سند خراب نشود
"""
from typing import Any, Dict, Optional


def _resolve_doc(conn, doc_type: str, doc_no: str):
    """پیدا کردن (id, person_id) سند از جدول سند با شماره سند"""
    if doc_type == 'RECEIPT':
        table, id_field, person_field = 'warehouse_receipts', 'receipt_no', 'supplier_id'
    else:
        table, id_field, person_field = 'warehouse_issues', 'issue_no', 'customer_id'
    try:
        row = conn.execute(
            f'SELECT id, {person_field} FROM {table} WHERE {id_field} = ?',
            (doc_no,),
        ).fetchone()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    # تلاش دوم: فقط id
    try:
        row = conn.execute(
            f'SELECT id FROM {table} WHERE {id_field} = ?',
            (doc_no,),
        ).fetchone()
        if row:
            return row[0], None
    except Exception:
        pass
    return None, None


def _person_name(conn, person_id: Optional[int]) -> str:
    """نام شخص از جدول persons (ترکیب first_name + last_name)"""
    if not person_id:
        return ''
    try:
        row = conn.execute(
            "SELECT COALESCE(first_name,'') || ' ' || COALESCE(last_name,'') AS full_name "
            "FROM persons WHERE id = ?",
            (person_id,)
        ).fetchone()
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        pass
    return ''

def open_upload_after_save(
    parent,
    doc_type: str,
    saved: Dict[str, Any],
    db,
    user_data: Optional[Dict[str, Any]] = None,
) -> None:
    """باز کردن فرم آپلود عکس بعد از ثبت موفق سند.

    doc_type: 'RECEIPT' یا 'ISSUE'
    saved: خروجی repository (شامل receipt_no / issue_no / id / person_id / person_name)
    """
    try:
        from app.ui.document_upload_dialog import DocumentUploadDialog

        doc_no = saved.get('receipt_no') or saved.get('issue_no') or ''
        doc_id = saved.get('id')
        person_id = saved.get('person_id')
        person_name = saved.get('person_name') or ''

        # تکمیل از دیتابیس اگر در saved نبود
        if db is not None and (not doc_id or not person_id or not person_name):
            try:
                with db.connect() as conn:
                    if not doc_id or not person_id:
                        did, pid = _resolve_doc(conn, doc_type, doc_no)
                        if not doc_id:
                            doc_id = did
                        if not person_id:
                            person_id = pid
                    if not person_name:
                        person_name = _person_name(conn, person_id)
            except Exception:
                pass

        if not doc_id:
            doc_id = 0

        dlg = DocumentUploadDialog(
            db,
            doc_type,
            doc_id,
            person_id=person_id,
            person_name=person_name,
            doc_no=doc_no,
            user_data=user_data,
            parent=parent,
        )
        dlg.exec_()
    except Exception as exc:
        print('[doc-images] upload dialog error:', exc)
