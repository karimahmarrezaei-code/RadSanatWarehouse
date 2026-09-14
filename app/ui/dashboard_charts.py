from __future__ import annotations

from html import escape
from typing import Dict, List


def _fmt_money(value: int) -> str:
    return f'{int(value):,} ریال'


def _svg_container(title: str, subtitle: str, svg_body: str, height: int = 280) -> str:
    return f"""
    <html lang='fa' dir='rtl'>
    <body style="margin:0; background:#39424f; color:#e5e7eb; font-family:Segoe UI, Tahoma, Arial, sans-serif;">
      <div style="padding:10px 12px;">
        <div style="font-size:15px; font-weight:700; color:#f8fafc;">{escape(title)}</div>
        <div style="font-size:11px; color:#64748b; margin:4px 0 8px 0;">{escape(subtitle)}</div>
        <svg width="100%" height="{height}" viewBox="0 0 720 {height}" xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="720" height="{height}" rx="16" fill="#39424f" />
          {svg_body}
        </svg>
      </div>
    </body>
    </html>
    """


def build_warehouse_value_chart(rows: List[Dict], title: str = 'ارزش ریالی انبارها', subtitle: str = 'مقایسه ارزش فعلی موجودی در انبارها') -> str:
    if not rows:
        body = "<text x='360' y='150' fill='#64748b' font-size='18' text-anchor='middle'>داده ای برای نمایش وجود ندارد</text>"
        return _svg_container(title, subtitle, body)

    max_value = max(max(abs(int(item.get('current_value') or item.get('period_value_delta') or 0)), 1) for item in rows)
    chart_x = 70
    chart_y = 30
    chart_w = 600
    chart_h = 200
    bar_gap = 18
    bar_w = max(36, int((chart_w - bar_gap * (len(rows) - 1)) / max(len(rows), 1)))
    base_y = chart_y + chart_h
    body_parts = [
        f"<line x1='{chart_x}' y1='{base_y}' x2='{chart_x + chart_w}' y2='{base_y}' stroke='#5b6675' stroke-width='2'/>"
    ]
    for idx, item in enumerate(rows):
        value = int(item.get('current_value') if item.get('current_value') is not None else item.get('period_value_delta') or 0)
        height = int((abs(value) / max_value) * (chart_h - 20)) if max_value else 0
        x = chart_x + idx * (bar_w + bar_gap)
        y = base_y - height if value >= 0 else base_y
        label = f"{item.get('code') or ''}"
        name = item.get('name') or ''
        qty = int(item.get('current_qty') if item.get('current_qty') is not None else item.get('period_qty_delta') or 0)
        color = '#38bdf8' if value >= 0 else '#f59e0b'
        body_parts.extend([
            f"<rect x='{x}' y='{y}' width='{bar_w}' height='{height}' rx='10' fill='{color}' opacity='0.95'/>",
            f"<text x='{x + bar_w/2}' y='{(y - 8) if value >= 0 else (y + height + 16)}' fill='#e5e7eb' font-size='11' text-anchor='middle'>{value:,}</text>",
            f"<text x='{x + bar_w/2}' y='{base_y + 26}' fill='#93c5fd' font-size='11' text-anchor='middle'>{escape(label[:10])}</text>",
            f"<text x='{x + bar_w/2}' y='{base_y + 42}' fill='#64748b' font-size='10' text-anchor='middle'>{qty:,} عدد</text>",
            f"<title>{escape(name)} | ارزش: {_fmt_money(value)} | تعداد: {qty:,}</title>",
        ])
    return _svg_container(title, subtitle, ''.join(body_parts))


def build_financial_balance_chart(summary: Dict, title: str = 'نمای مالی مدیریتی', subtitle: str = 'مقایسه مانده دریافتنی و پرداختنی') -> str:
    receivable = int(summary.get('receivable_balance') or 0)
    payable = int(summary.get('payable_balance') or 0)
    total = max(receivable + payable, 1)
    receivable_width = int((receivable / total) * 520)
    payable_width = int((payable / total) * 520)
    open_docs = int(summary.get('open_docs') or 0)
    settled_docs = int(summary.get('settled_docs') or 0)
    body = f"""
      <rect x='90' y='70' width='520' height='36' rx='18' fill='#1f2937'/>
      <rect x='90' y='70' width='{receivable_width}' height='36' rx='18' fill='#047857'/>
      <rect x='{90 + receivable_width}' y='70' width='{payable_width}' height='36' rx='18' fill='#f59e0b'/>
      <text x='90' y='56' fill='#a7f3d0' font-size='14'>مانده دریافتنی: {_fmt_money(receivable)}</text>
      <text x='610' y='56' fill='#fde68a' font-size='14' text-anchor='end'>مانده پرداختنی: {_fmt_money(payable)}</text>
      <rect x='90' y='150' width='250' height='90' rx='18' fill='#172033' stroke='#25324a'/>
      <rect x='360' y='150' width='250' height='90' rx='18' fill='#172033' stroke='#25324a'/>
      <text x='215' y='185' fill='#93c5fd' font-size='14' text-anchor='middle'>اسناد باز</text>
      <text x='215' y='220' fill='#f8fafc' font-size='28' font-weight='700' text-anchor='middle'>{open_docs}</text>
      <text x='485' y='185' fill='#93c5fd' font-size='14' text-anchor='middle'>اسناد تسویه</text>
      <text x='485' y='220' fill='#f8fafc' font-size='28' font-weight='700' text-anchor='middle'>{settled_docs}</text>
    """
    return _svg_container(title, subtitle, body)



