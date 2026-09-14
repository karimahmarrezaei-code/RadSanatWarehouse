# -*- coding: utf-8 -*-
"""letterhead.py - تنها نقطهٔ کنترل سربرگ شرکت برای همهٔ اسناد چاپی"""
import re
from typing import Any, Dict

_FIELDS = ['company_name', 'ceo_name', 'national_id', 'economic_code', 'registration_number',
           'phone', 'mobile', 'email', 'website', 'address']
_START = '<!-- LH-START -->'
_END = '<!-- LH-END -->'


def get_company_profile(db) -> Dict[str, Any]:
    try:
        from app.repositories.company_repository import CompanyRepository
        return CompanyRepository(db).get_company_profile() or {}
    except Exception:
        return {}


def filtered_company(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {f: (profile.get(f) if (bool(profile.get('show_' + f, 1)) and bool((profile.get(f) or '').strip())) else '')
            for f in _FIELDS}


def get_filtered_company(db) -> Dict[str, Any]:
    return filtered_company(get_company_profile(db))


def render_letterhead_html(profile: Dict[str, Any]) -> str:
    c = filtered_company(profile)
    if not any(c.values()):
        return ''
    nat = ' | '.join(x for x in [
        ('شناسه ملی: ' + c['national_id']) if c['national_id'] else '',
        ('کد اقتصادی: ' + c['economic_code']) if c['economic_code'] else '',
        ('شماره ثبت: ' + c['registration_number']) if c['registration_number'] else ''] if x)
    contact = ' | '.join(x for x in [
        ('تلفن: ' + c['phone']) if c['phone'] else '',
        ('موبایل: ' + c['mobile']) if c['mobile'] else '',
        ('ایمیل: ' + c['email']) if c['email'] else '',
        ('وب‌سایت: ' + c['website']) if c['website'] else ''] if x)
    p12 = 'margin:2px 0;font-size:12px;color:#334155;'
    parts = []
    if c['company_name']:
        parts.append('<h1 style="margin:0;font-size:16px;color:#1e293b;">{}</h1>'.format(c['company_name']))
    if c['ceo_name']:
        parts.append('<p style="{}">مدیر عامل: {}</p>'.format(p12, c['ceo_name']))
    if nat:
        parts.append('<p style="{}">{}</p>'.format(p12, nat))
    if contact:
        parts.append('<p style="{}">{}</p>'.format(p12, contact))
    if c['address']:
        parts.append('<p style="{}">آدرس: {}</p>'.format(p12, c['address']))
    return '{}<div style="text-align:right;margin-bottom:12px;border-bottom:2px solid #2563eb;padding-bottom:8px;">{}</div>{}'.format(
        _START, ''.join(parts), _END)


def build_letterhead_html(profile: Dict[str, Any]) -> str:
    return render_letterhead_html(profile)


def finalize_print_html(db, html: str) -> str:
    """تزریق سربرگ به‌صورت idempotent - تنها نقطهٔ تماس برای همهٔ اسناد"""
    try:
        html = re.sub(re.escape(_START) + r'.*?' + re.escape(_END), '', html, flags=re.S)
        lh = render_letterhead_html(get_company_profile(db))
        if lh:
            html = html.replace('<body>', '<body>' + lh, 1)
    except Exception:
        pass
    return html