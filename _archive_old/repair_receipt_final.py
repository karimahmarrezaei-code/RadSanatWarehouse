# -*- coding: utf-8 -*-
"""
repair_receipt_final.py - تعمیر جامع و یکجا (رسید / حواله / پرینت / قیمت)
=======================================================================

این پچ همه مشکلات باقی‌مانده را یکجا تعمیر می‌کند:

  ۱) ارزش افزوده ۹٪ و مخارج اضافی:
       - ستون‌های vat_amount / extra_costs در دیتابیس (اگر نبود)
       - خواندن از payload + محاسبه قیمت نهایی در repository (رسید و حواله)
       - افزودن به INSERT جدول‌ها
       - نمایش در قالب چاپ (render)
  ۲) قیمت میانگین پالت (از افتتاحیه + تراکنش‌ها + موجودی inventory_levels)
       - جایگزینی _load_pallet_prices در فرم رسید و حواله
  ۳) پیش‌نمایش چاپ:
       - بازسازی print_html همه رسیدها/حواله‌ها با قالب جدید
  ۴) تشخیص وضعیت شماره‌گذاری (چاپ شماره آخرین رسید + sequences + خطوط فرم)

برای هر فایل پشتیبان گرفته می‌شود و سینتکس چک می‌شود؛ اگر خراب شد
خودکار از پشتیبان برمی‌گرداند.

اجرا (از پوشه F:\\warehouse_app — برنامه بسته باشد):
    py -X utf8 .\\repair_receipt_final.py

بعدش:
    py -X utf8 .\\main.py
"""

import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

SKIP = {'venv', '.venv', '__pycache__', 'node_modules', '.git',
        'test_docimg', 'test_issue_percent', 'migration', 'backup_before_update',
        'junk', '_junk', 'Junk', '_junk_junk'}

CHANGED_FILES = []


def log(*a):
    print(' '.join(str(x) for x in a))


def hr():
    print('-' * 66)


def find_file(name):
    for base, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in SKIP]
        if name in files:
            return os.path.join(base, name)
    return None


def find_db():
    for c in ('data/app.db', 'app.db'):
        if os.path.exists(c):
            return c
    return None


def compile_ok(path):
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        return True, ''
    except Exception as e:
        return False, str(e)


def backup(path, tag):
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = '{}.{}_{}.bak'.format(path, tag, stamp)
    shutil.copy2(path, bak)
    return bak


def write_safe(path, content, tag):
    """نوشتن با پشتیبان و بررسی سینتکس — در صورت خرابی، برگرداندن"""
    with open(path, encoding='utf-8') as f:
        old = f.read()
    if content == old:
        return True, ['تغییری لازم نبود']
    bak = backup(path, tag)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    ok, err = compile_ok(path)
    if not ok:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(old)
        return False, ['❌ سینتکس خراب شد — برگردانده شد از پشتیبان: ' + str(err)[:120]]
    CHANGED_FILES.append(path)
    return True, ['پشتیبان: ' + bak, '✅ سینتکس سالم']


# =====================================================================
# ۱) دیتابیس: ستون‌ها + گزارش
# =====================================================================

def fix_db_columns(conn):
    changes = []
    for table in ('warehouse_receipts', 'warehouse_issues'):
        try:
            cols = [r[1] for r in conn.execute('PRAGMA table_info({})'.format(table)).fetchall()]
            if 'vat_amount' not in cols:
                conn.execute('ALTER TABLE {} ADD COLUMN vat_amount INTEGER NOT NULL DEFAULT 0'.format(table))
                changes.append('{}: ستون vat_amount اضافه شد'.format(table))
            if 'extra_costs' not in cols:
                conn.execute('ALTER TABLE {} ADD COLUMN extra_costs INTEGER NOT NULL DEFAULT 0'.format(table))
                changes.append('{}: ستون extra_costs اضافه شد'.format(table))
        except Exception as e:
            changes.append('{}: ⚠️ ' + str(e)[:80])
    conn.commit()
    return changes


