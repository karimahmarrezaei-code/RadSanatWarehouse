# -*- coding: utf-8 -*-
import os

def find_db():
    base = os.path.dirname(os.path.abspath(__file__))
    for b in (base, os.path.dirname(base)):
        for p in (os.path.join(b, '_internal', 'data', 'app.db'),
                  os.path.join(b, 'data', 'app.db')):
            if os.path.exists(p):
                return p
    return None

"""مهاجرت CHECK اسناد مالی (PAYROLL) - لپ‌تاپ"""
import re, sqlite3

dbp = find_db()
print('دیتابیس:', dbp)
c = sqlite3.connect(dbp)
c.isolation_level = None
views = [(r[0], r[1]) for r in c.execute(
    "SELECT name, sql FROM sqlite_master WHERE type='view' AND sql IS NOT NULL")]
c.execute('BEGIN')
try:
    for name, _ in views:
        c.execute('DROP VIEW IF EXISTS "{}"'.format(name))
    c.execute('DROP TABLE IF EXISTS financial_documents_new')
    sql = c.execute("SELECT sql FROM sqlite_master WHERE name='financial_documents'").fetchone()[0]
    if 'PAYROLL' not in sql:
        new_sql = sql.replace("'OUTBOUND_FREIGHT')", "'OUTBOUND_FREIGHT', 'PAYROLL', 'EXPENSE')", 1)
        new_sql = re.sub(r'CREATE TABLE (IF NOT EXISTS )?financial_documents',
                         'CREATE TABLE financial_documents_new', new_sql, count=1)
        cols = [r[1] for r in c.execute('PRAGMA table_info(financial_documents)')]
        cl = ', '.join(cols)
        c.execute(new_sql)
        c.execute('INSERT INTO financial_documents_new ({}) SELECT {} FROM financial_documents'.format(cl, cl))
        c.execute('DROP TABLE financial_documents')
        c.execute('ALTER TABLE financial_documents_new RENAME TO financial_documents')
        print('✔ PAYROLL اضافه شد')
    else:
        print('· از قبل داشت')
    for name, sqlv in views:
        c.execute(sqlv)
    c.execute('COMMIT')
    print('✔ مهاجرت کامل شد')
except Exception as e:
    c.execute('ROLLBACK')
    print('❌ برگشت کامل:', str(e)[:120])
c.close()
input('Enter...')
