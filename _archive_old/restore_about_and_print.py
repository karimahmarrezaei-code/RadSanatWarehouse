# -*- coding: utf-8 -*-
"""برگرداندن تزریق اشتباه + چاپ کد درباره/داشبورد - اجرا: python restore_about_and_print.py"""
import os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
mw = os.path.join(ROOT, 'app', 'ui', 'main_window.py')
bak = mw + '.bakabout2'
if os.path.exists(bak):
    shutil.copy2(bak, mw)
    print('✔ تزریق اشتباه درباره برگشت به حالت قبل')
else:
    s0 = open(mw, encoding='utf-8').read()
    if '# about_light' in s0:
        lines = [l for l in s0.split('\n') if '# about_light' not in l]
        open(mw, 'w', encoding='utf-8').write('\n'.join(lines))
        print('✔ خط about_light حذف شد')

s = open(mw, encoding='utf-8', errors='replace').read()
lines = s.split('\n')

i = s.find('def _show_about')
if i != -1:
    j = s.find('\n    def ', i + 10)
    print('\n======== بدنهٔ _show_about:')
    for k, ln in enumerate(lines[s[:i].count('\n'): s[:i].count('\n') + 90]):
        print('{:5d}|{}'.format(s[:i].count('\n') + k + 1, ln))
        if k > 4 and ln.strip().startswith('def ') and '_show_about' not in ln:
            break

print('\n======== خطوط dash_today_lbl / full_name:')
for idx, ln in enumerate(lines):
    if 'dash_today_lbl' in ln or 'full_name' in ln or 'now_for_display' in ln:
        for j2 in range(max(0, idx - 2), min(len(lines), idx + 5)):
            print('{:5d}|{}'.format(j2 + 1, lines[j2]))
        print('   ---')
input('Enter...')