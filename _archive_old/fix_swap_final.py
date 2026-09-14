# -*- coding: utf-8 -*-
"""جای کد/ابعاد + پایداری پیش‌نمایش + رفع خطای ref_no + ماندهٔ دقیق - اجرا: python fix_swap_final.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) جابجایی کد و ابعاد در متن کامبو
for rel in ('app/ui/issue_manager_window.py', 'app/ui/receipt_manager_window.py',
            'app/ui/opening_inventory_window.py', 'app/ui/proforma_window.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    s = open(p, encoding='utf-8').read()
    print('=' * 20, rel)
    for l in s.split('\n'):
        if 'موجودی آزاد' in l:
            print('   قبل:', l.strip()[:110])
    pat = re.compile(r'("\{\} \| \{\} \| \{\} \(موجودی آزاد: \{:,}\)"\.format\()([^,]+), ([^,]+),')
    s2, n = pat.subn(lambda m: m.group(1) + m.group(3).strip() + ', ' + m.group(2).strip() + ',', s)
    if n:
        open(p, 'w', encoding='utf-8').write(s2)
        py_compile.compile(p, doraise=True)
    print('   swap:', n)

# 2) پیش‌نمایش: رنگِ دوم بعد از 500ms (ضدِ سفیدشدنِ گاه‌به‌گاه)
p = os.path.join(ROOT, 'app', 'ui', 'webengine_preview.py')
if os.path.exists(p):
    s = open(p, encoding='utf-8').read()
    if '# PREV-RETRY' not in s:
        m = re.search(r'(?m)^(\s*)([A-Za-z_][A-Za-z0-9_\.]*)\.setHtml\(([^)\n]+)\)', s)
        if m:
            ind, recv, args = m.group(1), m.group(2), m.group(3).strip()
            add = (f"{ind}try:  # PREV-RETRY\n"
                   f"{ind}    from PyQt5.QtCore import QTimer as _QT2  # PREV-RETRY\n"
                   f"{ind}    _QT2.singleShot(500, lambda: {recv}.setHtml({args}))  # PREV-RETRY\n"
                   f"{ind}except Exception:  # PREV-RETRY\n"
                   f"{ind}    pass  # PREV-RETRY\n")
            s = s[:m.end()] + '\n' + add + s[m.end():]
            open(p, 'w', encoding='utf-8').write(s)
            py_compile.compile(p, doraise=True)
            print('2) PREV-RETRY نصب شد ✔')
    else:
        print('2) از قبل بود ✔')

# 3) رفع UnboundLocalError رف‌نو (نسخهٔ امن)
p = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')
s = open(p, encoding='utf-8').read()
old = ("ref_no = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)\n"
       "            _k = 2  # REF-RETRY\n"
       "            while conn.execute(\"SELECT 1 FROM outbound_loads WHERE reference_no = ?\", (ref_no,)).fetchone():  # REF-RETRY\n"
       "                ref_no = f\"{ref_no}-{_k}\"  # REF-RETRY\n"
       "                _k += 1  # REF-RETRY\n")
new = ("_base_ref = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)  # REF-SAFE\n"
       "            ref_no = _base_ref  # REF-SAFE\n"
       "            _k = 2  # REF-SAFE\n"
       "            while conn.execute(\"SELECT 1 FROM outbound_loads WHERE reference_no = ?\", (ref_no,)).fetchone():  # REF-SAFE\n"
       "                ref_no = f\"{_base_ref}-{_k}\"  # REF-SAFE\n"
       "                _k += 1  # REF-SAFE\n")
if old in s:
    s = s.replace(old, new, 1); open(p, 'w', encoding='utf-8').write(s); py_compile.compile(p, doraise=True)
    print('3) issue_repository امن شد ✔')
p = os.path.join(ROOT, 'app', 'ui', 'proforma_window.py')
s = open(p, encoding='utf-8').read()
old2 = ('ref_no = f"EX-{_jy}-" + str(proforma_id).zfill(4)\n'
        '                _k = 2  # REF-RETRY\n'
        '                while conn.execute("SELECT 1 FROM outbound_loads WHERE reference_no = ?", (ref_no,)).fetchone():  # REF-RETRY\n'
        '                    ref_no = f"{ref_no}-{_k}"  # REF-RETRY\n'
        '                    _k += 1  # REF-RETRY\n')
new2 = ('_base_ref = f"EX-{_jy}-" + str(proforma_id).zfill(4)  # REF-SAFE\n'
        '                ref_no = _base_ref  # REF-SAFE\n'
        '                _k = 2  # REF-SAFE\n'
        '                while conn.execute("SELECT 1 FROM outbound_loads WHERE reference_no = ?", (ref_no,)).fetchone():  # REF-SAFE\n'
        '                    ref_no = f"{_base_ref}-{_k}"  # REF-SAFE\n'
        '                    _k += 1  # REF-SAFE\n')
if old2 in s:
    s = s.replace(old2, new2, 1); open(p, 'w', encoding='utf-8').write(s); py_compile.compile(p, doraise=True)
    print('3) proforma_window امن شد ✔')

# 4) ماندهٔ دقیق: تازه‌سازی موجودی هنگام نمایش هر فرم
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# STOCK-REFRESH' not in s:
    anchor = '                    pass  # COL-WIDTH2\n'
    i = s.rfind(anchor)
    if i != -1:
        j = i + len(anchor)
        block = (
            "                try:  # STOCK-REFRESH\n"
            "                    ps = getattr(self, 'pallet_service', None)  # STOCK-REFRESH\n"
            "                    if ps is not None and callable(getattr(ps, 'reload', None)):  # STOCK-REFRESH\n"
            "                        ps.reload()  # STOCK-REFRESH\n"
            "                        if callable(getattr(self, '_refresh_pallet_combos', None)):  # STOCK-REFRESH\n"
            "                            self._refresh_pallet_combos()  # STOCK-REFRESH\n"
            "                except Exception:  # STOCK-REFRESH\n"
            "                    pass  # STOCK-REFRESH\n"
        )
        s = s[:j] + block + s[j:]
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('4) STOCK-REFRESH نصب شد ✔')
else:
    print('4) از قبل بود ✔')

# 5) بیلد با محافظ داده
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
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
    print('5) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('6) تمام ✔')
input('Enter...')