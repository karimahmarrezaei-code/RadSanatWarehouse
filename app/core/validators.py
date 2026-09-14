import re
from pathlib import Path
from typing import Any, Dict, List


class ValidationError(Exception):
    pass


VEHICLE_TYPES = [
    'سواری',
    'وانت',
    'خاور',
    'کامیون سبک',
    'کامیون سنگین',
    'تریلی',
    'کفی 12 متری',
]

PERSON_ROLE_TYPES = ['CUSTOMER', 'SUPPLIER', 'DRIVER']
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _normalize_text(value: Any) -> str:
    return str(value or '').strip()


def _digits_only(value: Any) -> str:
    return ''.join(ch for ch in _normalize_text(value) if ch.isdigit())


def _to_non_negative_int(value: Any, field_title: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f'{field_title} باید عدد صحیح باشد.') from exc
    if number < 0:
        raise ValidationError(f'{field_title} نمی‌تواند منفی باشد.')
    return number


def _to_positive_int(value: Any, field_title: str) -> int:
    number = _to_non_negative_int(value, field_title)
    if number <= 0:
        raise ValidationError(f'{field_title} باید بیشتر از صفر باشد.')
    return number


def _parse_int_from_text(value: Any, field_title: str, allow_zero: bool = True) -> int:
    raw = _normalize_text(value)
    if raw == '':
        raw = '0' if allow_zero else ''
    digits = raw if raw.isdigit() else _digits_only(raw)
    if digits == '':
        raise ValidationError(f'{field_title} باید عدد صحیح باشد.')
    number = int(digits)
    if not allow_zero and number <= 0:
        raise ValidationError(f'{field_title} باید بیشتر از صفر باشد.')
    return number


def _normalize_mobile(value: Any) -> str:
    digits = _digits_only(value)
    if not digits:
        return ''
    if digits.startswith('98') and len(digits) == 12:
        digits = '0' + digits[2:]
    if len(digits) == 10 and digits.startswith('9'):
        digits = '0' + digits
    if len(digits) != 11 or not digits.startswith('09'):
        raise ValidationError('شماره موبایل معتبر نیست.')
    return digits


def _validate_email(value: Any) -> str:
    email = _normalize_text(value)
    if email and not EMAIL_RE.match(email):
        raise ValidationError('ایمیل معتبر نیست.')
    return email


