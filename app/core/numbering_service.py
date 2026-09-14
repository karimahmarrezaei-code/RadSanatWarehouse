# -*- coding: utf-8 -*-
"""
numbering_service.py - کلاس مرکزی شماره‌گذاری (ایده کاربر)

همه فرم‌ها (رسید، حواله، پیش‌فاکتور، برگشت) از این کلاس استفاده می‌کنند
تا شماره بگیرند — یک نقطه کنترل واحد.

فرمت:  PREFIX-سال-PERSON-سریال
مثال:  RC-1405-001-0001

قوانین:
  - سریال برای هر پرسنل جدا از 0001
  - پیش‌نمایش (peek) جلو نمی‌برد
  - ثبت واقعی (next) جلو می‌برد
  - مرجع بار (WH/EX) بدون پرسنل
  - اگر conn داده نشود، خودش اتصال را باز می‌کند و می‌بندد
"""
from typing import Optional


class NumberingService:
    """کلاس مرکزی شماره‌گذاری اسناد"""

    # ─── دیکشنری پیکربندی انواع سند ───
    CONFIG = {
        'RECEIPT':      {'prefix': 'RC', 'person': 'supplier_id', 'label': 'رسید ورود'},
        'ISSUE':        {'prefix': 'IS', 'person': 'customer_id', 'label': 'حواله خروج'},
        'PROFORMA':     {'prefix': 'PR', 'person': 'customer_id', 'label': 'پیش‌فاکتور'},
        'RETURN_BUY':   {'prefix': 'BR', 'person': 'supplier_id', 'label': 'برگشت از خرید'},
        'RETURN_SALE':  {'prefix': 'BS', 'person': 'customer_id', 'label': 'برگشت از فروش'},
        'LOAD_IN':      {'prefix': 'WH', 'person': None, 'label': 'مرجع بار ورود'},
        'LOAD_OUT':     {'prefix': 'EX', 'person': None, 'label': 'مرجع بار خروج'},
    }

    # ─── متدهای کمکی ───

    @classmethod
    def config(cls, doc_type: str) -> dict:
        """پیکربندی یک نوع سند"""
        if doc_type not in cls.CONFIG:
            raise ValueError('نوع سند ناشناخته: {}'.format(doc_type))
        return cls.CONFIG[doc_type]

    @classmethod
    def _import_utils(cls):
        """import محلی sequence_utils (جلوگیری از وابستگی چرخشی)"""
        from app.core.sequence_utils import next_sequence_no, peek_sequence_no
        return next_sequence_no, peek_sequence_no

    @classmethod
    def _resolve_conn(cls, conn):
        """اگر conn داده نشده بود خودش اتصال را باز می‌کند.
        خروجی: (اتصال, آیا خودش باز کرده؟)"""
        if conn is not None:
            return conn, False
        from app.core import database as _dbmod
        _cls = None
        for _name in ('DatabaseManager', 'Database', 'AppDatabase', 'SQLiteDatabase'):
            _cls = getattr(_dbmod, _name, None)
            if _cls is not None:
                break
        if _cls is None:
            raise RuntimeError('کلاس دیتابیس در app/core/database.py پیدا نشد')
        _conn = _cls().connect()
        try:
            _conn.row_factory = None
        except Exception:
            pass
        return _conn, True

    @classmethod
    def _finish(cls, conn, own, commit):
        """بستن اتصالی که خودش باز کرده (با commit در صورت نیاز)"""
        if not own:
            return
        if commit:
            try:
                conn.commit()
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

    # ─── API اصلی ───

    @classmethod
    def next(cls, doc_type: str, conn, iso_date: str = None,
             person_id: Optional[int] = None) -> str:
        """شماره بعدی (ثبت واقعی — شمارنده جلو می‌رود)"""
        cfg = cls.config(doc_type)
        next_seq, _ = cls._import_utils()
        pid = person_id if cfg['person'] is not None else None
        _conn, own = cls._resolve_conn(conn)
        try:
            return next_seq(_conn, cfg['prefix'], iso_date=iso_date, personnel_id=pid)
        finally:
            cls._finish(_conn, own, commit=True)

    @classmethod
    def peek(cls, doc_type: str, conn, iso_date: str = None,
             person_id: Optional[int] = None) -> str:
        """شماره پیش‌نمایش (جلو نمی‌برد)"""
        cfg = cls.config(doc_type)
        _, peek_seq = cls._import_utils()
        pid = person_id if cfg['person'] is not None else None
        _conn, own = cls._resolve_conn(conn)
        try:
            return peek_seq(_conn, cfg['prefix'], iso_date=iso_date, personnel_id=pid)
        finally:
            cls._finish(_conn, own, commit=False)

    @classmethod
    def next_for_payload(cls, doc_type: str, conn, payload: dict,
                         iso_date: str = None) -> str:
        """شماره بعدی — پرسنل را خودش از payload می‌گیرد"""
        cfg = cls.config(doc_type)
        person_field = cfg['person']
        person_id = payload.get(person_field) if person_field else None
        return cls.next(doc_type, conn, iso_date=iso_date, person_id=person_id)

    # ─── ابزارها ───

    @classmethod
    def summary(cls) -> str:
        """نمایش خلاصه پیکربندی"""
        lines = []
        for key, cfg in cls.CONFIG.items():
            person = cfg['person'] or '—'
            lines.append('  {:12s} → {}-سال-{}-سریال  ({})'.format(
                key, cfg['prefix'], person, cfg['label']))
        return '\n'.join(lines)
