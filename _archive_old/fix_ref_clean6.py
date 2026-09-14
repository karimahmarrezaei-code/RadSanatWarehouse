# -*- coding: utf-8 -*-
"""ترمیم رمزگذاری متن برچسب - اجرا: python fix_ref_clean6.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

PLANNED = "(SELECT COALESCE(SUM(qty), 0) FROM outbound_load_items WHERE outbound_load_id = ol.id)"
ISSUED = ("(SELECT COALESCE(SUM(wii.qty), 0) FROM warehouse_issue_items wii "
          "JOIN warehouse_issues wi ON wi.id = wii.issue_id "
          "WHERE wi.outbound_load_id = ol.id AND wi.issue_status != 'CANCELLED')")

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

def swap_balanced(text, start_idx):
    depth = 0
    for j in range(start_idx, len(text)):
        if text[j] == '(':
            depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0:
                return text[:start_idx] + ISSUED + text[j + 1:], True
    return text, False

# 1) پایه سالم با رمز درست
g = subprocess.run(['git', 'show', 'HEAD:app/ui/issue_manager_window.py'], capture_output=True)
bl = g.stdout.decode('utf-8', errors='replace').split('\n')
bs, be = extract_func(bl, '_refresh_reference_combo')
if bs is None:
    print('❌ تابع در گیت نیست'); input(); raise SystemExit
btext = '\n'.join(bl[bs:be])
btext, n1 = re.subn(r'COALESCE\(ol\.total_load_qty,\s*0\)', PLANNED, btext)
k = btext.find(PLANNED)
k2 = btext.find('(SELECT', k + len(PLANNED)) if k != -1 else -1
ok2 = False
if k2 != -1:
    btext, ok2 = swap_balanced(btext, k2)
print('1) تعویض‌ها:', n1, ok2)
for l in btext.split('\n'):
    if 'label' in l or 'format(' in l:
        print('   برچسب:', l.strip()[:110])

# 2) جایگزینی تابع فعلی
p = os.path.join(ROOT, 'app/ui/issue_manager_window.py')
cur = open(p, encoding='utf-8').read().split('\n')
cs, ce = extract_func(cur, '_refresh_reference_combo')
if cs is None:
    print('❌ تابع فعلی نیست'); input(); raise SystemExit
cur[cs:ce] = btext.split('\n')

# 3) جاروب له‌شدگی رمز در کل فایل
n2 = 0
for i, l in enumerate(cur):
    if 'ظ…' in l or 'ط§' in l:
        try:
            cand = l.encode('cp1256').decode('utf-8')
            if cand != l and 'ظ…' not in cand:
                cur[i] = cand
                n2 += 1
        except Exception:
            pass
print('2) خطوط ترمیم‌شده رمز:', n2)
open(p, 'w', encoding='utf-8').write('\n'.join(cur))
py_compile.compile(p, doraise=True)
print('3) کامپایل سالم ✔')

# 4) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('4) بیلد...')
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
    print('4) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('5) تمام ✔')
input('Enter...')