def report_db(conn):
    log('   ── آخرین ۳ رسید ذخیره‌شده ──')
    try:
        rows = conn.execute(
            "SELECT id, receipt_no, COALESCE(supplier_id,0), COALESCE(total_qty,0), "
            "COALESCE(vat_amount,0), COALESCE(extra_costs,0), LENGTH(COALESCE(print_html,'')) "
            "FROM warehouse_receipts ORDER BY id DESC LIMIT 3"
        ).fetchall()
        if not rows:
            log('      (رسیدی وجود ندارد)')
        for r in rows:
            log('      id={} | شماره={} | تامین‌کننده={} | تعداد={} | ارزش‌افزوده={} | مخارج={} | طول HTML={}'.format(*r))
    except Exception as e:
        log('      ⚠️ ' + str(e)[:100])
    log('   ── شمارنده‌ها (sequences) ──')
    try:
        rows = conn.execute("SELECT name, current_value FROM sequences ORDER BY name").fetchall()
        if rows:
            log('      ' + ', '.join('{}={}'.format(r[0], r[1]) for r in rows))
        else:
            log('      (خالی)')
    except Exception as e:
        log('      ⚠️ ' + str(e)[:100])


# =====================================================================
# ۲) repository: ارزش افزوده / مخارج
# =====================================================================

def add_columns_to_insert(content, table):
    """افزودن vat_amount, extra_costs به INSERT — بدون وابستگی به ترتیب ستون‌ها.
    ستون‌ها را قبل از آخرین ) قبل از VALUES و مقادیر را قبل از ) پایانی tuple اضافه می‌کند."""
    m = re.search(r'INSERT INTO {}\s*'.format(re.escape(table)), content)
    if not m:
        return content, False
    start = m.start()
    vpos = content.find('VALUES', m.end())
    if vpos == -1:
        return content, False

    # ── پیدا کردن پایان tuple ──
    nl = content.find('\n', vpos)
    if nl == -1:
        # INSERT تک‌خطی (نادر) — پایان همان خط
        line_end = content.find('\n', vpos)
        seg_end = line_end if line_end != -1 else len(content)
    else:
        # چندخطی: شمارش پرانتزها از خط بعد از VALUES
        depth = 0
        started = False
        seg_end = None
        pos = nl + 1
        while pos < len(content):
            ch = content[pos]
            if ch == '(':
                depth += 1
                started = True
            elif ch == ')':
                if started:
                    depth -= 1
                    if depth <= 0:
                        seg_end = pos + 1
                        break
            pos += 1
        if seg_end is None:
            return content, False

    segment = content[start:seg_end]
    if 'vat_amount' in segment:
        return content, False  # از قبل هست

    # ۱) ستون‌ها: آخرین ) قبل از VALUES (پایان لیست ستون‌ها)
    vpos2 = segment.find('VALUES')
    close_cols = segment.rfind(')', 0, vpos2)
    if close_cols == -1:
        return content, False
    segment = segment[:close_cols] + ', vat_amount, extra_costs' + segment[close_cols:]

    # ۲) placeholder ها: اولین ( بعد از VALUES و اولین ) بعد از آن
    vpos3 = segment.find('VALUES')
    open_ph = segment.find('(', vpos3)
    close_ph = segment.find(')', open_ph)
    if open_ph == -1 or close_ph == -1:
        return content, False
    segment = segment[:close_ph] + ',?,?' + segment[close_ph:]

    # ۳) tuple: از ( بعد از placeholder ها تا ) متناظرش (شمارش پرانتز)
    open_tuple = segment.find('(', close_ph + 1)
    if open_tuple == -1:
        return content, False
    depth = 0
    close_tuple = None
    p = open_tuple
    while p < len(segment):
        ch = segment[p]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth <= 0:
                close_tuple = p
                break
        p += 1
    if close_tuple is None:
        return content, False
    segment = segment[:close_tuple] + ', vat_amount, extra_costs' + segment[close_tuple:]

    content = content[:start] + segment + content[seg_end:]
    return content, True


