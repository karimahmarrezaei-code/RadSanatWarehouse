from datetime import date, datetime


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def today_iso_date() -> str:
    return datetime.now().date().isoformat()


def _jalali_datetime_from_gregorian(value: datetime):
    import jdatetime  # type: ignore

    return jdatetime.datetime.fromgregorian(datetime=value)


def _jalali_date_from_gregorian(value: date):
    import jdatetime  # type: ignore

    return jdatetime.date.fromgregorian(date=value)


def format_now_for_display() -> str:
    gregorian = datetime.now().strftime('%Y-%m-%d %H:%M')
    try:
        jalali = _jalali_datetime_from_gregorian(datetime.now()).strftime('%Y/%m/%d %H:%M')
        return f'شمسی: {jalali} | میلادی: {gregorian}'
    except Exception:
        return f'میلادی: {gregorian}'


def jalali_date_display_from_iso(iso_date: str) -> str:
    try:
        gregorian_date = date.fromisoformat(iso_date)
        return _jalali_date_from_gregorian(gregorian_date).strftime('%Y/%m/%d')
    except Exception:
        return iso_date


def jalali_date_compact_from_iso(iso_date: str) -> str:
    try:
        gregorian_date = date.fromisoformat(iso_date)
        return _jalali_date_from_gregorian(gregorian_date).strftime('%Y%m%d')
    except Exception:
        return iso_date.replace('-', '')
