# -*- coding: utf-8 -*-
"""
db_consistency.py - بررسی تناقض‌های دیتابیس (اشخاص و ارتباطات)

این اسکریپت نشان می‌دهد:
  ۱) چند شخص در جدول persons هست و چندتا نقش دارند
  ۲) کدام جدول‌ها به اشخاص ارجاع می‌دهند (person_id / *_person_id / counterparty_person_id)
  ۳) ارجاع‌هایی که به شخصی که وجود ندارد (یتیم) یا به شخص بدون نقش اشاره می‌کنند
  ۴) تناقض بین bank_accounts و persons
  ۵) اسنادی که counterparty_person_id ندارند یا شخصشان نقشی ندارد

استفاده:
    py -X utf8 db_consistency.py
"""
import os
import sqlite3

DB_CANDIDATES = ['data/app.db', 'app.db', 'data/appdb', 'appdb']


def main():
    db = next((c for c in DB_CANDIDATES if os.path.exists(c)), None)
    if not db:
        print('دیتابیس پیدا نشد')
        return
    print('دیتابیس:', db)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    # ۱) آمار پایه
    print('\n=== ۱) آمار پایه ===')
    for t in ['persons', 'person_roles', 'bank_accounts', 'financial_documents',
              'inbound_loads', 'outbound_loads', 'warehouse_receipts', 'warehouse_issues',
              'payment_entries', 'cash_accounts', 'treasury_accounts']:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            print(f'  {t}: {c}')
        except Exception as e:
            print(f'  {t}: (خطا: {e})')

    # ۲) اشخاص بدون نقش
    print('\n=== ۲) اشخاص بدون نقش ===')
    no_role = conn.execute("""
        SELECT p.id, p.first_name, p.last_name FROM persons p
        WHERE NOT EXISTS (SELECT 1 FROM person_roles pr WHERE pr.person_id = p.id)
        ORDER BY p.id
    """).fetchall()
    for r in no_role:
        print(f"  شخص {r['id']} ({r['first_name'] or ''} {r['last_name'] or ''}) — بدون نقش")
    if not no_role:
        print('  (هیچ — همه اشخاص نقش دارند)')

    # ۳) ارجاع‌های یتیم به اشخاص
    print('\n=== ۳) ارجاع‌های یتیم (به شخصی که وجود ندارد) ===')
    checks = [
        ('financial_documents', 'counterparty_person_id'),
        ('inbound_loads', 'supplier_id'),
        ('inbound_loads', 'driver_id'),
        ('outbound_loads', 'customer_id'),
        ('outbound_loads', 'driver_id'),
        ('warehouse_receipts', 'supplier_id'),
        ('warehouse_receipts', 'driver_id'),
        ('warehouse_issues', 'customer_id'),
        ('warehouse_issues', 'driver_id'),
        ('payment_entries', 'payer_payee_person_id'),
        ('bank_accounts', 'person_id'),
    ]
    total_orphans = 0
    for table, col in checks:
        try:
            orphans = conn.execute(
                f"SELECT COUNT(*) FROM {table} t "
                f"LEFT JOIN persons p ON p.id = t.{col} "
                f"WHERE t.{col} IS NOT NULL AND p.id IS NULL"
            ).fetchone()[0]
            if orphans:
                total_orphans += orphans
                print(f'  ⚠️ {table}.{col}: {orphans} ارجاع به شخص ناموجود')
        except Exception as e:
            pass
    if not total_orphans:
        print('  (هیچ ارجاع یتیمی نیست ✅)')

    # ۴) بانک‌ها: تناقض
    print('\n=== ۴) تناقض bank_accounts ===')
    bank_orphan = conn.execute("""
        SELECT ba.id, ba.person_id FROM bank_accounts ba
        LEFT JOIN persons p ON p.id = ba.person_id
        WHERE p.id IS NULL
    """).fetchall()
    for r in bank_orphan:
        print(f"  ⚠️ bank_accounts id={r['id']} → person_id={r['person_id']} (شخص ناموجود)")
    if not bank_orphan:
        print('  همه bank_accounts به شخص معتبر وصلاند ✅')

    # ۵) اسناد بدون شخص یا شخص بدون نقش
    print('\n=== ۵) اسناد بدون counterparty_person_id یا شخص بی‌نقش ===')
    bad = conn.execute("""
        SELECT fd.id, fd.finance_no, fd.counterparty_person_id,
               CASE WHEN fd.counterparty_person_id IS NULL THEN 'بدون شخص'
                    WHEN NOT EXISTS (SELECT 1 FROM persons p WHERE p.id = fd.counterparty_person_id) THEN 'شخص ناموجود'
                    WHEN NOT EXISTS (SELECT 1 FROM person_roles pr WHERE pr.person_id = fd.counterparty_person_id) THEN 'شخص بدون نقش'
                    ELSE 'OK' END AS status
        FROM financial_documents fd
        WHERE fd.counterparty_person_id IS NULL
           OR NOT EXISTS (SELECT 1 FROM persons p WHERE p.id = fd.counterparty_person_id)
           OR NOT EXISTS (SELECT 1 FROM person_roles pr WHERE pr.person_id = fd.counterparty_person_id)
        ORDER BY fd.id
    """).fetchall()
    for r in bad:
        print(f"  ⚠️ سند#{r['id']} {r['finance_no']} شخص={r['counterparty_person_id']} → {r['status']}")
    if not bad:
        print('  (همه اسناد شخص معتبر و دارای نقش دارند ✅)')

    # ۶) اسناد دارای شخص ولی بدون بانک
    print('\n=== ۶) اسنادی که شخص‌شان در bank_accounts بانک ندارد ===')
    nobank = conn.execute("""
        SELECT DISTINCT fd.counterparty_person_id, p.first_name, p.last_name,
               (SELECT COUNT(*) FROM financial_documents f2 WHERE f2.counterparty_person_id = fd.counterparty_person_id) AS cnt
        FROM financial_documents fd
        LEFT JOIN persons p ON p.id = fd.counterparty_person_id
        WHERE fd.counterparty_person_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM bank_accounts ba WHERE ba.person_id = fd.counterparty_person_id)
        ORDER BY fd.counterparty_person_id
    """).fetchall()
    for r in nobank:
        print(f"  شخص {r['counterparty_person_id']} ({r['first_name'] or ''} {r['last_name'] or ''}) "
              f"— {r['cnt']} سند — بدون بانک")
    if not nobank:
        print('  (همه اشخاصِ دارای سند، بانک دارند ✅)')

    conn.close()
    print()
    print('== پایان بررسی ==')


if __name__ == '__main__':
    main()