def patch_repo_vat(content, table):
    """خواندن vat/extra از payload + محاسبه قیمت نهایی + افزودن به INSERT"""
    changes = []
    if 'vat_enabled = bool(payload.get' in content:
        changes.append('خواندن vat/extra از payload: از قبل بود')
    else:
        m = re.search(
            r"^([ \t]*)freight_amount = self\._safe_int\(payload\.get\('freight_amount', '0'\)\)\s*$",
            content, re.M)
        if m:
            add = ('\n'
                   + m.group(1) + "vat_enabled = bool(payload.get('vat_enabled', False))\n"
                   + m.group(1) + "vat_amount = self._safe_int(payload.get('vat_amount', '0'))\n"
                   + m.group(1) + "extra_costs = self._safe_int(payload.get('extra_costs', '0'))\n")
            content = content[:m.end()] + add + content[m.end():]
            changes.append('خواندن vat/extra از payload اضافه شد')
        else:
            changes.append('⚠️ خط freight_amount پیدا نشد — خواندن payload اضافه نشد')

    if 'lines_total_amount = total_amount' in content:
        changes.append('محاسبه قیمت نهایی: از قبل بود')
    else:
        m = re.search(
            r"^([ \t]*)total_amount = sum\(.*?for line in lines\s*\)\s*$",
            content, re.M | re.S)
        if m:
            add = ('\n'
                   + m.group(1) + '# [VAT-EXTRA] قیمت نهایی = جمع ردیف‌ها + ارزش افزوده + مخارج\n'
                   + m.group(1) + 'lines_total_amount = total_amount\n'
                   + m.group(1) + 'if vat_enabled:\n'
                   + m.group(1) + '    vat_amount = int(lines_total_amount * 9 / 100)\n'
                   + m.group(1) + 'total_amount = lines_total_amount + vat_amount + extra_costs\n')
            content = content[:m.end()] + add + content[m.end():]
            changes.append('محاسبه قیمت نهایی (VAT+مخارج) اضافه شد')
        else:
            changes.append('⚠️ خط total_amount = sum(...) پیدا نشد — محاسبه اضافه نشد')

    if 'vat_amount, extra_costs' in content:
        changes.append('INSERT: ستون‌های vat/extra از قبل بود')
    else:
        content2, done = add_columns_to_insert(content, table)
        if done:
            content = content2
            changes.append('INSERT {}: ستون‌های vat/extra اضافه شد (روش عمومی)'.format(table))
        else:
            changes.append('⚠️ INSERT {} پیدا نشد یا قابل تشخیص نبود — ستون‌ها اضافه نشد (بخش INSERT فعلی در گزارش چاپ می‌شود)'.format(table))

    # context پرینت
    if "'vat_amount': vat_amount" in content:
        changes.append('context پرینت: از قبل vat/extra داشت')
    else:
        m = re.search(r"'lines_total_amount':\s*(\w+),", content)
        if m:
            var = m.group(1)
            if var == 'total_amount':
                # تبدیل به lines_total_amount (که بعد از محاسبه تعریف می‌شود)
                content = content.replace(
                    m.group(0),
                    "'lines_total_amount': lines_total_amount, 'vat_amount': vat_amount, 'extra_costs': extra_costs,", 1)
            else:
                content = content.replace(
                    m.group(0),
                    m.group(0).rstrip(',') + ", 'vat_amount': vat_amount, 'extra_costs': extra_costs,", 1)
            changes.append('vat/extra به context پرینت اضافه شد')
        else:
            changes.append('⚠️ context پرینت پیدا نشد (ردیف‌های چاپ بدون vat می‌مانند)')

    return content, changes


def print_insert_segment(content, table):
    """برای گزارش: چاپ بخش INSERT مربوطه"""
    m = re.search(r'INSERT INTO {}(.{{0,700}})'.format(re.escape(table)), content, re.S)
    if m:
        seg = m.group(0)
        log('      ' + seg.replace('\n', '\n      ')[:700])
    else:
        log('      ⚠️ INSERT INTO {} پیدا نشد'.format(table))


# =====================================================================
# ۳) render: ردیف‌های VAT/مخارج در قالب چاپ
# =====================================================================

