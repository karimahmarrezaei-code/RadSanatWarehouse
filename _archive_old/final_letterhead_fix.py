# -*- coding: utf-8 -*-
import re, io, os
BASE = os.path.dirname(os.path.abspath(__file__))
def read(p):
    with io.open(os.path.join(BASE, p), 'r', encoding='utf-8') as f: return f.read()
def write(p, s):
    with io.open(os.path.join(BASE, p), 'w', encoding='utf-8') as f: f.write(s)

PLAIN_OPEN = '''    def _open_html_in_browser(self, html: str) -> None:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name
        webbrowser.open('file:///' + temp_file)

'''
INJECT = '''    def _inject_letterhead(self, html: str) -> str:
        try:
            from app.core.letterhead import build_letterhead_html, get_filtered_company
            lh = build_letterhead_html(get_filtered_company(self.db))
            if lh:
                html = html.replace('<body>', '<body>' + lh, 1)
        except Exception:
            pass
        return html

'''
PREVIEW_CURRENT = '''    def preview_current_receipt(self) -> None:
        selected_reference_id = self.reference_selector_combo.currentData()
        if not selected_reference_id:
            QMessageBox.information(self, 'پیش‌نمایش رسید', 'ابتدا یک مرجع بار باز انتخاب کنید.')
            return
        try:
            details = self.repository.get_completed_receipt_details(selected_reference_id)
            if not details:
                QMessageBox.warning(self, 'پیش‌نمایش', 'حواله یافت نشد.'); return
            self._open_html_in_browser(self._inject_letterhead(self.repository.render_completed_receipt_html(details)))
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در پیش‌نمایش', f'خطا: {exc}')

'''
PREVIEW_SAVED = '''    def preview_selected_saved_receipt(self) -> None:
        row = self.receipts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, 'پیش‌نمایش', 'ابتدا یک حواله را از جدول انتخاب کنید.'); return
        item = self.receipts_table.item(row, 0)
        if not item: return
        try:
            details = self.repository.get_completed_receipt_details(int(item.text()))
            if not details:
                QMessageBox.warning(self, 'پیش‌نمایش', 'حواله یافت نشد.'); return
            self._open_html_in_browser(self._inject_letterhead(self.repository.render_completed_receipt_html(details)))
        except Exception as exc:
            QMessageBox.critical(self, 'خطا در پیش‌نمایش', f'خطا: {exc}')

'''
LH_BLOCK = re.compile(r"\n[ \t]*from app\.core\.letterhead import build_letterhead_html, get_filtered_company\n[ \t]*_lh = build_letterhead_html\(get_filtered_company\(self\.db\)\)\n[ \t]*if _lh:\n[ \t]*    html = html\.replace\('<body>', '<body>' \+ _lh, 1\)")
FINALIZE = re.compile(r"\n[ \t]*from app\.core\.letterhead import finalize_print_html\n[ \t]*html = finalize_print_html\(self\.db, html\)")

print('شروع پاک‌سازی نهایی...')

# ── هر سه پنجره: بازگشت به _open_html_in_browser ساده و حذف تزریق‌ها ──
for w in ['app/ui/receipt_manager_window.py', 'app/ui/issue_manager_window.py', 'app/ui/proforma_window.py']:
    src = read(w)
    src = re.sub(r"    def _open_html_in_browser\(self, html: str\).*?(?=\n    def )", PLAIN_OPEN, src, flags=re.S)
    src = FINALIZE.sub("", src)
    src = LH_BLOCK.sub("", src)
    write(w, src); print('==> cleaned', w)

# ── رسید: متد امن + دو پیش‌نمایش + سیو ──
p = 'app/ui/receipt_manager_window.py'
src = read(p)
src = re.sub(r"    def _inject_letterhead\(self\).*?(?=\n    def )", "", src, flags=re.S)
src = re.sub(r"    def preview_current_receipt\(self\).*?(?=\n    def )", INJECT + PREVIEW_CURRENT, src, flags=re.S)
src = re.sub(r"    def preview_selected_saved_receipt\(self\).*?(?=\n    def )", PREVIEW_SAVED, src, flags=re.S)
src = src.replace("self._open_html_in_browser(saved['print_html'])",
                  "self._open_html_in_browser(self._inject_letterhead(saved.get('print_html') or ''))")
write(p, src); print('==> receipt previews fixed')

# ── ریپازیتوری‌ها: _get_company_info = فیلترشده ──
FILTERED = "    def _get_company_info(self) -> Dict[str, Any]:\n        try:\n            from app.core.letterhead import get_filtered_company\n            return get_filtered_company(self.db)\n        except Exception:\n            return {}\n\n"
for r in ['app/repositories/receipt_repository.py', 'app/repositories/issue_repository.py']:
    src = read(r)
    src = re.sub(r"    def _get_company_info\(self\).*?(?=\n    def )", FILTERED, src, flags=re.S)
    src = re.sub(r"\n[ \t]*# ── تزریق سربرگ شرکت.*?except Exception:\n[ \t]*pass", "", src, flags=re.S)
    write(r, src); print('==> repo filtered', r)

# ── پیش‌فاکتور: company فیلترشده ──
p = 'app/ui/proforma_window.py'
src = read(p)
src = src.replace("company = {}", "company = get_filtered_company(self.db)")
if 'from app.core.letterhead import get_filtered_company' not in src:
    src = src.replace("def _print_proforma(self, proforma_id):",
                      "def _print_proforma(self, proforma_id):\n        from app.core.letterhead import get_filtered_company", 1)
write(p, src); print('==> proforma filtered')

print('پایان. برنامه را اجرا کنید.')