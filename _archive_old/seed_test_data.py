# -*- coding: utf-8 -*-
import sqlite3
from app.core.database import DatabaseManager
conn = sqlite3.connect(getattr(DatabaseManager(), 'db_path', None))
conn.row_factory = sqlite3.Row
cur = conn.cursor()
NOW = "datetime('now')"

sup = [('رضا','کریمی'),('محمد','احمدی'),('علی','محمدی'),('حسن','رضایی'),('مهدی','موسوی')]
cus = [('شرکت','پالت سازان'),('شرکت','چوب شمال'),('امیر','قاسمی'),('شرکت','بسته بندی آریا'),('سعید','نادری')]
sup_ids, cus_ids = [], []
for f, l in sup:
    cur.execute(f"INSERT INTO persons (first_name,last_name,role,is_active,created_at,updated_at) VALUES (?,?, 'SUPPLIER',1,{NOW},{NOW})", (f, l))
    sid = cur.lastrowid; sup_ids.append(sid)
    cur.execute(f"INSERT INTO person_roles (person_id,role_type,created_at) VALUES (?,?,{NOW})", (sid, 'SUPPLIER'))
for f, l in cus:
    cur.execute(f"INSERT INTO persons (first_name,last_name,role,is_active,created_at,updated_at) VALUES (?,?, 'CUSTOMER',1,{NOW},{NOW})", (f, l))
    cid = cur.lastrowid; cus_ids.append(cid)
    cur.execute(f"INSERT INTO person_roles (person_id,role_type,created_at) VALUES (?,?,{NOW})", (cid, 'CUSTOMER'))

acc = {r['code']: r['id'] for r in cur.execute("SELECT code,id FROM ledger_accounts")}

def post(no, date, desc, lines):
    cur.execute(f"INSERT INTO journal_entries (entry_no,entry_date,reference_type,description,created_at,created_by) VALUES (?,?,?,?,{NOW},1)", (no, date, 'MANUAL', desc))
    eid = cur.lastrowid
    for i, (code, d, c, pid) in enumerate(lines, 1):
        cur.execute("INSERT INTO journal_lines (journal_entry_id,line_no,account_id,person_id,debit_amount,credit_amount,description) VALUES (?,?,?,?,?,?,?)", (eid, i, acc[code], pid, d, c, desc))

M = 1_000_000
post('JE-0001', '2025-09-01', 'خرید نسیه پالت از تامین‌کننده', [('1000',500*M,0,None),('2100',0,500*M,sup_ids[0])])
post('JE-0002', '2025-09-10', 'پرداخت بخشی از بدهی به تامین‌کننده از بانک', [('2100',300*M,0,sup_ids[0]),('1200',0,300*M,None)])
post('JE-0003', '2025-09-15', 'خرید نسیه از تامین‌کننده دوم', [('1000',400*M,0,None),('2100',0,400*M,sup_ids[1])])
post('JE-0004', '2025-10-01', 'فروش نسیه به مشتری اول', [('2200',600*M,0,cus_ids[0]),('4000',0,600*M,None)])
post('JE-0005', '2025-10-12', 'دریافت وجه از مشتری اول به صندوق', [('1100',250*M,0,None),('2200',0,250*M,cus_ids[0])])
post('JE-0006', '2025-10-20', 'فروش نسیه به مشتری دوم', [('2200',700*M,0,cus_ids[1]),('4000',0,700*M,None)])
post('JE-0007', '2025-11-05', 'پرداخت هزینه حمل', [('5000',50*M,0,None),('1100',0,50*M,None)])
post('JE-0008', '2025-11-15', 'تسویه بدهی تامین‌کننده دوم از بانک', [('2100',400*M,0,sup_ids[1]),('1200',0,400*M,None)])
post('JE-0009', '2025-12-01', 'دریافت وجه از مشتری دوم به بانک', [('1200',300*M,0,None),('2200',0,300*M,cus_ids[1])])
post('JE-0010', '2026-01-10', 'خرید نسیه از تامین‌کننده سوم', [('1000',350*M,0,None),('2100',0,350*M,sup_ids[2])])

conn.commit(); conn.close()
print('✅ ۵ تامین‌کننده + ۵ مشتری + ۱۰ سند حسابداری ثبت شد.')