def _validate_national_id(value: Any) -> str:
    national_id = _digits_only(value)
    if not national_id:
        return ''
    if len(national_id) != 10:
        raise ValidationError('کد ملی باید 10 رقم باشد.')
    if len(set(national_id)) == 1:
        raise ValidationError('کد ملی معتبر نیست.')
    check = int(national_id[9])
    total = sum(int(national_id[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    valid = (check == remainder if remainder < 2 else check == 11 - remainder)
    if not valid:
        raise ValidationError('کد ملی معتبر نیست.')
    return national_id


def validate_pallet_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    code = _normalize_text(payload.get('code'))
    name = _normalize_text(payload.get('name'))
    material_type = _normalize_text(payload.get('material_type'))
    image_path = _normalize_text(payload.get('image_path'))
    description = _normalize_text(payload.get('description'))

    if not code:
        raise ValidationError('کد پالت الزامی است.')
    if len(code) > 50:
        raise ValidationError('کد پالت نباید بیشتر از 50 کاراکتر باشد.')
    if not name:
        raise ValidationError('نام پالت الزامی است.')
    if len(name) > 120:
        raise ValidationError('نام پالت نباید بیشتر از 120 کاراکتر باشد.')
    if not material_type:
        raise ValidationError('جنس پالت الزامی است.')
    if len(material_type) > 80:
        raise ValidationError('جنس پالت نباید بیشتر از 80 کاراکتر باشد.')

    if image_path:
        path = Path(image_path)
        allowed = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}
        if path.suffix.lower() not in allowed:
            raise ValidationError('فرمت تصویر پالت معتبر نیست.')

    return {
        'code': code,
        'name': name,
        'material_type': material_type,
        'length_cm': _to_positive_int(payload.get('length_cm'), 'طول'),
        'width_cm': _to_positive_int(payload.get('width_cm'), 'عرض'),
        'height_cm': _to_positive_int(payload.get('height_cm'), 'ارتفاع'),
        'opening_stock': _to_non_negative_int(payload.get('opening_stock'), 'موجودی اولیه'),
        'low_stock_threshold': _to_non_negative_int(payload.get('low_stock_threshold'), 'حد هشدار'),
        'image_path': image_path or None,
        'description': description or None,
        'is_active': 1 if bool(payload.get('is_active', True)) else 0,
    }


def validate_warehouse_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    code = _normalize_text(payload.get('code'))
    name = _normalize_text(payload.get('name'))
    address = _normalize_text(payload.get('address'))

    if not code:
        raise ValidationError('کد انبار الزامی است.')
    if len(code) > 50:
        raise ValidationError('کد انبار نباید بیشتر از 50 کاراکتر باشد.')
    if not name:
        raise ValidationError('نام انبار الزامی است.')
    if len(name) > 120:
        raise ValidationError('نام انبار نباید بیشتر از 120 کاراکتر باشد.')
    if address and len(address) > 500:
        raise ValidationError('آدرس انبار نباید بیشتر از 500 کاراکتر باشد.')

    return {
        'code': code,
        'name': name,
        'capacity_count': _to_non_negative_int(payload.get('capacity_count'), 'ظرفیت انبار'),
        'address': address or None,
        'is_active': 1 if bool(payload.get('is_active', True)) else 0,
    }


def validate_treasury_account_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    code = _normalize_text(payload.get('code'))
    name = _normalize_text(payload.get('name'))
    account_type = _normalize_text(payload.get('account_type'))
    bank_name = _normalize_text(payload.get('bank_name'))
    account_number = _digits_only(payload.get('account_number'))
    iban = _normalize_text(payload.get('iban')).upper().replace(' ', '')
    card_number = _digits_only(payload.get('card_number'))
    branch_name = _normalize_text(payload.get('branch_name'))
    branch_code = _normalize_text(payload.get('branch_code'))
    description = _normalize_text(payload.get('description'))

    if not code:
        raise ValidationError('کد صندوق / بانک الزامی است.')
    if len(code) > 50:
        raise ValidationError('کد صندوق / بانک نباید بیشتر از 50 کاراکتر باشد.')
    if not name:
        raise ValidationError('نام صندوق / بانک الزامی است.')
    if len(name) > 120:
        raise ValidationError('نام صندوق / بانک نباید بیشتر از 120 کاراکتر باشد.')
    if account_type not in {'CASHBOX', 'BANK'}:
        raise ValidationError('نوع حساب باید صندوق یا بانک باشد.')

    if account_type == 'BANK' and not bank_name:
        raise ValidationError('برای حساب بانکی، نام بانک الزامی است.')
    if card_number and len(card_number) != 16:
        raise ValidationError('شماره کارت باید 16 رقم باشد.')
    if iban and not (iban.startswith('IR') and len(iban) == 26 and iban[2:].isdigit()):
        raise ValidationError('شماره شبا باید با IR شروع شود و 26 کاراکتر باشد.')

    return {
        'code': code,
        'name': name,
        'account_type': account_type,
        'bank_name': bank_name or None,
        'account_number': account_number or None,
        'iban': iban or None,
        'card_number': card_number or None,
        'branch_name': branch_name or None,
        'branch_code': branch_code or None,
        'opening_balance': _to_non_negative_int(payload.get('opening_balance'), 'موجودی اولیه'),
        'is_active': 1 if bool(payload.get('is_active', True)) else 0,
        'description': description or None,
    }


def validate_bank_account_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    bank_name = _normalize_text(payload.get('bank_name'))
    account_number = _digits_only(payload.get('account_number'))
    iban = _normalize_text(payload.get('iban')).upper().replace(' ', '')
    card_number = _digits_only(payload.get('card_number'))
    branch_name = _normalize_text(payload.get('branch_name'))
    branch_code = _normalize_text(payload.get('branch_code'))

    if not bank_name:
        raise ValidationError('نام بانک الزامی است.')
    if len(bank_name) > 100:
        raise ValidationError('نام بانک نباید بیشتر از 100 کاراکتر باشد.')
    if account_number and len(account_number) > 32:
        raise ValidationError('شماره حساب معتبر نیست.')
    if card_number and len(card_number) != 16:
        raise ValidationError('شماره کارت باید 16 رقم باشد.')
    if iban and not (iban.startswith('IR') and len(iban) == 26 and iban[2:].isdigit()):
        raise ValidationError('شماره شبا باید با IR شروع شود و 26 کاراکتر باشد.')

    return {
        'bank_name': bank_name,
        'account_number': account_number or None,
        'iban': iban or None,
        'card_number': card_number or None,
        'branch_name': branch_name or None,
        'branch_code': branch_code or None,
        'is_default': 1 if bool(payload.get('is_default', False)) else 0,
    }


def validate_person_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    first_name = _normalize_text(payload.get('first_name'))
    last_name = _normalize_text(payload.get('last_name'))
    address = _normalize_text(payload.get('address'))
    notes = _normalize_text(payload.get('notes'))
    province_name = _normalize_text(payload.get('province_name'))
    city_name = _normalize_text(payload.get('city_name'))

    if not first_name:
        raise ValidationError('نام الزامی است.')
    if len(first_name) > 80:
        raise ValidationError('نام نباید بیشتر از 80 کاراکتر باشد.')
    if not last_name:
        raise ValidationError('نام خانوادگی الزامی است.')
    if len(last_name) > 120:
        raise ValidationError('نام خانوادگی نباید بیشتر از 120 کاراکتر باشد.')

    roles = [role for role in payload.get('roles', []) if role in PERSON_ROLE_TYPES]
    roles = list(dict.fromkeys(roles))
    if not roles:
        raise ValidationError('حداقل یکی از نقش‌های مشتری، تامین‌کننده یا راننده باید انتخاب شود.')

    province_code = payload.get('province_code')
    city_code = payload.get('city_code')
    if province_code in (None, '', 0):
        province_code = None
        province_name = None
        city_code = None
        city_name = None
    else:
        try:
            province_code = int(province_code)
        except (TypeError, ValueError) as exc:
            raise ValidationError('استان انتخابی معتبر نیست.') from exc
        if not province_name:
            raise ValidationError('نام استان معتبر نیست.')
        if city_code not in (None, '', 0):
            try:
                city_code = int(city_code)
            except (TypeError, ValueError) as exc:
                raise ValidationError('شهر انتخابی معتبر نیست.') from exc
            if not city_name:
                raise ValidationError('نام شهر معتبر نیست.')
        else:
            city_code = None
            city_name = None

    driver_profile = payload.get('driver_profile') or {}
    if 'DRIVER' in roles:
        vehicle_type = _normalize_text(driver_profile.get('vehicle_type'))
        vehicle_plate = _normalize_text(driver_profile.get('vehicle_plate'))
        driver_notes = _normalize_text(driver_profile.get('notes'))
        if vehicle_type not in VEHICLE_TYPES:
            raise ValidationError('نوع وسیله نقلیه راننده معتبر نیست.')
        if not vehicle_plate:
            raise ValidationError('شماره پلاک خودرو برای راننده الزامی است.')
        if len(vehicle_plate) > 30:
            raise ValidationError('شماره پلاک خودرو معتبر نیست.')
        driver_profile_normalized = {
            'vehicle_type': vehicle_type,
            'vehicle_plate': vehicle_plate,
            'notes': driver_notes or None,
        }
    else:
        driver_profile_normalized = None

    bank_accounts_input = payload.get('bank_accounts') or []
    bank_accounts: List[Dict[str, Any]] = []
    for item in bank_accounts_input:
        if not any(_normalize_text(item.get(key)) for key in ('bank_name', 'account_number', 'iban', 'card_number', 'branch_name', 'branch_code')):
            continue
        bank_accounts.append(validate_bank_account_payload(item))

    if bank_accounts and not any(account['is_default'] for account in bank_accounts):
        bank_accounts[0]['is_default'] = 1
    if sum(1 for account in bank_accounts if account['is_default']) > 1:
        raise ValidationError('فقط یک حساب بانکی می‌تواند پیش‌فرض باشد.')

    return {
        'national_id': _validate_national_id(payload.get('national_id')) or None,
        'first_name': first_name,
        'last_name': last_name,
        'mobile': _normalize_mobile(payload.get('mobile')) or None,
        'email': _validate_email(payload.get('email')) or None,
        'province_code': province_code,
        'province_name': province_name,
        'city_code': city_code,
        'city_name': city_name,
        'address': address or None,
        'notes': notes or None,
        'is_active': 1 if bool(payload.get('is_active', True)) else 0,
        'roles': roles,
        'driver_profile': driver_profile_normalized,
        'bank_accounts': bank_accounts,
    }


def _validate_operation_lines(lines_in: List[Dict[str, Any]], operation_title: str) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    for index, line in enumerate(lines_in, start=1):
        pallet_id = line.get('pallet_id')
        warehouse_id = line.get('warehouse_id')
        quantity_raw = line.get('quantity')
        unit_price_raw = line.get('unit_price')
        defect_notes = _normalize_text(line.get('defect_notes'))
        description = _normalize_text(line.get('description'))

        if not pallet_id and not warehouse_id and _normalize_text(quantity_raw) == '' and _normalize_text(unit_price_raw) == '':
            continue
        if not pallet_id:
            raise ValidationError(f'پالت در ردیف {index} {operation_title} انتخاب نشده است.')
        if not warehouse_id:
            raise ValidationError(f'انبار در ردیف {index} {operation_title} انتخاب نشده است.')

        quantity = _parse_int_from_text(quantity_raw, f'تعداد ردیف {index}', allow_zero=False)
        unit_price = _parse_int_from_text(unit_price_raw, f'قیمت ردیف {index}', allow_zero=True)
        lines.append(
            {
                'pallet_id': int(pallet_id),
                'warehouse_id': int(warehouse_id),
                'quantity': quantity,
                'unit_price': unit_price,
                'line_total_amount': quantity * unit_price,
                'defect_notes': defect_notes or None,
                'description': description or None,
            }
        )
    return lines


def validate_opening_inventory_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    opening_date = _normalize_text(payload.get('opening_date'))
    if not opening_date:
        raise ValidationError('تاریخ افتتاحیه الزامی است.')
    warehouse_id = payload.get('warehouse_id')
    if not warehouse_id:
        raise ValidationError('انتخاب انبار الزامی است.')

    lines_in = payload.get('lines') or []
    lines: List[Dict[str, Any]] = []
    seen_pallets = set()
    for index, line in enumerate(lines_in, start=1):
        pallet_id = line.get('pallet_id')
        qty_raw = line.get('qty')
        unit_price_raw = line.get('unit_price')
        description = _normalize_text(line.get('description'))
        if not pallet_id and _normalize_text(qty_raw) == '' and _normalize_text(unit_price_raw) == '':
            continue
        if not pallet_id:
            raise ValidationError(f'پالت در ردیف {index} انتخاب نشده است.')
        if pallet_id in seen_pallets:
            raise ValidationError('تکرار پالت در یک سند افتتاحیه مجاز نیست.')
        seen_pallets.add(pallet_id)
        qty = _parse_int_from_text(qty_raw, f'تعداد ردیف {index}', allow_zero=False)
        unit_price = _parse_int_from_text(unit_price_raw, f'قیمت ردیف {index}', allow_zero=True)
        lines.append(
            {
                'pallet_id': int(pallet_id),
                'qty': qty,
                'unit_price': unit_price,
                'total_price': qty * unit_price,
                'description': description or None,
            }
        )
    if not lines:
        raise ValidationError('حداقل یک ردیف برای افتتاحیه لازم است.')

    total_qty = sum(item['qty'] for item in lines)
    total_amount = sum(item['total_price'] for item in lines)
    return {
        'opening_date': opening_date,
        'warehouse_id': int(warehouse_id),
        'description': _normalize_text(payload.get('description')) or None,
        'lines': lines,
        'total_types_count': len(lines),
        'total_qty': total_qty,
        'total_amount': total_amount,
    }


def validate_receipt_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    operation_date = _normalize_text(payload.get('operation_date'))
    if not operation_date:
        raise ValidationError('تاریخ عملیات الزامی است.')

    supplier_person_id = payload.get('supplier_person_id')
    driver_person_id = payload.get('driver_person_id')
    if not supplier_person_id:
        raise ValidationError('انتخاب تأمین‌کننده الزامی است.')
    if not driver_person_id:
        raise ValidationError('انتخاب راننده الزامی است.')

    total_declared_qty = _parse_int_from_text(payload.get('total_declared_qty'), 'تعداد کل بار', allow_zero=False)
    stage_declared_qty = _parse_int_from_text(payload.get('stage_declared_qty'), 'تعداد بار این مرحله', allow_zero=False)
    stage_received_qty = _parse_int_from_text(payload.get('stage_received_qty'), 'تعداد تحویل به انبار', allow_zero=False)
    freight_amount = _parse_int_from_text(payload.get('freight_amount'), 'مبلغ پس‌کرایه', allow_zero=True)

    if stage_declared_qty > total_declared_qty:
        raise ValidationError('تعداد این مرحله نمی‌تواند از تعداد کل بار بیشتر باشد.')
    if stage_received_qty > stage_declared_qty:
        raise ValidationError('تعداد تحویل شده نمی‌تواند از تعداد بار این مرحله بیشتر باشد.')

    warehouse_keeper_name = _normalize_text(payload.get('warehouse_keeper_name'))
    receiver_name = _normalize_text(payload.get('receiver_name'))
    source_location = _normalize_text(payload.get('source_location'))
    destination_location = _normalize_text(payload.get('destination_location'))
    notes = _normalize_text(payload.get('notes'))
    waybill_no = _normalize_text(payload.get('waybill_no'))

    lines = _validate_operation_lines(payload.get('lines') or [], 'رسید')
    if not lines:
        raise ValidationError('حداقل یک ردیف پالت برای رسید لازم است.')

    total_line_qty = sum(line['quantity'] for line in lines)
    if total_line_qty != stage_received_qty:
        raise ValidationError('جمع تعداد ردیف‌های پالت باید با تعداد تحویل به انبار برابر باشد.')

    return {
        'inbound_load_id': int(payload['inbound_load_id']) if payload.get('inbound_load_id') else None,
        'operation_date': operation_date,
        'supplier_person_id': int(supplier_person_id),
        'driver_person_id': int(driver_person_id),
        'total_declared_qty': total_declared_qty,
        'stage_declared_qty': stage_declared_qty,
        'stage_received_qty': stage_received_qty,
        'freight_amount': freight_amount,
        'waybill_no': waybill_no or None,
        'source_location': source_location or None,
        'destination_location': destination_location or None,
        'warehouse_keeper_name': warehouse_keeper_name or None,
        'receiver_name': receiver_name or None,
        'notes': notes or None,
        'lines': lines,
    }


def validate_issue_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    operation_date = _normalize_text(payload.get('operation_date'))
    if not operation_date:
        raise ValidationError('تاریخ عملیات الزامی است.')

    customer_person_id = payload.get('customer_person_id')
    driver_person_id = payload.get('driver_person_id')
    if not customer_person_id:
        raise ValidationError('انتخاب مشتری الزامی است.')
    if not driver_person_id:
        raise ValidationError('انتخاب راننده الزامی است.')

    total_declared_qty = _parse_int_from_text(payload.get('total_declared_qty'), 'تعداد کل بار', allow_zero=False)
    stage_declared_qty = _parse_int_from_text(payload.get('stage_declared_qty'), 'تعداد بار این مرحله', allow_zero=False)
    delivered_qty = _parse_int_from_text(payload.get('delivered_qty'), 'تعداد تحویل خروج', allow_zero=False)
    freight_amount = _parse_int_from_text(payload.get('freight_amount'), 'مبلغ پس‌کرایه', allow_zero=True)

    if stage_declared_qty > total_declared_qty:
        raise ValidationError('تعداد این مرحله نمی‌تواند از تعداد کل بار بیشتر باشد.')
    if delivered_qty > stage_declared_qty:
        raise ValidationError('تعداد تحویل خروج نمی‌تواند از تعداد بار این مرحله بیشتر باشد.')

    warehouse_keeper_name = _normalize_text(payload.get('warehouse_keeper_name'))
    receiver_name = _normalize_text(payload.get('receiver_name'))
    source_location = _normalize_text(payload.get('source_location'))
    destination_location = _normalize_text(payload.get('destination_location'))
    notes = _normalize_text(payload.get('notes'))
    waybill_no = _normalize_text(payload.get('waybill_no'))

    lines = _validate_operation_lines(payload.get('lines') or [], 'حواله خروج')
    if not lines:
        raise ValidationError('حداقل یک ردیف پالت برای حواله خروج لازم است.')

    total_line_qty = sum(line['quantity'] for line in lines)
    if total_line_qty != delivered_qty:
        raise ValidationError('جمع تعداد ردیف‌های پالت باید با تعداد تحویل خروج برابر باشد.')

    return {
        'outbound_load_id': int(payload['outbound_load_id']) if payload.get('outbound_load_id') else None,
        'operation_date': operation_date,
        'customer_person_id': int(customer_person_id),
        'driver_person_id': int(driver_person_id),
        'total_declared_qty': total_declared_qty,
        'stage_declared_qty': stage_declared_qty,
        'delivered_qty': delivered_qty,
        'freight_amount': freight_amount,
        'waybill_no': waybill_no or None,
        'source_location': source_location or None,
        'destination_location': destination_location or None,
        'warehouse_keeper_name': warehouse_keeper_name or None,
        'receiver_name': receiver_name or None,
        'notes': notes or None,
        'lines': lines,
    }
