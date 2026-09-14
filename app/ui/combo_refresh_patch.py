# -*- coding: utf-8 -*-
# combo_refresh_patch - رفرش زنده کامبو مرجع خروج + حفظ انبار پس از ثبت
from PyQt5.QtCore import QObject, QEvent

class _RefComboFilter(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.w = window
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            try:
                self.w._reload_open_references()
            except Exception:
                pass
        return False

def _reload_open_references(self):
    try:
        with self.db.connect() as conn:
            conn.row_factory = None
            try:  # REF-SYNC
                conn.execute("UPDATE outbound_loads SET remaining_qty = (SELECT COALESCE(SUM(qty),0) FROM outbound_load_items oli2 WHERE oli2.outbound_load_id=outbound_loads.id) - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED'),0), load_status = CASE WHEN (SELECT COALESCE(SUM(qty),0) FROM outbound_load_items oli2 WHERE oli2.outbound_load_id=outbound_loads.id) - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=outbound_loads.id AND wi.issue_status!='CANCELLED'),0) > 0 THEN 'OPEN' ELSE 'COMPLETE' END WHERE is_active=1")  # REF-SYNC
            except Exception:  # REF-SYNC
                pass  # REF-SYNC
            rows = conn.execute(
                "SELECT id, reference_no, customer_id, driver_id, total_load_qty, remaining_qty, "
                "waybill_no, source_location, destination_location FROM outbound_loads "
                "WHERE is_active = 1 AND remaining_qty > 0 "
                "AND wi.issue_status<>'CANCELLED')) ORDER BY id DESC").fetchall()
        self.open_references = [
            {'id': r[0], 'reference_no': r[1] or 'نامشخص', 'customer_id': r[2], 'driver_id': r[3],
             'total_load_qty': r[4] or 0, 'remaining_qty': r[5] or 0, 'waybill_no': r[6] or '',
             'source_location': r[7] or '', 'destination_location': r[8] or ''} for r in rows]
    except Exception:
        pass
    self._refresh_reference_combo()

def apply():
    from app.ui.issue_manager_window import IssueManagerWindow as W
    if getattr(W, '_combo_refresh_patched', False):
        return
    W._combo_refresh_patched = True
    W._reload_open_references = _reload_open_references

    orig_build = W._build_ui
    def _build_ui(self):
        orig_build(self)
        try:
            self._ref_combo_filter = _RefComboFilter(self)
            self.reference_selector_combo.installEventFilter(self._ref_combo_filter)
            self.reference_selector_combo.setToolTip('با هر کلیک، لیست مرجع‌ها تازه‌سازی می‌شود؛ ابتدا انبار را انتخاب کنید.')
        except Exception as e:
            print('[combo-refresh] filter error:', e)
    W._build_ui = _build_ui

    orig_clear = W.clear_form
    def clear_form(self):
        prev_w = None
        try:
            prev_w = self.warehouse_combo.currentData()
        except Exception:
            pass
        orig_clear(self)
        if prev_w:
            try:
                self.warehouse_combo.blockSignals(True)
                idx = self.warehouse_combo.findData(prev_w)
                if idx >= 0:
                    self.warehouse_combo.setCurrentIndex(idx)
                self.warehouse_combo.blockSignals(False)
                if hasattr(self, 'warehouse_msg_lbl'):
                    self.warehouse_msg_lbl.hide()
                self._refresh_reference_combo()
                self._refresh_pallet_combos()
            except Exception:
                pass
    W.clear_form = clear_form
    print('[combo-refresh] applied ✔')
