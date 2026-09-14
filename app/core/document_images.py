# -*- coding: utf-8 -*-
"""
document_images.py - v2 مدیریت تصاویر اسناد (رسید/حواله)

v2 تغییرات نسبت به نسخه قبل:
  - نام فایل: {doc_type}_{doc_id}_{person_id}_{person_name}_{شماره}{ext}
    مثال: RECEIPT_105_7_شرکت_راد_صنعت_1.jpg
  - پوشه دلخواه: می‌توان پوشه ذخیره را انتخاب کرد (پیش‌فرض uploads/documents)
    آخرین پوشه انتخابی در فایل settings.json حفظ می‌شود
  - اگر پوشه انتخابی خارج از پروژه باشد، مسیر مطلق در دیتابیس ذخیره می‌شود
  - حداکثر ۳ عکس برای هر سند (اختیاری)
  - فرمت‌های مجاز: jpg, jpeg, png, bmp, webp
  - حداکثر حجم: ۱۰ مگابایت

استفاده:
  from app.core.document_images import (
      save_document_image, get_document_images, delete_document_image,
      get_person_documents, get_last_upload_dir, set_last_upload_dir,
  )
"""
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
MAX_IMAGES = 3
MAX_SIZE_MB = 10

_SETTINGS_FILE = 'doc_images_settings.json'


# ----------------------------------------------------------------------
# پوشه و تنظیمات
# ----------------------------------------------------------------------

def _default_dir() -> Path:
    """پوشه پیش‌فرض ذخیره تصاویر (داخل پروژه)"""
    d = Path(os.getcwd()) / 'uploads' / 'documents'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _settings_path() -> Path:
    return Path(os.getcwd()) / _SETTINGS_FILE


def get_last_upload_dir() -> str:
    """آخرین پوشه انتخابی کاربر (از settings.json)"""
    try:
        with open(_settings_path(), encoding='utf-8') as f:
            data = json.load(f)
        d = data.get('last_upload_dir', '')
        if d and os.path.isdir(d):
            return d
    except Exception:
        pass
    return str(_default_dir())


