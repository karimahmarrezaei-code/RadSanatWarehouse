# -*- coding: utf-8 -*-
# issue_wh_patch v3 - پچ زمان‌اجرا (مصون از بازنویسی ادیتور)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (QTableWidgetItem, QMessageBox, QComboBox, QSpinBox,
                             QLabel, QHBoxLayout, QFrame, QLineEdit)
from app.core.jalali import jalali_date_display_from_iso

def _avg_price_for_warehouse_ext(self, pallet_id, warehouse_id):
    """میانگین: اول کاردکس انبار، بعد افتتاحیه، بعد قیمت پایه پالت"""
    try:
        with self.db.connect() as conn:
            conn.row_factory = None
            if warehouse_id:
                r = conn.execute(
                    "SELECT COALESCE(SUM(qty_in*unit_price),0)/COALESCE(SUM(qty_in),0) "
                    "FROM inventory_transactions WHERE pallet_id=? AND warehouse_id=? "
                    "AND qty_in>0 AND unit_price>0 AND reference_type<>'TRANSFER'",
                    (pallet_id, warehouse_id)).fetchone()
                if r and r[0]:
                    return int(r[0])
            r2 = conn.execute(
                "SELECT COALESCE(SUM(qty*unit_price),0)/COALESCE(SUM(qty),0) "
                "FROM opening_inventory_items WHERE pallet_id=? AND qty>0 AND unit_price>0",
                (pallet_id,)).fetchone()
            if r2 and r2[0]:
                return int(r2[0])
            try:
                r3 = conn.execute("SELECT price FROM pallets WHERE id=?", (pallet_id,)).fetchone()
                if r3 and r3[0]:
                    return int(r3[0])
            except Exception:
                pass
            return int(self.avg_pallet_prices.get(pallet_id, 0) or 0)
    except Exception:
        return int(self.avg_pallet_prices.get(pallet_id, 0) or 0)

def _infer_reference_warehouse(self, reference_id):
    try:
        with self.db.connect() as conn:
            conn.row_factory = None
            ol = conn.execute("SELECT customer_id FROM outbound_loads WHERE id=?", (reference_id,)).fetchone()
            if ol:
                items = conn.execute("SELECT pallet_id, SUM(qty) FROM outbound_load_items WHERE outbound_load_id=? GROUP BY pallet_id ORDER BY pallet_id", (reference_id,)).fetchall()
                if items:
                    sig = '|'.join('{}:{}'.format(a, int(b or 0)) for a, b in items)
                    pros = conn.execute("SELECT id, warehouse_id FROM proforma_invoices WHERE status='CONVERTED' AND COALESCE(customer_id,0)=COALESCE(?,0) ORDER BY id DESC", (ol[0],)).fetchall()
                    for pid, pwh in pros:
                        if not pwh:
                            continue
                        pitems = conn.execute("SELECT pallet_id, SUM(quantity) FROM proforma_invoice_items WHERE proforma_id=? GROUP BY pallet_id ORDER BY pallet_id", (pid,)).fetchall()
                        if '|'.join('{}:{}'.format(a, int(b or 0)) for a, b in pitems) == sig:
                            return int(pwh)
            r = conn.execute("SELECT id FROM warehouses WHERE is_active=1 ORDER BY code LIMIT 1").fetchone()
            return int(r[0]) if r else None
    except Exception:
        return None

def _reference_remaining_qty_map(self, exclude_reference_id=None):
    res = {}
    try:
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute("SELECT oli.pallet_id, SUM(oli.qty) - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=oli.outbound_load_id AND wii.pallet_id=oli.pallet_id AND wi.issue_status!='CANCELLED'),0) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE ol.is_active=1 AND COALESCE(ol.remaining_qty,0)>0 AND ol.id!=? GROUP BY oli.outbound_load_id, oli.pallet_id", (exclude_reference_id or 0,)).fetchall()
            for pid, rem in rows:
                rem = int(rem or 0)
                if rem > 0:
                    res[pid] = res.get(pid, 0) + rem
    except Exception:
        pass
    return res

def _pallet_options_for_warehouse(self):
    wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
    ref_id = self.reference_selector_combo.currentData() if hasattr(self, 'reference_selector_combo') else None
    committed = self._committed_qty_map(ref_id) if wid else {}
    result = []
    for p in self._pallet_options():
        in_allowed = self.allowed_pallet_ids is not None and p['id'] in self.allowed_pallet_ids
        phys = self._stock_for_warehouse(p['id'], wid) if wid else self.pallet_stock.get(p['id'], 0)
        s = int(phys) - int(committed.get(p['id'], 0)) if wid else int(phys)
        if (not wid) or in_allowed or s > 0:
            a = self._avg_price_for_warehouse(p['id'], wid) or int(self.avg_pallet_prices.get(p['id'], 0) or 0)
            result.append((p, s, a))
    return result

