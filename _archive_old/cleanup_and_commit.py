# -*- coding: utf-8 -*-
"""پاکسازی اسکریپت‌های موقت + ثبت گیت - اجرا: python cleanup_and_commit.py"""
import os, glob, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
KEEP = {'fix_clone_issue.py', 'regen_print_html2.py', 'cleanup_and_commit.py'}

# ── حذف اسکریپت‌های موقت تشخیص/پچ ──
for pat in ('print_*.py', 'fix_*.py', 'regen_*.py'):
    for f in glob.glob(os.path.join(ROOT, pat)):
        fn = os.path.basename(f)
        if fn not in KEEP:
            try:
                os.remove(f)
                print('حذف شد:', fn)
            except Exception:
                pass

# ── حذف فایل‌های پشتیبان اضافی ──
for pat in ('app/ui/*.bak*', 'app/repositories/*.bak*'):
    for f in glob.glob(os.path.join(ROOT, pat)):
        try:
            os.remove(f)
            print('حذف شد:', os.path.basename(f))
        except Exception:
            pass

# ── ثبت گیت ──
msg = ('یکپارچه‌سازی قالب رسید/حواله (کپی عین الگو) + پیش‌نمایش تک‌موتوره بدون WebEngine '
       '+ دکمه‌های چاپ/PDF + تحویل تجمعی و مغایرت + دکمه‌های تاریخچه رسید')
subprocess.run(['git', 'add', '-A'], cwd=ROOT)
r = subprocess.run(['git', 'commit', '-m', msg], cwd=ROOT, capture_output=True, text=True)
print(r.stdout or r.stderr)
s = subprocess.run(['git', 'status', '--short'], cwd=ROOT, capture_output=True, text=True)
print('وضعیت:', s.stdout or 'تمیز')
input('Enter...')