def patch_render_vat(content, kind):
    """kind: 'receipt' یا 'issue' — افزودن vat/extra به render"""
    changes = []
    if 'lines_total_amount = int(context.get' in content:
        changes.append('render: محاسبه vat/extra از قبل بود')
        return content, changes

    if kind == 'receipt':
        m = re.search(
            r"^([ \t]*)total_amount = context\.get\('lines_total_amount', 0\)\s*$",
            content, re.M)
        if m:
            indent = m.group(1)
            content = content.replace(
                m.group(0),
                indent + "lines_total_amount = int(context.get('lines_total_amount', 0) or 0)\n"
                + indent + "vat_amount = int(context.get('vat_amount', 0) or 0)\n"
                + indent + "extra_costs = int(context.get('extra_costs', 0) or 0)\n"
                + indent + "final_total = lines_total_amount + vat_amount + extra_costs\n"
                + indent + "total_amount = final_total", 1)
            changes.append('render رسید: محاسبه vat/extra/final اضافه شد')
        else:
            changes.append('⚠️ render رسید: خط total_amount پیدا نشد')
    else:
        m = re.search(
            r"^([ \t]*)total_amount = int\(context\.get\('lines_total_amount', 0\) or 0\)\s*$",
            content, re.M)
        if m:
            indent = m.group(1)
            content = content.replace(
                m.group(0),
                indent + "lines_total_amount = int(context.get('lines_total_amount', 0) or 0)\n"
                + indent + "vat_amount = int(context.get('vat_amount', 0) or 0)\n"
                + indent + "extra_costs = int(context.get('extra_costs', 0) or 0)\n"
                + indent + "total_amount = lines_total_amount + vat_amount + extra_costs", 1)
            changes.append('render حواله: محاسبه vat/extra/final اضافه شد')
        else:
            changes.append('⚠️ render حواله: خط total_amount پیدا نشد')

    # ردیف‌های جمع — فقط اگر هنوز ردیف VAT نباشد
    if 'ارزش افزوده' not in content:
        if kind == 'receipt':
            anchor = 'جمع کل:'
            cell = 'delivered_qty'
        else:
            anchor = 'جمع کل حواله:'
            cell = 'delivered_qty'
        m = re.search(r'(<tr class="total-row">.*?</tr>)', content, re.S)
        if m:
            add = ('\n'
                   '    <tr class="total-row" style="background:#f5f3ff;">'
                   '<td colspan="3" style="text-align:left;padding:8px;">ارزش افزوده ۹٪:</td>'
                   '<td></td><td></td><td>{vat_amount:,} ریال</td><td colspan="2"></td></tr>\n'
                   '    <tr class="total-row" style="background:#f5f3ff;">'
                   '<td colspan="3" style="text-align:left;padding:8px;">مخارج اضافی:</td>'
                   '<td></td><td></td><td>{extra_costs:,} ریال</td><td colspan="2"></td></tr>\n'
                   '    <tr class="total-row" style="background:#dcfce7;">'
                   '<td colspan="3" style="text-align:left;padding:10px;"><strong>قیمت نهایی:</strong></td>'
                   '<td></td><td></td><td><strong>{final_total:,} ریال</strong></td><td colspan="2"></td></tr>')
            content = content[:m.end()] + add + content[m.end():]
            changes.append('render: ردیف‌های VAT/مخارج/نهایی اضافه شد')
        else:
            changes.append('⚠️ render: ردیف جمع کل پیدا نشد — ردیف‌های VAT اضافه نشد')
        # افزودن به دیکشنری format در انتهای تابع render
        m = re.search(
            r"(return html\.format\()",
            content)
        if m:
            pass  # مقادیر در قالب استفاده می‌شوند — چک در زیر
    else:
        changes.append('render: ردیف ارزش افزوده از قبل بود')

    return content, changes


# =====================================================================
# ۴) فرم: payload + قیمت میانگین + چک‌باکس
# =====================================================================

NEW_LOAD = '''    def _load_pallet_prices(self) -> None:
        """قیمت میانگین از افتتاحیه + تراکنش‌ها + موجودی از inventory_levels"""
        self.avg_pallet_prices = {}
        self.pallet_stock = {}
        try:
            with self.db.connect() as conn:
                conn.row_factory = None

                # ۱) قیمت میانگین از opening_inventory_items (افتتاحیه)
                rows = conn.execute(
                    "SELECT pallet_id, "
                    "CASE WHEN SUM(qty) > 0 THEN SUM(total_price) * 1.0 / SUM(qty) ELSE 0 END AS avg_price "
                    "FROM opening_inventory_items "
                    "WHERE qty > 0 "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows:
                    self.avg_pallet_prices[r[0]] = float(r[1] or 0)

                # ۲) قیمت میانگین از inventory_transactions (رسیدهای بعدی)
                rows = conn.execute(
                    "SELECT pallet_id, "
                    "CASE WHEN SUM(qty_in) > 0 THEN SUM(total_price) * 1.0 / SUM(qty_in) ELSE 0 END AS avg_price "
                    "FROM inventory_transactions "
                    "WHERE transaction_type = 'IN' AND qty_in > 0 AND COALESCE(is_void, 0) = 0 "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows:
                    self.avg_pallet_prices[r[0]] = float(r[1] or 0)

                # ۳) موجودی از inventory_levels
                rows = conn.execute(
                    "SELECT pallet_id, SUM(quantity) AS stock "
                    "FROM inventory_levels "
                    "GROUP BY pallet_id"
                ).fetchall()
                for r in rows:
                    self.pallet_stock[r[0]] = max(int(r[1] or 0), 0)

                print(f'_load_pallet_prices: {len(self.avg_pallet_prices)} prices loaded')
        except Exception as e:
            print('Load pallet prices error:', str(e))
            self.avg_pallet_prices = {}
            self.pallet_stock = {}

'''


