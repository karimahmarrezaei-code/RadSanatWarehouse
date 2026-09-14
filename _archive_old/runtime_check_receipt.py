# -*- coding: utf-8 -*-
import sys, traceback
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)

try:
    from app.core.database import DatabaseManager
    db = DatabaseManager()
    from app.ui.receipt_manager_window import ReceiptManagerWindow
    w = ReceiptManagerWindow(db, {'id': 1, 'role_code': 'ADMIN', 'permissions': ['receipts.manage']})
    print('✅ فرم ساخته شد.')
    print('warehouse_combo دارد؟', hasattr(w, 'warehouse_combo'))
    if hasattr(w, 'warehouse_combo'):
        print('تعداد گزینه‌های انبار:', w.warehouse_combo.count())
        print('متن پیام:', w.warehouse_msg_lbl.text())
        print('پیام مخفی است؟', w.warehouse_msg_lbl.isHidden())
except Exception:
    print('❌ خطا هنگام ساخت فرم:')
    traceback.print_exc()