def build_treasury_balance_chart(rows: List[Dict], title: str = 'مانده صندوق / بانک', subtitle: str = 'وضعیت مانده فعلی خزانه') -> str:
    if not rows:
        body = "<text x='360' y='150' fill='#64748b' font-size='18' text-anchor='middle'>هیچ صندوق یا حساب بانکی فعالی ثبت نشده است</text>"
        return _svg_container(title, subtitle, body)
    max_value = max(max(abs(int(item.get('current_balance') or item.get('period_balance_delta') or 0)), 1) for item in rows)
    body_parts = []
    start_y = 34
    row_h = 38
    for idx, item in enumerate(rows[:6]):
        y = start_y + idx * row_h
        value = int(item.get('current_balance') if item.get('current_balance') is not None else item.get('period_balance_delta') or 0)
        width = int((abs(value) / max_value) * 420) if max_value else 0
        color = '#22c55e' if value >= 0 else '#f97316'
        label = f"{item.get('code')} | {item.get('name')}"
        body_parts.extend([
            f"<text x='80' y='{y + 20}' fill='#e5e7eb' font-size='12'>{escape(label[:34])}</text>",
            f"<rect x='250' y='{y}' width='420' height='24' rx='12' fill='#1f2937'/>",
            f"<rect x='250' y='{y}' width='{width}' height='24' rx='12' fill='{color}'/>",
            f"<text x='{min(660, 250 + width + 8)}' y='{y + 17}' fill='#cbd5e1' font-size='11'>{value:,}</text>",
        ])
    return _svg_container(title, subtitle, ''.join(body_parts), height=300)



def build_activity_chart(rows: List[Dict], title: str = 'روند 7 روز اخیر', subtitle: str = 'تعداد رسید، حواله و اسناد مالی') -> str:
    if not rows:
        body = "<text x='360' y='150' fill='#64748b' font-size='18' text-anchor='middle'>عملیاتی برای این بازه ثبت نشده است</text>"
        return _svg_container(title, subtitle, body)

    max_value = max(max(int(item.get('receipts') or 0), int(item.get('issues') or 0), int(item.get('finance_docs') or 0), 1) for item in rows)
    chart_x = 90
    chart_y = 30
    chart_h = 190
    chart_w = 560
    col_w = int(chart_w / max(len(rows), 1))
    body_parts = [
        f"<line x1='{chart_x}' y1='{chart_y + chart_h}' x2='{chart_x + chart_w}' y2='{chart_y + chart_h}' stroke='#5b6675' stroke-width='2'/>"
    ]
    colors = {'receipts': '#38bdf8', 'issues': '#f59e0b', 'finance_docs': '#047857'}
    for idx, item in enumerate(rows):
        base_x = chart_x + idx * col_w + 14
        label = str(item.get('day_label') or '')[-5:]
        for offset, key in enumerate(['receipts', 'issues', 'finance_docs']):
            value = int(item.get(key) or 0)
            bar_h = int((value / max_value) * 120) if max_value else 0
            x = base_x + offset * 18
            y = chart_y + chart_h - bar_h
            body_parts.append(f"<rect x='{x}' y='{y}' width='14' height='{bar_h}' rx='4' fill='{colors[key]}'/>")
        body_parts.append(f"<text x='{base_x + 18}' y='{chart_y + chart_h + 18}' fill='#93c5fd' font-size='10' text-anchor='middle'>{escape(label)}</text>")
    body_parts.append("<text x='90' y='252' fill='#38bdf8' font-size='11'>■ رسید</text><text x='165' y='252' fill='#f59e0b' font-size='11'>■ حواله</text><text x='250' y='252' fill='#047857' font-size='11'>■ سند مالی</text>")
    return _svg_container(title, subtitle, ''.join(body_parts))