def set_last_upload_dir(path: str) -> None:
    """ذخیره پوشه انتخابی کاربر برای دفعات بعد"""
    try:
        data = {}
        if _settings_path().exists():
            with open(_settings_path(), encoding='utf-8') as f:
                data = json.load(f)
        data['last_upload_dir'] = str(path)
        with open(_settings_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ----------------------------------------------------------------------
# جدول
# ----------------------------------------------------------------------

def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS document_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,           -- RECEIPT / ISSUE / PROFORMA / OTHER
            doc_id INTEGER NOT NULL,          -- شناسه سند
            person_id INTEGER,                -- مشتری/تامین‌کننده
            file_path TEXT NOT NULL,          -- مسیر فایل (مطلق یا نسبی)
            original_name TEXT,               -- نام اصلی فایل
            uploaded_at TEXT NOT NULL,
            uploaded_by INTEGER
        )
        """
    )
    conn.commit()


# ----------------------------------------------------------------------
# نام فایل
# ----------------------------------------------------------------------

def _sanitize(name: str) -> str:
    """پاک‌سازی نام برای استفاده در نام فایل (حذف کاراکترهای غیرمجاز ویندوز)"""
    name = re.sub(r'[\\/:*?"<>|]', '_', str(name))
    name = re.sub(r'\s+', '_', name).strip('_')
    return name or 'unknown'


def build_image_filename(doc_type: str, doc_id: int, person_id, person_name: str, seq: int, ext: str) -> str:
    """نام فایل: {doc_type}_{doc_id}_{person_id}_{person_name}_{seq}{ext}"""
    pid = _sanitize(str(person_id if person_id else 0))
    pname = _sanitize(person_name)
    return '{}_{}_{}_{}_{}{}'.format(doc_type, doc_id, pid, pname, seq, ext)


# ----------------------------------------------------------------------
# عملیات اصلی
# ----------------------------------------------------------------------

def save_document_image(
    conn: sqlite3.Connection,
    doc_type: str,
    doc_id: int,
    source_path: str,
    person_id: Optional[int] = None,
    person_name: str = '',
    target_dir: Optional[str] = None,
    seq: Optional[int] = None,
    uploaded_by: Optional[int] = None,
) -> Dict[str, Any]:
    """ذخیره یک عکس برای سند.

    - target_dir: پوشه دلخواه؛ اگر None باشد پوشه پیش‌فرض uploads/documents
    - seq: شماره ترتیبی عکس (۱، ۲، ۳)؛ اگر None باشد به‌صورت خودکار count+1
    - نام فایل: {doc_type}_{doc_id}_{person_id}_{person_name}_{seq}{ext}
    """
    _ensure_table(conn)

    count = conn.execute(
        "SELECT COUNT(*) FROM document_images WHERE doc_type = ? AND doc_id = ?",
        (doc_type, doc_id),
    ).fetchone()[0]
    if count >= MAX_IMAGES:
        raise ValueError('حداکثر {} عکس برای هر سند مجاز است.'.format(MAX_IMAGES))

    ext = Path(source_path).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError('فرمت {} مجاز نیست. فرمت‌های مجاز: jpg, png, bmp, webp'.format(ext))

    size_mb = os.path.getsize(source_path) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise ValueError('حجم عکس ({:.1f}MB) بیشتر از حد مجاز ({}MB) است.'.format(size_mb, MAX_SIZE_MB))

    # پوشه مقصد
    if target_dir:
        dest_dir = Path(target_dir)
    else:
        dest_dir = _default_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    # شماره ترتیبی
    if seq is None:
        seq = count + 1

    new_name = build_image_filename(doc_type, doc_id, person_id, person_name, seq, ext)
    dest = dest_dir / new_name

    # جلوگیری از بازنویسی فایل هم‌نام (اگر قبلاً همان شماره بود)
    n = 1
    while dest.exists():
        dest = dest_dir / '{}_{}{}'.format(new_name[: -len(ext)], n, ext)
        n += 1

    shutil.copy2(source_path, str(dest))

    # مسیر: اگر داخل پروژه بود نسبی، وگرنه مطلق
    cwd = os.getcwd() + os.sep
    if str(dest).startswith(cwd):
        rel_path = str(dest).replace(cwd, '')
    else:
        rel_path = str(dest)

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "INSERT INTO document_images "
        "(doc_type, doc_id, person_id, file_path, original_name, uploaded_at, uploaded_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_type, doc_id, person_id, rel_path, Path(source_path).name, now, uploaded_by),
    )
    conn.commit()

    img_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    return {
        'id': img_id,
        'doc_type': doc_type,
        'doc_id': doc_id,
        'person_id': person_id,
        'file_path': rel_path,
        'original_name': Path(source_path).name,
        'uploaded_at': now,
    }


def get_document_images(conn: sqlite3.Connection, doc_type: str, doc_id: int) -> List[Dict[str, Any]]:
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, doc_type, doc_id, person_id, file_path, original_name, uploaded_at "
        "FROM document_images WHERE doc_type = ? AND doc_id = ? ORDER BY id",
        (doc_type, doc_id),
    ).fetchall()
    return [
        {
            'id': r[0], 'doc_type': r[1], 'doc_id': r[2], 'person_id': r[3],
            'file_path': r[4], 'original_name': r[5], 'uploaded_at': r[6],
        }
        for r in rows
    ]


def delete_document_image(conn: sqlite3.Connection, img_id: int) -> bool:
    _ensure_table(conn)
    row = conn.execute("SELECT file_path FROM document_images WHERE id = ?", (img_id,)).fetchone()
    if not row:
        return False
    try:
        # اگر مسیر مطلق بود مستقیم، وگرنه نسبت به cwd
        p = row[0]
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass
    conn.execute("DELETE FROM document_images WHERE id = ?", (img_id,))
    conn.commit()
    return True


def get_person_documents(conn: sqlite3.Connection, person_id: int) -> List[Dict[str, Any]]:
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, doc_type, doc_id, person_id, file_path, original_name, uploaded_at "
        "FROM document_images WHERE person_id = ? ORDER BY id DESC",
        (person_id,),
    ).fetchall()
    return [
        {
            'id': r[0], 'doc_type': r[1], 'doc_id': r[2], 'person_id': r[3],
            'file_path': r[4], 'original_name': r[5], 'uploaded_at': r[6],
        }
        for r in rows
    ]
