# -*- coding: utf-8 -*-
"""ابزار مشاهده کاربران و ساخت کاربر تستی (مطابق ساختار واقعی)"""
import sqlite3
from pathlib import Path
from app.core.config import DB_PATH
from app.core.security import hash_password

DB_FILE = Path(DB_PATH)

def _conn():
    c = sqlite3.connect(str(DB_FILE)); c.row_factory = sqlite3.Row
    return c

def list_users():
    print("\n" + "="*90); print("لیست کاربران و دسترسی‌ها"); print("="*90)
    c = _conn()
    rows = c.execute("""
        SELECT u.id, u.username, u.full_name, r.code AS role_code, u.is_active,
          (SELECT GROUP_CONCAT(p.code, ', ') FROM role_permissions rp
           JOIN permissions p ON p.id=rp.permission_id WHERE rp.role_id=u.role_id) AS perms
        FROM users u LEFT JOIN roles r ON r.id=u.role_id ORDER BY u.id""").fetchall()
    for r in rows:
        print(f"[{r['id']}] {r['username']:<14} | {(r['full_name'] or '-'):<22} | "
              f"نقش: {r['role_code'] or '-':<10} | فعال: {'✓' if r['is_active'] else '✗'}")
        print(f"     دسترسی‌ها: {r['perms'] or '—'}")
    c.close()

def create_test_user():
    c = _conn()
    role = c.execute("SELECT id, code FROM roles WHERE code='ADMIN'").fetchone()
    if not role:
        role = c.execute("SELECT id, code FROM roles ORDER BY id LIMIT 1").fetchone()
    if not role:
        print("❌ هیچ نقشی تعریف نشده."); c.close(); return

    existing = c.execute("SELECT id FROM users WHERE username='test_admin'").fetchone()
    if existing:
        c.execute("UPDATE users SET password_hash=?, is_active=1, role_id=? WHERE username='test_admin'",
                  (hash_password('1234'), role['id']))
        c.commit(); c.close()
        print("✅ کاربر test_admin بود؛ رمز به '1234' ریست شد.")
        return

    c.execute("""INSERT INTO users
        (username, password_hash, full_name, role_id, is_active, created_at, updated_at)
        VALUES (?,?,?,?,1,datetime('now'),datetime('now'))""",
        ('test_admin', hash_password('1234'), 'کاربر تست (دسترسی کامل)', role['id']))
    c.commit(); c.close()
    print("\n✅ کاربر تستی ساخته شد:")
    print("   نام کاربری: test_admin")
    print("   رمز عبور:   1234")
    print(f"   نقش:        {role['code']}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        create_test_user()
    else:
        list_users()
        print("\n💡 ساخت کاربر تستی: py -X utf8 user_manager_tool.py create")
