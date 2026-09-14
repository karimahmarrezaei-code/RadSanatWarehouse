# -*- coding: utf-8 -*-
"""پیش‌نمایش غنی سند برگشت (هم‌قالب با لیست) - بعد از ثبت"""
import tempfile
import webbrowser


def show_return_preview(win, repo, ctx):
    from app.core.jalali import jalali_date_display_from_iso
    from app.core.letterhead import get_filtered_company
    company = get_filtered_company(win.db)
    fd_id = ctx.get('financial_document_id')
    items = repo.get_return_items(fd_id)
    with win.db.connect() as conn:
        conn.row_factory = None
        meta = conn.execute(
            "SELECT smart_no, return_type, source_doc_id, source_doc_no, reason, return_date "
            "FROM return_items WHERE financial_document_id = ? LIMIT 1", (fd_id,)
        ).fetchone()
        if not meta:
            raise Exception('متادیتای برگشت یافت نشد')
        meta = {'smart_no': meta[0], 'return_type': meta[1], 'source_doc_id': meta[2],
                'source_doc_no': meta[3], 'reason': meta[4], 'return_date': meta[5]}
        fd = conn.execute("SELECT counterparty_person_id FROM financial_documents WHERE id=?",
                          (fd_id,)).fetchone()
        person = '-'
        if fd and fd[0]:
            pr = conn.execute("SELECT first_name || ' ' || last_name FROM persons WHERE id=?",
                              (fd[0],)).fetchone()
            person = pr[0] if pr else '-'
        is_purchase = meta['return_type'] == 'RECEIPT'
        t = 'warehouse_receipt_items' if is_purchase else 'warehouse_issue_items'
        link = 'receipt_id' if is_purchase else 'issue_id'
        o = conn.execute(
            "SELECT COALESCE(SUM(qty),0), COALESCE(SUM(total_price),0) FROM {} WHERE {}=?".format(t, link),
            (meta['source_doc_id'],)).fetchone()
        orig_qty = int(o[0] or 0)
        orig_amount = int(o[1] or 0)
        d = conn.execute(
            "SELECT {} FROM {} WHERE id=?".format(
                'receipt_date' if is_purchase else 'issue_date',
                'warehouse_receipts' if is_purchase else 'warehouse_issues'),
            (meta['source_doc_id'],)).fetchone()
        src_date = d[0] if d and d[0] else None

    rows_html = ''
    total = 0
    for it in items:
        total += int(it.get('total_price') or 0)
        rows_html += ('<tr><td>{}</td><td>{}</td><td>{}</td><td>{:,}</td><td>{:,}</td><td>{:,}</td></tr>').format(
            it.get('row_no', ''), it.get('pallet_code', ''), it.get('pallet_name', ''),
            int(it.get('qty') or 0), int(it.get('unit_price') or 0), int(it.get('total_price') or 0))

    doc_label = 'خرید' if is_purchase else 'فروش'
    money_label = 'دریافتنی از مشتری' if is_purchase else 'پرداختنی به مشتری'

    html = """<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><style>
body {{ font-family: Tahoma; direction: rtl; padding: 20px; background: #fff; }}
.company-info {{ text-align: right; margin-bottom: 20px; }}
.company-info p {{ margin: 4px 0; }}
.box {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px; margin:12px 0; }}
.box h3 {{ margin: 0 0 8px 0; }}
table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
th {{ background:#f59e0b; color:#46505f; padding:8px; border:1px solid #5b6675; font-size:13px; }}
td {{ padding:8px; border:1px solid #e2e8f0; text-align:center; }}
.money {{ background:#dcfce7; border:1px solid #16a34a; border-radius:6px; padding:12px; margin-top:15px; font-size:16px; font-weight:bold; color:#14532d; }}
.print-btn {{ position:fixed; top:20px; left:20px; padding:10px 20px; background:#9333ea; color:#fff; border:none; border-radius:6px; cursor:pointer; }}
</style></head><body>
<button class="print-btn" onclick="window.print()">چاپ / PDF</button>
<div class="company-info"><h1>{company_name}</h1>
<p>مدیر عامل: {ceo}</p>
<p>شناسه ملی: {national}</p>
<p>آدرس: {address}</p>
<p>تلفن: {phone}</p></div>
<h2>سند برگشت از {doc_label} — {smart_no}</h2>
<div class="box">
<p><strong>سند مرجع:</strong> {source_doc_no} | <strong>تاریخ سند مرجع:</strong> {src_txt}</p>
<p><strong>طرف حساب:</strong> {person}</p>
<p><strong>تاریخ برگشت:</strong> {ret_txt} | <strong>علت:</strong> {reason}</p>
</div>
<div class="box"><h3>۱) سند اصلی</h3>
<table><thead><tr><th>تعداد کل ثبت</th><th>مبلغ ثبت‌شده (ریال)</th></tr></thead>
<tbody><tr><td>{orig_qty:,}</td><td>{orig_amount:,}</td></tr></tbody></table></div>
<div class="box"><h3>۲) اقلام برگشتی</h3>
<table><thead><tr><th>ردیف</th><th>کد</th><th>نام</th><th>تعداد</th><th>قیمت</th><th>جمع</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<p><strong>جمع برگشتی: {total:,} ریال</strong></p></div>
<div class="money">{money_label}: {total:,} ریال</div>
</body></html>""".format(
        company_name=company.get('company_name', ''), ceo=company.get('ceo_name', ''),
        national=company.get('national_id', ''), address=company.get('address', ''),
        phone=company.get('phone', ''),
        doc_label=doc_label, smart_no=meta['smart_no'], source_doc_no=meta['source_doc_no'],
        src_txt=(jalali_date_display_from_iso(src_date) + ' / ' + src_date) if src_date else '-',
        person=person,
        ret_txt=jalali_date_display_from_iso(meta['return_date']) if meta['return_date'] else '-',
        reason=meta['reason'] or '-', rows_html=rows_html,
        orig_qty=orig_qty, orig_amount=orig_amount, total=total, money_label=money_label)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        path = f.name
    webbrowser.open('file:///' + path)
