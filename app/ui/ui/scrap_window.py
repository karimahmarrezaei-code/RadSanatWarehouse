# -*- coding: utf-8 -*-
import os, shutil, tempfile, webbrowser
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QMessageBox, QAbstractItemView,
    QLineEdit, QGroupBox, QFormLayout, QFileDialog)
from app.core.jalali import jalali_date_display_from_iso
from app.core.letterhead import get_filtered_company
from app.repositories.scrap_repository import ScrapRepository

class ScrapWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.repo = ScrapRepository(db)
        self.last_sale_id = None
        self.setWindowTitle('فروش ضایعات (وزنی)')
        self.resize(1100, 760); self.setLayoutDirection(Qt.RightToLeft)
        self._build(); self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        g = QGroupBox('سند فروش ضایعات'); f = QFormLayout(g)
        self.buyer_combo = QComboBox()
        self.date_edit = QDateEdit(QDate.currentDate()); self.date_edit.setDisplayFormat('yyyy-MM-dd')
        self.jalali_lbl = QLabel('-'); self.jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self.date_edit.dateChanged.connect(self._jalali)
        self.vehicle_edit = QLineEdit(); self.vehicle_edit.setPlaceholderText('شماره خودروی حمل')
        self.desc_edit = QLineEdit()
        f.addRow('خریدار:', self.buyer_combo); f.addRow('تاریخ:', self.date_edit)
        f.addRow('شمسی:', self.jalali_lbl); f.addRow('شماره خودرو:', self.vehicle_edit)
        f.addRow('توضیح:', self.desc_edit)
        root.addWidget(g)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(['قلم', 'وزن ناخالص', 'تاره/باسکول', 'وزن خالص', 'قیمت هر کیلو', 'جمع'])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.tbl)

        bar = QHBoxLayout()
        add_btn = QPushButton('➕ ردیف'); add_btn.clicked.connect(self._add_row)
        save_btn = QPushButton('💾 ثبت و اتصال به مالی'); save_btn.setObjectName('PrimaryButton'); save_btn.clicked.connect(self._save)
        self.photo_btn = QPushButton('📷 افزودن عکس (تا ۳)'); self.photo_btn.setEnabled(False); self.photo_btn.clicked.connect(self._photo)
        self.print_btn = QPushButton('🖨️ پیش‌نمایش / چاپ'); self.print_btn.setEnabled(False); self.print_btn.clicked.connect(self._print)
        self.total_lbl = QLabel('جمع: 0 ریال'); self.total_lbl.setStyleSheet('font-weight:bold;color:#047857;')
        bar.addWidget(add_btn); bar.addStretch(); bar.addWidget(self.total_lbl)
        bar.addWidget(save_btn); bar.addWidget(self.photo_btn); bar.addWidget(self.print_btn)
        root.addLayout(bar)

        self.list_tbl = QTableWidget(0, 5)
        self.list_tbl.setHorizontalHeaderLabels(['شماره', 'تاریخ', 'خریدار', 'مبلغ', 'وضعیت'])
        self.list_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_tbl.itemSelectionChanged.connect(self._on_select)
        root.addWidget(self.list_tbl)
        self._add_row()

    def _on_select(self):
        r = self.list_tbl.currentRow()
        if r < 0: return
        self.last_sale_id = int(self.list_tbl.item(r, 0).text().split('-')[-1]) if False else None
        # شناسه از ستون شماره نیست؛ از دادهٔ پنهان استفاده می‌کنیم
        self.last_sale_id = getattr(self, '_row_ids', [None]*self.list_tbl.rowCount())[r]
        self.photo_btn.setEnabled(bool(self.last_sale_id))
        self.print_btn.setEnabled(bool(self.last_sale_id))

    def _jalali(self):
        self.jalali_lbl.setText(jalali_date_display_from_iso(self.date_edit.date().toString('yyyy-MM-dd')))

    def _add_row(self):
        r = self.tbl.rowCount(); self.tbl.insertRow(r)
        cb = QComboBox()
        for p in self.repo.list_products(): cb.addItem(f"{p['code']} | {p['name']}", p['id'])
        self.tbl.setCellWidget(r, 0, cb)
        for c in (1, 2, 4):
            e = QLineEdit(); e.setAlignment(Qt.AlignCenter); e.textChanged.connect(self._recalc)
            self.tbl.setCellWidget(r, c, e)
        for c in (3, 5):
            it = QTableWidgetItem('0'); it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tbl.setItem(r, c, it)

    def _recalc(self):
        total_all = 0
        for r in range(self.tbl.rowCount()):
            g = int(''.join(ch for ch in (self.tbl.cellWidget(r,1).text() or '0') if ch.isdigit()) or 0)
            t = int(''.join(ch for ch in (self.tbl.cellWidget(r,2).text() or '0') if ch.isdigit()) or 0)
            p = int(''.join(ch for ch in (self.tbl.cellWidget(r,4).text() or '0') if ch.isdigit()) or 0)
            net = max(g - t, 0); tot = net * p; total_all += tot
            self.tbl.item(r,3).setText(f"{net:,}"); self.tbl.item(r,5).setText(f"{tot:,}")
        self.total_lbl.setText(f"جمع: {total_all:,} ریال")

    def _save(self):
        items = []
        for r in range(self.tbl.rowCount()):
            cb = self.tbl.cellWidget(r,0)
            g = int(''.join(ch for ch in (self.tbl.cellWidget(r,1).text() or '0') if ch.isdigit()) or 0)
            t = int(''.join(ch for ch in (self.tbl.cellWidget(r,2).text() or '0') if ch.isdigit()) or 0)
            p = int(''.join(ch for ch in (self.tbl.cellWidget(r,4).text() or '0') if ch.isdigit()) or 0)
            if g <= 0 or p <= 0: continue
            items.append({'product_id': cb.currentData(), 'name': cb.currentText(), 'gross': g, 'tare': t, 'net': max(g-t,0), 'price': p, 'total': max(g-t,0)*p})
        if not items:
            QMessageBox.warning(self, 'خطا', 'حداقل یک ردیف با وزن و قیمت وارد کنید.'); return
        if not self.buyer_combo.currentData():
            QMessageBox.warning(self, 'خطا', 'خریدار را انتخاب کنید.'); return
        no, sale_id = self.repo.register_sale(items, self.buyer_combo.currentData(),
            self.date_edit.date().toString('yyyy-MM-dd'), self.desc_edit.text(),
            self.user_data.get('id',1), self.vehicle_edit.text().strip())
        self.last_sale_id = sale_id
        self.photo_btn.setEnabled(True); self.print_btn.setEnabled(True)
        QMessageBox.information(self, 'موفق', f'سند {no} ثبت شد.\nاکنون می‌توانید عکس اضافه و چاپ کنید.')
        self.refresh()

    def _photo(self):
        if not self.last_sale_id: return
        files, _ = QFileDialog.getOpenFileNames(self, 'انتخاب عکس', '', 'Images (*.png *.jpg *.jpeg)')
        existing = len(self.repo.get_sale(self.last_sale_id)[2])
        for fp in files:
            if existing >= 3:
                QMessageBox.information(self, 'عکس', 'حداکثر ۳ عکس مجاز است.'); break
            dst_dir = os.path.join(os.getcwd(), 'attachments', f'scrap_{self.last_sale_id}')
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(fp))
            shutil.copy2(fp, dst)
            self.repo.add_photo(self.last_sale_id, dst)
            existing += 1
        QMessageBox.information(self, 'عکس', 'عکس‌ها پیوست شد.')

    def _print(self):
        if not self.last_sale_id: return
        sale, items, photos = self.repo.get_sale(self.last_sale_id)
        company = get_filtered_company(self.db)
        rows_html = ''
        for i, it in enumerate(items):
            rows_html += f"<tr><td>{i+1}</td><td>{it['name']}</td><td>{int(it['gross_weight']):,}</td><td>{int(it['tare_weight']):,}</td><td>{int(it['net_weight']):,}</td><td>{int(it['unit_price']):,}</td><td>{int(it['total']):,}</td></tr>"
        photos_html = ''
        if photos:
            photos_html = '<h3>تصاویر پیوست:</h3><div style="display:flex;gap:10px;">' +                 ''.join(f'<img src="file:///{p}" style="max-width:200px;border:1px solid #999;"/>' for p in photos) + '</div>'
        html = f"""<html dir='rtl'><head><meta charset='utf-8'><style>
            body{{font-family:Tahoma;padding:20px;}} h1{{text-align:center;font-size:26px;}} h3{{text-align:center;}}
            table{{width:100%;border-collapse:collapse;margin:15px 0;}} th,td{{border:1px solid #999;padding:8px;font-size:12px;text-align:center;}} th{{background:#eee;}}
            .sig{{display:flex;justify-content:space-between;margin-top:60px;}} .sig div{{width:40%;text-align:center;border-top:1px solid #333;padding-top:8px;}}
            .print-btn{{position:fixed;top:20px;left:20px;padding:10px 20px;background:#9333ea;color:#fff;border:none;border-radius:6px;cursor:pointer;}}</style></head><body>
            <button class='print-btn' onclick='window.print()'>چاپ / ذخیره PDF</button>
            <h1>{company.get('company_name','')}</h1><h3>سند فروش ضایعات {sale['sale_no']}</h3>
            <p>تاریخ: {jalali_date_display_from_iso(sale['sale_date'])} | خریدار: {sale['buyer'] or '-'} | شماره خودرو: {sale['vehicle_no'] or '-'}</p>
            <table><tr><th>ردیف</th><th>قلم</th><th>وزن ناخالص</th><th>تاره</th><th>وزن خالص</th><th>قیمت/کیلو</th><th>جمع</th></tr>{rows_html}
            <tr><td colspan='6'>جمع کل (ریال)</td><td>{int(sale['total_amount']):,}</td></tr></table>
            {photos_html}
            <div class='sig'><div>امضاء فروشنده</div><div>امضاء خریدار</div></div>
            </body></html>"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html); t = f.name
        webbrowser.open('file:///' + t)

    def refresh(self):
        self.buyer_combo.clear(); self.buyer_combo.addItem('انتخاب کنید', None)
        for p in self.repo.list_persons(): self.buyer_combo.addItem(p['name'], p['id'])
        rows = self.repo.list_sales()
        self._row_ids = [r['id'] for r in rows]
        self.list_tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r['sale_no'], jalali_date_display_from_iso(r['sale_date']) if r['sale_date'] else '-', r['buyer'] or '-', f"{int(r['total_amount'] or 0):,}", 'باز' if r['status']=='OPEN' else 'تسویه']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); self.list_tbl.setItem(i, c, it)
        self._jalali()
