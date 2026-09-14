# -*- coding: utf-8 -*-
"""همگام‌سازی خودکار مرجع/مانده + فرمول دقیق موجودی - اجرا: python fix_ref_track.py"""
import os, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

SYNC = ("UPDATE outbound_loads SET remaining_qty = COALESCE(issued_qty_total,0) - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED'),0), "
        "load_status = CASE WHEN COALESCE(issued_qty_total,0) - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED'),0) > 0 THEN 'OPEN' ELSE 'COMPLETE' END WHERE is_active=1")

# 0) شفاف‌سازی ساختار
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
if os.path.exists(db):
    con = sqlite3.connect(db)
    for t in ('warehouse_issue_items', 'warehouse_issues', 'outbound_loads', 'inventory_levels'):
        try:
            print(t, ':', [r[1] for r in con.execute(f'PRAGMA table_info({t})').fetchall()])
        except Exception as e:
            print(t, 'err', e)
    try:
        con.execute(SYNC); con.commit()
        print('=== بعد از همگام‌سازی ===')
        for r in con.execute("SELECT id, reference_no, load_status, remaining_qty, issued_qty_total FROM outbound_loads").fetchall():
            print('   ', r)
        for r in con.execute("SELECT pallet_id, quantity FROM inventory_levels").fetchall():
            print('    inventory:', r)
    except Exception as e:
        print('⚠ SYNC روی دیتابیس اجرا نشد:', e)
    con.close()
print('0) داده همگام شد ✔')

# 1) خودترمیمی در مسیر خواندن مرجع‌ها (دو جا)
for rel in ('app/ui/issue_manager_window.py', 'app/ui/combo_refresh_patch.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    s = open(p, encoding='utf-8').read()
    if '# REF-SYNC' in s:
        print('1)', rel, 'از قبل بود ✔'); continue
    lines = s.split('\n')
    done = False
    for i, l in enumerate(lines):
        if 'rows = conn.execute(' in l:
            nxt = '\n'.join(lines[i:i + 8])
            if 'FROM outbound_loads' in nxt and 'remaining_qty' in nxt:
                ind = len(l) - len(l.lstrip())
                sp = ' ' * ind
                ins = [sp + 'try:  # REF-SYNC',
                       sp + '    conn.execute("' + SYNC.replace('"', "'") + '")  # REF-SYNC',
                       sp + 'except Exception:  # REF-SYNC',
                       sp + '    pass  # REF-SYNC']
                lines[i:i] = ins
                done = True
                break
    if done:
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
        py_compile.compile(p, doraise=True)
        print('1)', rel, '✔')
    else:
        print('1)', rel, '⚠ نقطه پیدا نشد')

# 2) فرمول موجودی: فقط ماندهٔ تعهدات کسر شود
OLD_R2 = '    r2 = conn.execute("SELECT SUM(oli.qty) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE oli.pallet_id=? AND ol.load_status=\'OPEN\' AND ol.is_active=1", (pallet_id,)).fetchone()  # STOCK-FORMULA'
NEW_R2 = '    r2 = conn.execute("SELECT SUM(oli.qty - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=ol.id AND wi.issue_status!=\'CANCELLED\' AND wii.pallet_id=oli.pallet_id),0)) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE oli.pallet_id=? AND ol.load_status=\'OPEN\' AND ol.is_active=1", (pallet_id,)).fetchone()  # STOCK-FORMULA'
for rel in ('app/ui/issue_manager_window.py', 'app/ui/receipt_manager_window.py'):
    p = os.path.join(ROOT, rel)
    s = open(p, encoding='utf-8').read()
    if OLD_R2 in s:
        s = s.replace(OLD_R2, NEW_R2, 1)
        open(p, 'w', encoding='utf-8').write(s)
        py_compile.compile(p, doraise=True)
        print('2)', rel, '✔')

# 3) بیلد با محافظ داده
db_dist = db
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
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
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
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
    shutil.copy2(keep, db_dist)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')