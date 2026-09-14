# -*- coding: utf-8 -*-
import re, io, os
BASE = os.path.dirname(os.path.abspath(__file__))
def read(p):
    with io.open(os.path.join(BASE, p), 'r', encoding='utf-8') as f: return f.read()
def write(p, s):
    with io.open(os.path.join(BASE, p), 'w', encoding='utf-8') as f: f.write(s)

NEW_OPEN = '''    def _open_html_in_browser(self, html: str) -> None:
        from app.core.letterhead import finalize_print_html
        html = finalize_print_html(self.db, html)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name
        webbrowser.open('file:///' + temp_file)

'''

print('شروع بازسازی...')

# ۱) سه پنجره: درگاه واحد نمایش
for w in ['app/ui/receipt_manager_window.py', 'app/ui/issue_manager_window.py', 'app/ui/proforma_window.py']:
    src = read(w)
    src, n = re.subn(r"    def _open_html_in_browser\(self, html: str\).*?(?=\n    def )", NEW_OPEN, src, flags=re.S)
    # حذف بلوک‌های تزریق قدیمی _lh
    src, m = re.subn(r"\n[ \t]*from app\.core\.letterhead import build_letterhead_html, get_filtered_company\n[ \t]*_lh = build_letterhead_html\(get_filtered_company\(self\.db\)\)\n[ \t]*if _lh:\n[ \t]*    html = html\.replace\('<body>', '<body>' \+ _lh, 1\)", "", src)
    write(w, src)
    print(f'==> {w}: open={n}, removed_inject={m}')

# ۲) خاموش‌کردن هدر داخلی رسید و حواله
for r in ['app/repositories/receipt_repository.py', 'app/repositories/issue_repository.py']:
    src = read(r)
    src, n = re.subn(r"    def _get_company_info\(self\).*?(?=\n    def )",
                     "    def _get_company_info(self) -> Dict[str, Any]:\n        return {}\n\n", src, flags=re.S)
    # حذف بلوک تزریق rebuild در صورت وجود
    src, m = re.subn(r"\n[ \t]*# ── تزریق سربرگ شرکت.*?except Exception:\n[ \t]*pass", "", src, flags=re.S)
    write(r, src)
    print(f'==> {r}: company_off={n}, removed_rebuild={m}')

# ۳) پیش‌فاکتور: خاموش‌کردن هدر داخلی
p = 'app/ui/proforma_window.py'
src = read(p)
src, n = re.subn(r"company = get_filtered_company\(self\.db\)", "company = {}", src)
write(p, src)
print(f'==> {p}: company_off={n}')

print('پایان بازسازی.')