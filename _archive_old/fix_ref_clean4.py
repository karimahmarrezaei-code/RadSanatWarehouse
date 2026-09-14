# -*- coding: utf-8 -*-
"""تعویض کامل reload_open_references از پایه سالم - اجرا: python fix_ref_clean4.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

SYNC_ONE = ("UPDATE outbound_loads SET remaining_qty = "
            "(SELECT COALESCE(SUM(qty),0) FROM outbound_load_items oli2 WHERE oli2.outbound_load_id=outbound_loads.id) - "
            "(SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id "
            "WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED'), "
            "load_status = CASE WHEN (SELECT COALESCE(SUM(qty),0) FROM outbound_load_items oli2 WHERE oli2.outbound_load_id=outbound_loads.id) - "
            "(SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id "
            "WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED') > 0 THEN 'OPEN' ELSE 'COMPLETE' END "
            "WHERE is_active=1")

def extract_func(lines, name):
    s = None
    for i, l in enumerate(lines):
        if l.strip().startswith('def ' + name):
            s = i
            break
    if s is None:
        return None, None
    ind = len(lines[s]) - len(lines[s].lstrip())
    e = len(lines)
    for j in range(s + 1, len(lines)):
        lj = lines[j]
        if lj.strip() and (len(lj) - len(lj.lstrip())) == ind and lj.lstrip().startswith('def '):
            e = j
            break
    return s, e

# 1) تابع سالم از گیت
g = subprocess.run(['git', 'show', 'HEAD:app/ui/issue_manager_window.py'], capture_output=True, text=True)
if g.returncode != 0:
    print('❌ گیت نیست'); input(); raise SystemExit
bl = g.stdout.split('\n')
bs, be = extract_func(bl, 'reload_open_references')
if bs is None:
    print('❌ تابع در گیت نیست'); input(); raise SystemExit
btext = '\n'.join(bl[bs:be])

# 2) ساده‌سازی شرط: فقط مانده>0
i = btext.find('AND (remaining_qty > 0')
if i != -1:
    j = btext.find('(', i + 4)
    depth = 0
    k = j
    for k in range(j, len(btext)):
        if btext[k] == '(':
            depth += 1
        elif btext[k] == ')':
            depth -= 1
            if depth == 0:
                break
    btext = btext[:i] + 'AND remaining_qty > 0 ' + btext[k + 1:]
    print('1) شرط ساده شد ✔')

# 3) درج REF-SYNC قبل از خواندن
lb = btext.split('\n')
for idx, l in enumerate(lb):
    if 'rows = conn.execute(' in l:
        ind = len(l) - len(l.lstrip())
        sp = ' ' * ind
        lb[idx:idx] = [sp + 'try:  # REF-SYNC',
                       sp + '    conn.execute("' + SYNC_ONE + '")  # REF-SYNC',
                       sp + 'except Exception:  # REF-SYNC',
                       sp + '    pass  # REF-SYNC']
        print('2) REF-SYNC داخل تابع ✔')
        break
btext = '\n'.join(lb)

# 4) جایگزینی کل تابع خراب فعلی
p = os.path.join(ROOT, 'app/ui/issue_manager_window.py')
cur = open(p, encoding='utf-8').read().split('\n')
cs, ce = extract_func(cur, 'reload_open_references')
if cs is None:
    print('❌ تابع فعلی نیست'); input(); raise SystemExit
print('3) تابع فعلی خطوط', cs + 1, 'تا', ce, 'جایگزین شد')
cur[cs:ce] = btext.split('\n')

# 5) جاروب خط‌های شکستهٔ باقی‌مانده
bad = [i for i, l in enumerate(cur) if l.strip().startswith('(SELECT') and 'REF-CLEAN' in l]
if bad:
    print('⚠ خط‌های شکسته:', [b + 1 for b in bad])
open(p, 'w', encoding='utf-8').write('\n'.join(cur))
py_compile.compile(p, doraise=True)
print('4) کامپایل سالم ✔')

# 6) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('5) بیلد...')
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
    print('5) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('6) تمام ✔')
input('Enter...')