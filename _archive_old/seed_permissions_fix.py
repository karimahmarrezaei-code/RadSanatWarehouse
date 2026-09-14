# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from app.core.config import DB_PATH

PERMS = [
    ('dashboard.view', 'مشاهده داشبورد', 'داشبورد'),
    ('users.view', 'مشاهده کاربران', 'سیستم'),
    ('users.manage', 'مدیریت کاربران', 'سیستم'),
    ('roles.manage', 'مدیریت نقش‌ها', 'سیستم'),
    ('audit.view', 'گزارش فعالیت کاربران', 'سیستم'),
    ('backup.manage', 'پشتیبان‌گیری / بازگردانی', 'سیستم'),
    ('warehouses.view', 'مشاهده انبارها', 'انبار'),
    ('warehouses.manage', 'مدیریت انبارها', 'انبار'),
    ('pallets.view', 'مشاهده پالت‌ها', 'انبار'),
    ('pallets.manage', 'مدیریت پالت‌ها', 'انبار'),
    ('openings.manage', 'افتتاحیه انبار', 'انبار'),
    ('stock_take.manage', 'انبارگردانی', 'انبار'),
    ('persons.view', 'مشاهده اشخاص', 'اشخاص'),
    ('persons.manage', 'مدیریت اشخاص', 'اشخاص'),
    ('receipts.view', 'مشاهده رسیدها', 'عملیات'),
    ('receipts.manage', 'ثبت رسید (خرید)', 'عملیات'),
    ('issues.view', 'مشاهده حواله‌ها', 'عملیات'),
    ('issues.manage', 'ثبت حواله (فروش)', 'عملیات'),
    ('returns.manage', 'برگشت کالا', 'عملیات'),
    ('proforma.manage', 'پیش‌فاکتور', 'عملیات'),
    ('finance.view', 'مشاهده اسناد مالی', 'مالی / حسابداری'),
    ('finance.manage', 'ثبت اسناد مالی', 'مالی / حسابداری'),
    ('treasury.manage', 'صندوق / بانک', 'مالی / حسابداری'),
    ('expenses.manage', 'ثبت هزینه', 'مالی / حسابداری'),
    ('ledger.view', 'دفتر کل و معین', 'مالی / حسابداری'),
    ('balance_sheet.view', 'ترازنامه', 'مالی / حسابداری'),
    ('bank_reconciliation.manage', 'مغایرت بانکی', 'مالی / حسابداری'),
    ('checkbook.manage', 'دفترچه چک', 'مالی / حسابداری'),
    ('reports.view', 'مشاهده گزارش‌ها', 'گزارش‌ها'),
    ('pnl.view', 'سود و زیان', 'گزارش‌ها'),
    ('aging.view', 'سن بدهی‌ها', 'گزارش‌ها'),
]

conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
added = 0
for code, name, module in PERMS:
    if not conn.execute("SELECT id FROM permissions WHERE code=?", (code,)).fetchone():
        action = code.split('.')[-1]
        conn.execute(
            "INSERT INTO permissions (code, name, module_name, action_name, description, created_at) "
            "VALUES (?,?,?,?,?,datetime('now'))",
            (code, name, module, action, name))
        added += 1
conn.commit()
print(f'✅ {added} دسترسی اضافه شد. فهرست کامل:')
for r in conn.execute("SELECT module_name, code, name FROM permissions ORDER BY module_name, name"):
    print(f"  [{r['module_name']}] {r['code']:<28} {r['name']}")
conn.close()