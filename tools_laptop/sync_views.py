# -*- coding: utf-8 -*-
"""ساخت اسکریپت اعمال ویوها برای لپ‌تاپ - اجرا: python sync_views.py"""
import os, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(os.path.join(ROOT, 'data', 'app.db'))
views = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='view' AND sql IS NOT NULL").fetchall()
conn.close()
print('ویوهای یافت‌شده:', [v[0] for v in views])

out = ['# -*- coding: utf-8 -*-',
       '"""اعمال ویوهای جدید روی لپ‌تاپ - فقط روی لپ‌تاپ اجرا شود"""',
       'import os, sqlite3',
       'p = None',
       'for c in (r"D:\\warehouse_app\\_internal\\data\\app.db", r"D:\\warehouse_app\\data\\app.db"):',
       '    if os.path.exists(c):',
       '        p = c',
       '        break',
       "print('دیتابیس:', p)",
       'conn = sqlite3.connect(p)']
for name, sql in views:
    out.append('conn.execute("DROP VIEW IF EXISTS {}")'.format(name))
    out.append('conn.execute("""{}""")'.format(sql))
out.append('conn.commit()')
out.append("print('✔ ویوها اعمال شد: " + str(len(views)) + " ویو')")
out.append('conn.close()')
out.append("input('Enter...')")

open(os.path.join(ROOT, 'apply_views_laptop.py'), 'w', encoding='utf-8').write('\n'.join(out))
print('✔ apply_views_laptop.py ساخته شد — با فلش به لپ‌تاپ ببرید')
input('Enter...')