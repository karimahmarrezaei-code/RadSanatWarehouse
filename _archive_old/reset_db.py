# -*- coding: utf-8 -*-
import sqlite3, shutil, os
from app.core.config import DB_PATH
from app.core.jalali import today_iso_date

# بک‌آپ ایمن قبل از ریست
bak = str(DB_PATH).replace('.db', f'_backup_{today_iso_date()}.db')
shutil.copy2(str(DB_PATH), bak)
print('✅ بک‌آپ ساخته شد:', bak)

# جدول‌هایی که باید بمانند (ادمین، نقش‌ها، دسترسی‌ها، تنظیمات)
KEEP = {'users', 'roles', 'permissions', 'role_permissions', 'payment_methods',
        'expense_categories', 'company', 'company_profile', 'settings', 'preferences'}

conn = sqlite3.connect(str(DB_PATH))
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
cleared = []
for t in tables:
    if t in KEEP:
        continue
    try:
        conn.execute(f"DELETE FROM {t}")
        # ریست شمارنده‌ها → شماره‌های مرجع (پیش‌فاکتور/رسید/حواله) از ۱ شروع می‌شوند
        conn.execute("DELETE FROM sqlite_sequence WHERE name=?", (t,))
        cleared.append(t)
    except Exception as e:
        print('رد شد:', t, e)
conn.commit()
conn.close()
print('✅ ریست کامل شد. جدول‌های پاک‌شده:', len(cleared))