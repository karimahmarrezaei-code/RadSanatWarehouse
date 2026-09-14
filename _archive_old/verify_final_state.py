# -*- coding: utf-8 -*-
"""راستی‌آزمایی نهایی سه مخزن - اجرا: python verify_final_state.py"""
import os, py_compile

ROOT = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(ROOT, 'app', 'repositories')
checks = {
    'issue_repository.py': ['از ماندهٔ مرجع', 'outbound_load_items (outbound_load_id, row_no'],
    'receipt_repository.py': ['vehicle_type_i', 'inbound_load_items (inbound_load_id, row_no',
                              'remaining_row = conn.execute'],
    'return_repository.py': ['[ADD-NET]'],
}
all_ok = True
for fn, marks in checks.items():
    p = os.path.join(R, fn)
    s = open(p, encoding='utf-8', errors='replace').read()
    okc = True
    try:
        py_compile.compile(p, doraise=True)
    except Exception as e:
        okc = False
        all_ok = False
        print('❌ کامپایل', fn, ':', str(e)[:100])
    missing = [m for m in marks if m not in s]
    extra_conn = (fn == 'receipt_repository.py') and ('check_conn' in s)
    if missing or extra_conn:
        all_ok = False
    print('{} {} | کامپایل: {} | جامانده: {} | اتصال جداگانه: {}'.format(
        '✔' if (okc and not missing and not extra_conn) else '⚠️',
        fn, 'OK' if okc else 'FAIL', missing or '-', 'دارد!' if extra_conn else 'ندارد'))
print('\nنتیجه:', '✅ همه‌چیز کامل و سالم — آمادهٔ تست و گیت' if all_ok else '⚠️ موارد بالا را ببینید')
input('Enter...')