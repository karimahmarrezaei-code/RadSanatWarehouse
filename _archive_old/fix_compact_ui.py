# -*- coding: utf-8 -*-
"""حالت فشرده در صفحه کوچک - اجرا: python fix_compact_ui.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

if '# COMPACT-UI' not in s:
    # 1) استایل فشرده در سطح برنامه
    qss = (
        'COMPACT_QSS = """\n'
        'QWidget { font-size: 12px; }\n'
        'QLabel { font-size: 12px; }\n'
        'QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit { font-size: 12px; padding: 1px; }\n'
        'QPushButton { font-size: 12px; padding: 4px 10px; }\n'
        'QTableWidget, QTableView { font-size: 12px; }\n'
        'QTabBar::tab { padding: 3px 10px; font-size: 12px; }\n'
        'QGroupBox { font-size: 12px; }\n'
        '"""  # COMPACT-QSS\n'
    )
    anchor_q = '# SAFE-FIT-CODE v2'
    i = s.find(anchor_q)
    if i == -1:
        i = s.find('# SAFE-FIT-CODE')
    s = s[:i] + qss + s[i:]

    # 2) تابع فشرده‌سازی پنجره
    anchor_d = '    def _safe_show(self):\n'
    comp = (
        "    def _compact(self):  # COMPACT-UI\n"
        "        try:  # COMPACT-UI\n"
        "            from PyQt5.QtWidgets import QApplication as _QA2, QLayout as _QL2  # COMPACT-UI\n"
        "            if _QA2.desktop().availableGeometry().height() >= 900:  # COMPACT-UI\n"
        "                return  # COMPACT-UI\n"
        "            if getattr(self, '_compact_done', False):  # COMPACT-UI\n"
        "                return  # COMPACT-UI\n"
        "            self._compact_done = True  # COMPACT-UI\n"
        "            for w in self.findChildren(_QW):  # COMPACT-UI\n"
        "                try:  # COMPACT-UI\n"
        "                    wf = w.font()  # COMPACT-UI\n"
        "                    if wf.pointSize() > 8:  # COMPACT-UI\n"
        "                        wf.setPointSize(max(8, wf.pointSize() - 1)); w.setFont(wf)  # COMPACT-UI\n"
        "                    if w.minimumHeight() == w.maximumHeight() and w.minimumHeight() > 52:  # COMPACT-UI\n"
        "                        w.setFixedHeight(int(w.minimumHeight() * 0.78))  # COMPACT-UI\n"
        "                except Exception:  # COMPACT-UI\n"
        "                    pass  # COMPACT-UI\n"
        "            for lay in self.findChildren(_QL2):  # COMPACT-UI\n"
        "                try:  # COMPACT-UI\n"
        "                    m = lay.contentsMargins()  # COMPACT-UI\n"
        "                    lay.setContentsMargins(int(m.left() * 0.6), int(m.top() * 0.6), int(m.right() * 0.6), int(m.bottom() * 0.6))  # COMPACT-UI\n"
        "                    if lay.spacing() > 4:  # COMPACT-UI\n"
        "                        lay.setSpacing(int(lay.spacing() * 0.6))  # COMPACT-UI\n"
        "                except Exception:  # COMPACT-UI\n"
        "                    pass  # COMPACT-UI\n"
        "        except Exception:  # COMPACT-UI\n"
        "            pass  # COMPACT-UI\n"
    )
    s = s.replace(anchor_d, comp + anchor_d, 1)

    # 3) صدا زدن در نمایش + الحاق QSS در صفحه کوچک
    s = s.replace('                _safe_flags(self)  # WIN-BTN\n',
                  '                _safe_flags(self)  # WIN-BTN\n                _compact(self)  # COMPACT-UI\n', 1)
    anchor_css = "        try:  # FONT-COMBO\n"
    add_css = (
        "        try:  # COMPACT-QSS-APPLY\n"
        "            import ctypes as _ct2  # COMPACT-QSS-APPLY\n"
        "            if _ct2.windll.user32.GetSystemMetrics(1) < 900:  # COMPACT-QSS-APPLY\n"
        "                app.setStyleSheet(app.styleSheet() + COMPACT_QSS)  # COMPACT-QSS-APPLY\n"
        "        except Exception:  # COMPACT-QSS-APPLY\n"
        "            pass  # COMPACT-QSS-APPLY\n"
    )
    if anchor_css in s:
        s = s.replace(anchor_css, add_css + anchor_css, 1)
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('1) COMPACT-UI نصب شد ✔')
else:
    print('1) از قبل بود ✔')

print('2) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
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
print('2) تمام ✔')
input('Enter...')