def replace_load_pallet_prices(content):
    """جایگزینی _load_pallet_prices با نسخه افتتاحیه‌محور (اگر قدیمی بود)"""
    changes = []
    m = re.search(r'^[ \t]*def _load_pallet_prices\(self.*?(?=\n[ \t]*def |\nclass |\Z)',
                  content, re.M | re.S)
    if not m:
        return content, changes + ['⚠️ _load_pallet_prices پیدا نشد — جایگزین نشد']
    seg = m.group(0)
    # اگر از قبل افتتاحیه دارد، دست نزن
    if 'opening_inventory_items' in seg:
        return content, changes + ['_load_pallet_prices از قبل افتتاحیه‌محور است ✅']
    content = content[:m.start()] + NEW_LOAD + content[m.end():]
    return content, changes + ['_load_pallet_prices با نسخه افتتاحیه‌محور جایگزین شد']


def patch_payload_vat(content):
    """افزودن vat/extra به payload فرم (اگر نبود)"""
    changes = []
    if "'vat_enabled':" in content:
        return content, changes + ['payload از قبل vat/extra داشت']
    lines = content.split('\n')
    for i, ln in enumerate(lines):
        if "'lines': self._collect_lines()" in ln:
            indent = ln[:len(ln) - len(ln.lstrip())]
            if not ln.rstrip().endswith(','):
                lines[i] = ln.rstrip() + ','
            add = [
                indent + "'vat_enabled': self.vat_checkbox.isChecked() if hasattr(self, 'vat_checkbox') else False,",
                indent + "'vat_amount': self._current_vat_amount() if hasattr(self, 'vat_checkbox') else 0,",
                indent + "'extra_costs': self._current_extra_costs() if hasattr(self, 'vat_checkbox') else 0,",
            ]
            lines[i+1:i+1] = add
            return '\n'.join(lines), changes + ['vat/extra به payload اضافه شد']
    return content, changes + ['⚠️ خط "lines": self._collect_lines() پیدا نشد']


def show_numbering_calls(path):
    """چاپ خطوط شماره‌گذاری در فرم (برای تشخیص شماره‌ها)"""
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return
    log('      ── فراخوانی‌های شماره‌گذاری در {} ──'.format(os.path.basename(path)))
    for i, ln in enumerate(lines):
        if re.search(r'repository\.(peek_document_no|build_document_no|next_reference_no)', ln):
            ctx = lines[max(0, i-1):i+2]
            for cl in ctx:
                log('        | ' + cl.rstrip())
            log()


# =====================================================================
# ۵) بازسازی print_html (پیش‌نمایش با قالب جدید)
# =====================================================================

def patch_numbering_calls(path, content, combo_attr):
    """در فراخوانی‌های تک‌خطی peek/build در فرم، personnel_id را از کمبو اضافه می‌کند"""
    if combo_attr not in content:
        return content, ['ℹ️  {} در فرم نیست — فراخوانی‌ها دست نمی‌خورد (خطوط آن بالا چاپ شد)'.format(combo_attr)]
    lines = content.split('\n')
    changed = []
    for i, ln in enumerate(lines):
        if re.search(r'self\.repository\.(peek_document_no|build_document_no)\(', ln) \
                and 'personnel_id' not in ln and ln.rstrip().endswith(')'):
            new_ln = ln.rstrip()
            new_ln = new_ln[:-1] + ', personnel_id=self.{}.currentData())'.format(combo_attr)
            changed.append((i + 1, ln.strip(), new_ln.strip()))
            lines[i] = new_ln
    if changed:
        return '\n'.join(lines), changed
    return content, ['هیچ فراخوانی تک‌خطیِ بدون personnel_id نبود']


