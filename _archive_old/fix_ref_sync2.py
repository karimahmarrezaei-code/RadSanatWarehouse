# -*- coding: utf-8 -*-
"""اصلاح فرمول همگام‌سازی: کل بار از اقلام - اجرا: python fix_ref_sync2.py"""
import os, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

OLD_PLAN = "COALESCE(issued_qty_total,0)"
NEW_PLAN = "(SELECT COALESCE(SUM(qty),0) FROM outbound_load_items oli2 WHERE oli2.outbound_load_id=outbound_loads.id)"

# 1) ترمیم داده با فرمول درست
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
ISS = "COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED'),0)"
SYNC = f"UPDATE outbound_loads SET remaining_qty = {NEW_PLAN} - {ISS}, load_status = CASE WHEN {NEW_PLAN} - {ISS} > 0 THEN 'OPEN' ELSE 'COMPLETE' END WHERE is_active=1"
if os.path.exists(db):
    con = sqlite3.connect(db)
    try:
        con.execute(SYNC); con.commit()
        print('=== بعد از ترمیم ===')
        for r in con.execute("SELECT id, reference_no, load_status, remaining_qty FROM outbound_loads").fetchall():
            print('   ', r)
    except Exception as e:
        print('⚠', e)
    con.close()
print('1) داده ترمیم شد ✔')

# 2) اصلاح همان خط‌های REF-SYNC در کد
for rel in ('app/ui/issue_manager_window.py', 'app/ui/combo_refresh_patch.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = open(p, encoding='utf-8').read().split('\n')
    n = 0
    for i, l in enumerate(lines):
        if '# REF-SYNC' in l and OLD_PLAN in l:
            lines[i] = l.replace(OLD_PLAN, NEW_PLAN)
            n += 1
    if n:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
    print('2)', rel, 'اصلاح خط‌ها:', n)

# 3) بیلد با محافظ داده
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('3) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel2 = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel2)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
good = os.path.join(ROOT, 'theme_manager.py')
if os.path.exists(good):
    for tgt in (os.path.join(DST, 'theme_manager.py'),
                os.path.join(DST, '_internal', 'theme_manager.py'),
                os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')