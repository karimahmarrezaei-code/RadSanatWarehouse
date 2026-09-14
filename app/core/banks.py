# -*- coding: utf-8 -*-
"""بارگذاری لیست نام بانک‌ها از فایل JSON"""

import json
from pathlib import Path
from typing import List

_BANKS_FILE = Path(__file__).with_name('banks.json')

_DEFAULT_BANKS = [
    'بانک ملی ایران', 'بانک سپه', 'بانک ملت', 'بانک تجارت',
    'بانک صادرات ایران', 'بانک اقتصاد نوین', 'بانک پارسیان',
    'بانک پاسارگاد', 'بانک سامان', 'بانک شهر', 'بانک مسکن',
]


def get_bank_names() -> List[str]:
    """خواندن نام بانک‌ها از banks.json (در صورت خطا، لیست پیش‌فرض)"""
    try:
        data = json.loads(_BANKS_FILE.read_text(encoding='utf-8'))
        names = [str(item).strip() for item in data if str(item).strip()]
        return names or list(_DEFAULT_BANKS)
    except Exception:
        return list(_DEFAULT_BANKS)