def backfill_print_html(db_path):
    """بازسازی print_html همه رسیدها و حواله‌ها با قالب جدید"""
    changes = []
    try:
        sys.path.insert(0, os.getcwd())
        from app.core.database import DatabaseManager
        from app.repositories.receipt_repository import ReceiptRepository
        from app.repositories.issue_repository import IssueRepository
        db = DatabaseManager(db_path)

        rr = ReceiptRepository(db)
        if hasattr(rr, 'rebuild_print_html'):
            with db.connect() as conn:
                conn.row_factory = None
                ids = [r[0] for r in conn.execute(
                    "SELECT id FROM warehouse_receipts "
                    "WHERE COALESCE(receipt_status,'CONFIRMED') <> 'CANCELLED'").fetchall()]
            ok = 0
            for rid in ids:
                try:
                    if rr.rebuild_print_html(rid):
                        ok += 1
                except Exception:
                    pass
            changes.append('رسیدها: {} از {} با قالب جدید بازسازی شد'.format(ok, len(ids)))

        ir = IssueRepository(db)
        if hasattr(ir, 'rebuild_print_html'):
            with db.connect() as conn:
                conn.row_factory = None
                ids = [r[0] for r in conn.execute(
                    "SELECT id FROM warehouse_issues "
                    "WHERE COALESCE(issue_status,'CONFIRMED') <> 'CANCELLED'").fetchall()]
            ok = 0
            for iid in ids:
                try:
                    if ir.rebuild_print_html(iid):
                        ok += 1
                except Exception:
                    pass
            changes.append('حواله‌ها: {} از {} با قالب جدید بازسازی شد'.format(ok, len(ids)))
    except Exception as e:
        changes.append('⚠️ بازسازی print_html انجام نشد: ' + str(e)[:150])
    return changes


# =====================================================================
# main
# =====================================================================

