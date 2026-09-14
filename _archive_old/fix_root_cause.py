# -*- coding: utf-8 -*-
"""پاکسازی ردیف پالت + سپر UNIQUE - اجرا: python fix_root_cause.py"""
import os, re, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) پاکسازی دادهٔ پالت‌ها
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
if not os.path.exists(db):
    db = os.path.join(ROOT, 'data', 'app.db')
con = sqlite3.connect(db)
print('=== پالت‌های فعلی ===')
for r in con.execute("SELECT id, code, name FROM pallets").fetchall():
    print(r)
for pid, code, name in con.execute("SELECT id, code, name FROM pallets").fetchall():
    new_code, new_name = (code or '').strip(), (name or '').strip()
    m = re.match(r'^(\d+(?:-\d+)+)\s*(.*)$', new_name)
    dims_in_name = m.group(1) if m else None
    if m:
        new_name = m.group(2).strip()
    tok = re.search(r'[A-Za-z]{2,}-\d+', new_name)
    if re.match(r'^\d+(?:-\d+)+$', new_code):
        if tok:
            new_code = tok.group(0)
            new_name = new_name.replace(tok.group(0), '').strip(' |-,')
    if dims_in_name and not re.match(r'^\d+(?:-\d+)+$', new_code):
        pass  # ابعاد از نام حذف شد
    if (new_code, new_name) != (code, name):
        con.execute("UPDATE pallets SET code=?, name=? WHERE id=?", (new_code, new_name, pid))
        print('اصلاح شد:', (code, name), '->', (new_code, new_name))
con.commit()
con.close()
print('1) پاکسازی داده انجام شد ✔')

# 2) سپر برخورد شماره مرجع (دو نقطهٔ تبدیل)
p = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')
s = open(p, encoding='utf-8').read()
old = "ref_no = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)"
guard = (old + "\n"
         "            _k = 2  # REF-RETRY\n"
         "            while conn.execute(\"SELECT 1 FROM outbound_loads WHERE reference_no = ?\", (ref_no,)).fetchone():  # REF-RETRY\n"
         "                ref_no = f\"{ref_no}-{_k}\"  # REF-RETRY\n"
         "                _k += 1  # REF-RETRY\n")
if old in s and '# REF-RETRY' not in s:
    s = s.replace(old, guard, 1)
    open(p, 'w', encoding='utf-8').write(s)
    py_compile.compile(p, doraise=True)
    print('2) سپر issue_repository ✔')
p2 = os.path.join(ROOT, 'app', 'ui', 'proforma_window.py')
s2 = open(p2, encoding='utf-8').read()
old2 = 'ref_no = f"EX-{_jy}-" + str(proforma_id).zfill(4)'
guard2 = (old2 + "\n"
          "                _k = 2  # REF-RETRY\n"
          "                while conn.execute(\"SELECT 1 FROM outbound_loads WHERE reference_no = ?\", (ref_no,)).fetchone():  # REF-RETRY\n"
          "                    ref_no = f\"{ref_no}-{_k}\"  # REF-RETRY\n"
          "                    _k += 1  # REF-RETRY\n")
if old2 in s2 and '# REF-RETRY' not in s2:
    s2 = s2.replace(old2, guard2, 1)
    open(p2, 'w', encoding='utf-8').write(s2)
    py_compile.compile(p2, doraise=True)
    print('2) سپر proforma_window ✔')

# 3) بیلد + تزریق (بدون حذف app.db)
print('3) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
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
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
input('Enter...')