def _refresh_reference_combo(self):
    wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
    cust_map = {}
    for c in self.customers:
        cid = c.get('id')
        if cid:
            cust_map[cid] = "{} {}".format(c.get('first_name', ''), c.get('last_name', '')).strip()
    self.reference_selector_combo.blockSignals(True)
    cur = self.reference_selector_combo.currentData()
    self.reference_selector_combo.clear()
    self.reference_selector_combo.addItem('مرجع خروج جدید', None)
    if not wid:
        self.reference_selector_combo.blockSignals(False)
        return
    try:
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute("SELECT ol.id, ol.reference_no, ol.customer_id, COALESCE(ol.total_load_qty,0), COALESCE((SELECT SUM(COALESCE(wi.delivered_qty,0)) FROM warehouse_issues wi WHERE wi.outbound_load_id=ol.id AND wi.issue_status!='CANCELLED'),0), (SELECT COUNT(*) FROM warehouse_issues wi WHERE wi.outbound_load_id=ol.id AND wi.issue_status!='CANCELLED'), ol.warehouse_id FROM outbound_loads ol WHERE ol.is_active=1 ORDER BY ol.id DESC").fetchall()
        for row in rows:
            ref_id, ref_no, cust_id = row[0], row[1] or 'نامشخص', row[2]
            remaining = max(int(row[3] or 0) - int(row[4] or 0), 0)
            if int(row[5] or 0) > 0 and remaining <= 0:
                continue
            ol_wh = row[6]
            if not ol_wh:
                ol_wh = self._infer_reference_warehouse(ref_id)
            if ol_wh and int(ol_wh) != int(wid):
                continue
            cust_name = cust_map.get(cust_id, '-') if cust_id else '-'
            self.reference_selector_combo.addItem("{} | مشتری: {} | مانده: {:,}".format(ref_no, cust_name, remaining), ref_id)
    except Exception as e:
        print('Error loading references:', e)
    if cur:
        idx = self.reference_selector_combo.findData(cur)
        if idx >= 0:
            self.reference_selector_combo.setCurrentIndex(idx)
    self.reference_selector_combo.blockSignals(False)

def _filter_remaining_shipments(self):
    wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
    if not wid:
        QMessageBox.information(self, 'فیلتر', 'ابتدا انبار را انتخاب کنید.')
        return
    try:
        with self.db.connect() as conn:
            conn.row_factory = None
            rows = conn.execute("SELECT ol.id, ol.reference_no, COALESCE(ol.total_load_qty,0), COALESCE((SELECT SUM(COALESCE(wi.delivered_qty,0)) FROM warehouse_issues wi WHERE wi.outbound_load_id=ol.id AND wi.issue_status!='CANCELLED'),0), COALESCE(p.first_name||' '||p.last_name,'-'), COALESCE(d.first_name||' '||d.last_name,'-'), COALESCE(ol.register_date,''), ol.warehouse_id FROM outbound_loads ol LEFT JOIN persons p ON p.id=ol.customer_id LEFT JOIN persons d ON d.id=ol.driver_id WHERE ol.is_active=1 ORDER BY ol.id DESC").fetchall()
        open_rows = []
        for r in rows:
            if (int(r[2] or 0) - int(r[3] or 0)) <= 0:
                continue
            ol_wh = r[7]
            if not ol_wh:
                ol_wh = self._infer_reference_warehouse(r[0])
            if ol_wh and int(ol_wh) != int(wid):
                continue
            open_rows.append(r)
        self.issues_table.setRowCount(len(open_rows))
        for row_idx, r in enumerate(open_rows):
            total = int(r[2] or 0); delivered = int(r[3] or 0)
            vals = [str(r[0]), 'مرجع باز', r[1] or '-', r[4] or '-', r[5] or '-', self._fmt_int(total), self._fmt_int(delivered), self._fmt_int(total - delivered), jalali_date_display_from_iso(r[6]) if r[6] else '-', 'باز', '-']
            for col_idx, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item.setBackground(QBrush(QColor(254, 240, 199)))
                self.issues_table.setItem(row_idx, col_idx, item)
        QMessageBox.information(self, 'فیلتر', 'تعداد {} مرجع دارای بار تحویل‌نشده در انبار انتخابی.'.format(len(open_rows)))
    except Exception as e:
        QMessageBox.critical(self, 'خطا', 'خطا در فیلتر حواله‌های مانده:{}'.format(e))

def _update_remaining_labels(self, row=None):
    try:
        if not hasattr(self, 'rem_qty_value'):
            return
        if row is None:
            row = self.lines_table.currentRow()
        combo = self.lines_table.cellWidget(row, 1) if row >= 0 else None
        spin = self.lines_table.cellWidget(row, 2) if row >= 0 else None
        pid = combo.currentData() if isinstance(combo, QComboBox) else None
        wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
        if not pid or not wid:
            self.rem_qty_value.setText('-')
            self.rem_amt_value.setText('-')
            return
        ref_id = self.reference_selector_combo.currentData() if hasattr(self, 'reference_selector_combo') else None
        avail = self._available_for_warehouse(pid, wid, ref_id)
        entered = spin.value() if isinstance(spin, QSpinBox) else 0
        rem = int(avail) - int(entered)
        avg = self._avg_price_for_warehouse(pid, wid)
        self.rem_qty_value.setText('{:,} عدد'.format(rem))
        self.rem_amt_value.setText('{:,} ریال'.format(rem * avg))
    except Exception:
        pass