def main():
    log('=== تعمیر جامع رسید / حواله / پرینت / قیمت ===')
    log('⚠️  برنامه باید بسته باشد!')
    hr()

    db = find_db()
    if not db:
        log('❌ app.db پیدا نشد — از پوشه F:\\warehouse_app اجرا کنید.')
        return
    log('دیتابیس:', db)

    # ── پشتیبان دیتابیس ──
    bak_db = backup(db, 'repair')
    log('پشتیبان دیتابیس:', bak_db)
    hr()

    conn = sqlite3.connect(db)

    # ── ۱) ستون‌ها ──
    log('۱) ستون‌های ارزش افزوده/مخارج:')
    for c in fix_db_columns(conn):
        log('   • ' + c)
    hr()

    # ── ۲) گزارش فعلی دیتابیس ──
    log('۲) وضعیت فعلی دیتابیس:')
    report_db(conn)
    conn.close()
    hr()

    # ── ۳) repository رسید ──
    repo_r = find_file('receipt_repository.py')
    if repo_r:
        log('۳) ' + repo_r)
        with open(repo_r, encoding='utf-8') as f:
            content = f.read()
        new_content, changes = patch_repo_vat(content, 'warehouse_receipts')
        for c in changes:
            log('   • ' + c)
        ok, msgs = write_safe(repo_r, new_content, 'repair')
        for m_ in msgs:
            log('   • ' + m_)
        if 'الگوی INSERT' in '\n'.join(changes):
            log('   ── INSERT فعلی در فایل شما ──')
            print_insert_segment(content, 'warehouse_receipts')
        hr()
    else:
        log('❌ receipt_repository.py پیدا نشد')
        hr()

    # ── ۴) repository حواله ──
    repo_i = find_file('issue_repository.py')
    if repo_i:
        log('۴) ' + repo_i)
        with open(repo_i, encoding='utf-8') as f:
            content = f.read()
        new_content, changes = patch_repo_vat(content, 'warehouse_issues')
        for c in changes:
            log('   • ' + c)
        ok, msgs = write_safe(repo_i, new_content, 'repair')
        for m_ in msgs:
            log('   • ' + m_)
        if 'الگوی INSERT' in '\n'.join(changes):
            log('   ── INSERT فعلی در فایل شما ──')
            print_insert_segment(content, 'warehouse_issues')
        hr()
    else:
        log('❌ issue_repository.py پیدا نشد')
        hr()

    # ── ۵) render چاپ ──
    for fname, kind in (('receipt_repository.py', 'receipt'),
                        ('issue_repository.py', 'issue')):
        path = find_file(fname)
        if not path:
            continue
        log('۵) render چاپ ' + ('رسید' if kind == 'receipt' else 'حواله') + ':')
        with open(path, encoding='utf-8') as f:
            content = f.read()
        new_content, changes = patch_render_vat(content, kind)
        for c in changes:
            log('   • ' + c)
        ok, msgs = write_safe(path, new_content, 'repair')
        for m_ in msgs:
            log('   • ' + m_)
        hr()

    # ── ۶) فرم رسید ──
    form_r = find_file('receipt_manager_window.py')
    if form_r:
        log('۶) ' + form_r)
        with open(form_r, encoding='utf-8') as f:
            content = f.read()
        has_ui = 'vat_checkbox' in content
        log('   • چک‌باکس ارزش افزوده در فرم:', '✅ هست' if has_ui else '❌ نیست (payload امن شد؛ اگر در فرم نمی‌بینی، بگو تا اضافه کنم)')
        new_content, changes = replace_load_pallet_prices(content)
        for c in changes:
            log('   • ' + c)
        new_content2, ch2 = patch_payload_vat(new_content)
        for c in ch2:
            log('   • ' + c)
        new_content3, ch3 = patch_numbering_calls(form_r, new_content2, 'supplier_combo')
        for c in ch3:
            if isinstance(c, tuple):
                log('   • خط {}: {}  →  {}'.format(c[0], c[1], c[2]))
            else:
                log('   • ' + c)
        ok, msgs = write_safe(form_r, new_content3, 'repair')
        for m_ in msgs:
            log('   • ' + m_)
        show_numbering_calls(form_r)
        hr()
    else:
        log('❌ receipt_manager_window.py پیدا نشد')
        hr()

    # ── ۷) فرم حواله ──
    form_i = find_file('issue_manager_window.py')
    if form_i:
        log('۷) ' + form_i)
        with open(form_i, encoding='utf-8') as f:
            content = f.read()
        has_ui = 'vat_checkbox' in content
        log('   • چک‌باکس ارزش افزوده در فرم:', '✅ هست' if has_ui else '❌ نیست (payload امن شد؛ اگر در فرم نمی‌بینی، بگو تا اضافه کنم)')
        new_content, changes = replace_load_pallet_prices(content)
        for c in changes:
            log('   • ' + c)
        new_content2, ch2 = patch_payload_vat(new_content)
        for c in ch2:
            log('   • ' + c)
        new_content3, ch3 = patch_numbering_calls(form_i, new_content2, 'customer_combo')
        for c in ch3:
            if isinstance(c, tuple):
                log('   • خط {}: {}  →  {}'.format(c[0], c[1], c[2]))
            else:
                log('   • ' + c)
        ok, msgs = write_safe(form_i, new_content3, 'repair')
        for m_ in msgs:
            log('   • ' + m_)
        show_numbering_calls(form_i)
        hr()
    else:
        log('❌ issue_manager_window.py پیدا نشد')
        hr()

    # ── ۸) بازسازی print_html ──
    log('۸) بازسازی پیش‌نمایش چاپ با قالب جدید:')
    for c in backfill_print_html(db):
        log('   • ' + c)
    hr()

    # ── ۹) جمع‌بندی ──
    log('=== جمع‌بندی ===')
    if CHANGED_FILES:
        log('فایل‌های تغییرکرده:')
        for f in CHANGED_FILES:
            log('   • ' + f)
    else:
        log('هیچ فایلی تغییر نکرد (همه از قبل درست بودند).')
    log()
    log('حالا برنامه را اجرا کن:')
    log('    py -X utf8 .\\main.py')
    log('و یک رسید جدید بزن (چک‌باکس ارزش افزوده و مخارج را تیک بزن).')
    log()
    log('توجه: وضعیت شماره‌گذاری و خطوط مربوطه در بالا چاپ شد — آن بخش را برای من بفرست.')
    log('بعدش پیش‌نمایش چاپ همان رسید را ببین.')


if __name__ == '__main__':
    main()