def apply_patch():
    try:
        from app.ui.issue_manager_window import IssueManagerWindow as W
    except Exception as e:
        print('[wh-patch] import error:', e)
        return
    if getattr(W, '_wh_patch_applied', False):
        return
    W._wh_patch_applied = True
    W._reserve_qty_map_base = W._reserve_qty_map
    W._infer_reference_warehouse = _infer_reference_warehouse
    W._reference_remaining_qty_map = _reference_remaining_qty_map
    W._avg_price_for_warehouse = _avg_price_for_warehouse_ext
    def _committed(self, exclude_reference_id=None):
        res = dict(self._reserve_qty_map_base())
        for pid, q in self._reference_remaining_qty_map(exclude_reference_id).items():
            res[pid] = res.get(pid, 0) + q
        return res
    W._committed_qty_map = _committed
    def _reserve_committed(self):
        return self._committed_qty_map(self.reference_selector_combo.currentData() if hasattr(self, 'reference_selector_combo') else None)
    W._reserve_qty_map = _reserve_committed
    def _available(self, pallet_id, warehouse_id, exclude_reference_id=None):
        return int(self._stock_for_warehouse(pallet_id, warehouse_id)) - int(self._committed_qty_map(exclude_reference_id).get(pallet_id, 0))
    W._available_for_warehouse = _available
    W._pallet_options_for_warehouse = _pallet_options_for_warehouse
    W._refresh_reference_combo = _refresh_reference_combo
    W._filter_remaining_shipments = _filter_remaining_shipments
    W._update_remaining_labels = _update_remaining_labels

    orig_build_ui = W._build_ui
    def _build_ui(self):
        orig_build_ui(self)
        try:
            tab = self.tabs.widget(1)
            lay = tab.layout()
            bar = QFrame(); bar.setObjectName('Card')
            hl = QHBoxLayout(bar)
            self.rem_qty_lbl = QLabel('تعداد مانده انبار:')
            self.rem_qty_value = QLabel('-')
            self.rem_qty_value.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
            self.rem_amt_lbl = QLabel('مبلغ مانده:')
            self.rem_amt_value = QLabel('-')
            self.rem_amt_value.setStyleSheet('color:#10b981;font-size:16px;font-weight:bold;')
            hl.addWidget(self.rem_qty_lbl); hl.addWidget(self.rem_qty_value)
            hl.addSpacing(24)
            hl.addWidget(self.rem_amt_lbl); hl.addWidget(self.rem_amt_value)
            hl.addStretch()
            lay.insertWidget(1, bar)
        except Exception as e:
            print('[wh-patch] labels ui error:', e)
    W._build_ui = _build_ui

    _orig = W._on_issue_pallet_changed
    def _on_issue_pallet_changed(self, row):
        _orig(self, row)
        try:
            combo = self.lines_table.cellWidget(row, 1)
            spin = self.lines_table.cellWidget(row, 2)
            price_edit = self.lines_table.cellWidget(row, 3)
            pid = combo.currentData() if isinstance(combo, QComboBox) else None
            wid = self.warehouse_combo.currentData() if hasattr(self, 'warehouse_combo') else None
            if pid and wid:
                if spin is not None and hasattr(spin, 'setMaximum'):
                    ref_id = self.reference_selector_combo.currentData() if hasattr(self, 'reference_selector_combo') else None
                    spin.setMaximum(max(self._available_for_warehouse(pid, wid, ref_id), 1))
                if isinstance(price_edit, QLineEdit):
                    avg = self._avg_price_for_warehouse(pid, wid)
                    d = ''.join(ch for ch in (self.issue_pct_edit.text() or '') if ch.isdigit())
                    pct = float(d) if d else 40.0
                    suggested = int(avg * (1 + pct / 100.0))
                    if suggested > 0:
                        price_edit.blockSignals(True)
                        price_edit.setText(self._fmt_int(suggested))
                        price_edit.blockSignals(False)
                    if not d:
                        self.issue_pct_edit.setText('40')
        except Exception:
            pass
        try:
            self._update_remaining_labels(row)
        except Exception:
            pass
    W._on_issue_pallet_changed = _on_issue_pallet_changed

    orig_recalc = W.recalculate_lines
    def recalculate_lines(self):
        orig_recalc(self)
        try:
            self._update_remaining_labels()
        except Exception:
            pass
    W.recalculate_lines = recalculate_lines
    print('[wh-patch] applied ✔ (v3: قیمت میانگین+درصد + لیبل مانده)')
