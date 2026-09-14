# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QComboBox, QLineEdit, QDateEdit, QTableWidget, QTableWidgetItem, QTabWidget, QWidget,
    QMessageBox, QAbstractItemView, QHeaderView, QFormLayout)
from app.core.jalali import jalali_date_display_from_iso, today_iso_date
from app.repositories.checkbook_repository import CheckbookRepository

STATUS_FA = {'IN_HAND': 'در دست', 'SPENT': 'خرج‌شده', 'COLLECTED': 'وصول‌شده', 'BOUNCED': 'برگشتی'}
MOVE_FA = {'RECEIVE': 'دریافت', 'SPEND': 'خرج/انتقال', 'COLLECT': 'وصول', 'BOUNCE': 'برگشت'}


class SpendDialog(QDialog):
    """دیالوگ خرج/انتقال چک - اطلاعات چک خودکار و فقط‌خواندنی"""
    def __init__(self, db, repo, check, parent=None):
        super().__init__(parent)
        self.db = db; self.repo = repo; self.check = check
        self.result_data = None
        self.setWindowTitle('خرج / انتقال چک')
        self.resize(520, 560)
        self.setLayoutDirection(Qt.RightToLeft)
        root = QVBoxLayout(self)
        g = QGroupBox('چک انتخاب‌شده (پر شده خودکار)')
        fg = QFormLayout(g)
        fg.addRow('شماره چک:', QLabel(str(check.get('check_no') or '-')))
        fg.addRow('صادرکننده:', QLabel(repo.person_name(check.get('issuer_person_id')) or '-'))
        fg.addRow('بانک:', QLabel(check.get('bank_name') or '-'))
        fg.addRow('مبلغ:', QLabel(f"{int(check.get('amount') or 0):,} ریال"))
        fg.addRow('سررسید:', QLabel(jalali_date_display_from_iso(check.get('due_date')) if check.get('due_date') else '-'))
        root.addWidget(g)
        f = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem('پشت‌نویسی به شخص', 'ENDORSE')
        self.mode_combo.addItem('سپرده به بانک', 'DEPOSIT')
        self.person_combo = QComboBox()
        self.person_combo.addItem('انتخاب کنید', None)
        for p in repo.list_persons():
            self.person_combo.addItem(p['name'], p['id'])
        self.account_combo = QComboBox()
        self.account_combo.addItem('انتخاب کنید', None)
        try:
            from app.repositories.finance_repository import FinanceRepository
            for a in FinanceRepository(db).list_active_treasury_accounts():
                self.account_combo.addItem(f"{a['code']} | {a['name']}", a['id'])
        except Exception:
            pass
        self.note_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        f.addRow('نوع انتقال:', self.mode_combo)
        f.addRow('گیرنده (پشت‌نویسی):', self.person_combo)
        f.addRow('حساب مقصد (سپرده):', self.account_combo)
        f.addRow('بابت:', self.note_edit)
        f.addRow('توضیحات:', self.desc_edit)
        self.mode_combo.currentIndexChanged.connect(self._sync)
        root.addLayout(f)
        bb = QPushButton('💾 ثبت خرج/انتقال'); bb.clicked.connect(self._accept)
        root.addWidget(bb)
        self._sync()

    def _sync(self):
        dep = self.mode_combo.currentData() == 'DEPOSIT'
        self.account_combo.setVisible(dep)
        self.person_combo.setVisible(not dep)

    def _accept(self):
        note = self.note_edit.text().strip() or 'خرج چک'
        if self.desc_edit.text().strip():
            note += ' | ' + self.desc_edit.text().strip()
        if self.mode_combo.currentData() == 'DEPOSIT':
            if not self.account_combo.currentData():
                QMessageBox.warning(self, 'خرج چک', 'حساب مقصد را انتخاب کنید.'); return
            self.result_data = {'mode': 'DEPOSIT', 'account_id': self.account_combo.currentData(), 'note': note}
        else:
            if not self.person_combo.currentData():
                QMessageBox.warning(self, 'خرج چک', 'گیرنده را انتخاب کنید.'); return
            self.result_data = {'mode': 'ENDORSE', 'person_id': self.person_combo.currentData(),
                                'person_name': self.person_combo.currentText(), 'note': note}
        self.accept()


class CheckbookWindow(QDialog):
    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db; self.user_data = user_data or {}
        self.repo = CheckbookRepository(db)
        permissions = set((user_data or {}).get('permissions', []) or [])
        self.can_manage = 'finance.manage' in permissions or (user_data or {}).get('role_code') == 'ADMIN'
        self.setWindowTitle('مدیریت چک‌های دریافتنی')
        self.resize(1100, 700); self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui(); self.refresh(); self._update_jalali()
        self._show_due_alerts()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_list(), '🏦 چک‌های من (در دست)')
        self.tabs.addTab(self._tab_register(), '➕ ثبت چک دریافتی')
        self.tabs.addTab(self._tab_trace(), ' کارت چک (ردپا)')
        root.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        close_btn = QPushButton('بستن'); close_btn.clicked.connect(self.accept)
        bl = QHBoxLayout(); bl.addStretch(); bl.addWidget(close_btn); root.addLayout(bl)

    def _tab_list(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.total_lbl = QLabel(''); l.addWidget(self.total_lbl)
        self.checks_table = QTableWidget(0, 8)
        self.checks_table.setHorizontalHeaderLabels(['شناسه','شماره چک','صادرکننده','بانک','مبلغ','سررسید','وضعیت','عملیات'])
        self.checks_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.checks_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.checks_table.verticalHeader().setVisible(False)
        self.checks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.checks_table.itemSelectionChanged.connect(self._load_trace)
        l.addWidget(self.checks_table)
        bar = QHBoxLayout()
        self.spend_btn = QPushButton('💸 خرج/انتقال'); self.spend_btn.clicked.connect(self._spend)
        collect_btn = QPushButton('✅ وصول (فقط در امور مالی)'); collect_btn.setEnabled(False); collect_btn.setToolTip('وصول چک فقط در امور مالی انجام می‌شود')
        bounce_btn = QPushButton('⛔ برگشت (فقط در امور مالی)'); bounce_btn.setEnabled(False); bounce_btn.setToolTip('برگشت چک فقط در امور مالی انجام می‌شود')
        import_btn = QPushButton('📥 وارد کردن چک‌های دریافتنی از مالی')
        import_btn.clicked.connect(self._import_from_finance)
        bar.addWidget(import_btn)

        edit_btn = QPushButton('✏️ ویرایش چک'); edit_btn.clicked.connect(self._edit_check)
        fin_btn = QPushButton('📄 ثبت سند مالی (به‌زودی)')
        fin_btn.setEnabled(False)
        fin_btn.setToolTip('ثبت سند مالی خودکار در نسخهٔ آینده فعال می‌شود')
        bar.addWidget(self.spend_btn); bar.addWidget(edit_btn); bar.addWidget(fin_btn); bar.addWidget(collect_btn); bar.addWidget(bounce_btn); bar.addStretch()
        if not self.can_manage:
            self.spend_btn.setEnabled(False); self.spend_btn.setToolTip('خرج/انتقال فقط با مجوز مدیر مالی')
        l.addLayout(bar)
        return w

    def _tab_register(self):
        w = QWidget(); l = QVBoxLayout(w)
        g = QGroupBox('مشخصات چک دریافتی'); f = QFormLayout(g)
        self.issuer_combo = QComboBox()
        self.check_no_edit = QLineEdit(); self.sayyad_edit = QLineEdit()
        self.bank_edit = QComboBox(); self.bank_edit.setEditable(True)
        self.bank_edit.addItems(['بانک سپه', 'بانک شهر', 'بانک ملی', 'بانک ملت', 'بانک صادرات', 'بانک تجارت', 'بانک رفاه', 'بانک پارسیان', 'بانک پاسارگاد', 'بانک سامان', 'بانک اقتصاد نوین', 'بانک آینده', 'بانک کشاورزی', 'بانک انصار'])
        self.branch_edit = QLineEdit()
        self.amount_edit = QLineEdit()
        self.amount_edit.textChanged.connect(self._format_amount)
        self.amount_words_lbl = QLabel('-')
        self.amount_words_lbl.setStyleSheet('color:#64748b;font-size:12px;')
        self.spend_dir_combo = QComboBox()
        self.spend_dir_combo.addItem('نگهداری تا سررسید', 'HOLD')
        self.spend_dir_combo.addItem('سپرده به بانک', 'DEPOSIT')
        self.spend_dir_combo.addItem('پشت‌نویسی به شخص', 'ENDORSE_OUT')
        self.desc_edit = QLineEdit()
        self.receive_type_combo = QComboBox()
        self.receive_type_combo.addItem('مستقیم از صادرکننده', 'DIRECT')
        self.receive_type_combo.addItem('پشت‌نویسی‌شده (انتقالی)', 'ENDORSED')
        self.endorser_combo = QComboBox()
        self.issue_date = QDateEdit(QDate.currentDate()); self.issue_date.setDisplayFormat('yyyy-MM-dd')
        self.due_date = QDateEdit(QDate.currentDate()); self.due_date.setDisplayFormat('yyyy-MM-dd')
        self.issue_jalali_lbl = QLabel('-'); self.issue_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self.due_jalali_lbl = QLabel('-'); self.due_jalali_lbl.setStyleSheet('color:#f59e0b;font-weight:bold;')
        self._jalali_pairs = [(self.issue_date, self.issue_jalali_lbl), (self.due_date, self.due_jalali_lbl)]
        self.issue_date.dateChanged.connect(self._update_jalali)
        self.due_date.dateChanged.connect(self._update_jalali)
        f.addRow('صادرکننده (از چه کسی):', self.issuer_combo)
        self.issuer_combo.currentIndexChanged.connect(self._on_issuer_changed)        
        f.addRow('نوع دریافت:', self.receive_type_combo)
        f.addRow('پشت‌نویسی‌کننده (انتقال‌دهنده):', self.endorser_combo)
        f.addRow('شماره چک:', self.check_no_edit); f.addRow('شماره صیاد:', self.sayyad_edit)
        f.addRow('جهت خرج (پیش‌بینی):', self.spend_dir_combo)
        f.addRow('بانک:', self.bank_edit); f.addRow('شعبه:', self.branch_edit)
        f.addRow('مبلغ (ریال):', self.amount_edit)
        f.addRow('', self.amount_words_lbl)
        f.addRow('تاریخ صدور:', self.issue_date); f.addRow('', self.issue_jalali_lbl)
        f.addRow('تاریخ سررسید:', self.due_date); f.addRow('', self.due_jalali_lbl)
        f.addRow('توضیحات:', self.desc_edit)
        l.addWidget(g)
        save_btn = QPushButton('💾 ثبت چک'); save_btn.clicked.connect(self._register)
        l.addWidget(save_btn); l.addStretch()
        return w

    def _tab_trace(self):
        w = QWidget(); l = QVBoxLayout(w)
        self.trace_lbl = QLabel('یک چک از لیست انتخاب کنید'); l.addWidget(self.trace_lbl)
        self.trace_table = QTableWidget(0, 5)
        self.trace_table.setHorizontalHeaderLabels(['تاریخ','نوع','از','به','توضیح'])
        self.trace_table.verticalHeader().setVisible(False)
        self.trace_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l.addWidget(self.trace_table)
        return w


    def _on_tab_changed(self, idx):
        if idx == 2:
            self._load_trace()

    def _import_from_finance(self):
        from app.repositories.finance_repository import FinanceRepository
        fr = FinanceRepository(self.db)
        rows = fr.list_check_entries(search_text='', status_filter='PENDING', due_scope='ALL')
        persons = {p['name']: p['id'] for p in self.repo.list_persons()}
        added = 0
        for r in rows:
            if (r.get('direction') or '').upper() != 'RECEIVABLE':
                continue
            issuer_id = persons.get((r.get('counterparty_name') or '').strip())
            with self.db.connect() as conn:
                exists = conn.execute(
                    "SELECT id, issuer_person_id FROM checkbook_checks "
                    "WHERE source_type='FINANCE' AND source_id=?", (r['id'],)).fetchone()
            if exists:
                # تعمیر صادرکنندهٔ خالیِ چک‌های قبلاً واردشده
                if issuer_id and not exists['issuer_person_id']:
                    with self.db.connect() as conn:
                        conn.execute("UPDATE checkbook_checks SET issuer_person_id=? WHERE id=?",
                                     (issuer_id, exists['id'])); conn.commit()
                continue
            self.repo.create_check({
                'check_no': r.get('check_no'), 'sayyad_no': r.get('check_serial'),
                'bank_name': r.get('check_bank_name'), 'branch': r.get('check_branch_name'),
                'amount': int(r.get('amount') or 0),
                'issue_date': None, 'due_date': r.get('due_date'),
                'issuer_person_id': issuer_id,
                'source_type': 'FINANCE', 'source_id': r['id'],
                'note': 'وارد شده از اسناد مالی',
            }, self.user_data.get('id', 1))
            added += 1
        if added:
            QMessageBox.information(self, 'وارد کردن', f'{added} چک دریافتنی به «چک‌های من» اضافه شد.')
        else:
            QMessageBox.information(self, 'وارد کردن', 'مورد جدیدی یافت نشد؛ صادرکننده‌های خالی هم تعمیر شدند.')
        self.refresh()   
        
    def _on_issuer_changed(self):
        pid = self.issuer_combo.currentData()
        if not pid:
            return
        with self.db.connect() as conn:
            r = conn.execute(
                "SELECT bank_name, branch FROM checkbook_checks "
                "WHERE issuer_person_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        if r:
            if not self.bank_edit.currentText():
                self.bank_edit.setCurrentText(r['bank_name'] or '')
            if not self.branch_edit.text():
                self.branch_edit.setText(r['branch'] or '')        

    # ── منطق ──

    def _update_jalali(self):
        from app.core.jalali import jalali_date_display_from_iso
        for ed, lb in getattr(self, '_jalali_pairs', []):
            lb.setText(jalali_date_display_from_iso(ed.date().toString('yyyy-MM-dd')))

    def refresh(self):
        self.issuer_combo.clear(); self.issuer_combo.addItem('انتخاب کنید', None)
        self.endorser_combo.clear(); self.endorser_combo.addItem('انتخاب کنید', None)
        for p in self.repo.list_persons():
            self.issuer_combo.addItem(p['name'], p['id'])
            self.endorser_combo.addItem(p['name'], p['id'])
        rows = self.repo.list_checks()
        self.checks_table.setRowCount(len(rows))
        onhand = 0
        for i, r in enumerate(rows):
            if r['status'] == 'IN_HAND': onhand += int(r['amount'] or 0)
            moves = self.repo.movements(r['id'])
            if moves:
                lm = moves[-1]
                ops = MOVE_FA.get(lm['move_type'], lm['move_type'])
                to_name = self.repo.person_name(lm['to_person_id']) if lm.get('to_person_id') else ''
                ops = ops + (' به ' + to_name if to_name else '')
            else:
                ops = 'دریافت'
            vals = [str(r['id']), r['check_no'] or '-', self.repo.person_name(r['issuer_person_id']),
                    r['bank_name'] or '-', f"{int(r['amount'] or 0):,}",
                    jalali_date_display_from_iso(r['due_date']) if r['due_date'] else '-',
                    STATUS_FA.get(r['status'], r['status']), ops]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.checks_table.setItem(i, c, it)
        self.total_lbl.setText(f'جمع چک‌های در دست: {onhand:,} ریال  (جزء صندوق و چک‌های شما)')

    def _show_due_alerts(self):
        from PyQt5.QtWidgets import QMessageBox
        today = today_iso_date()
        overdue, due_today = [], []
        for r in self.repo.list_checks(status='IN_HAND'):
            d = r.get('due_date')
            if not d:
                continue
            if d < today:
                overdue.append(r)
            elif d == today:
                due_today.append(r)
        if not overdue and not due_today:
            return
        lines = []
        if overdue:
            lines.append('⛔ چک‌های معوق (سررسید گذشته):')
            for r in overdue[:10]:
                lines.append(f"  • {r['check_no'] or '-'} | {int(r['amount'] or 0):,} ریال | سررسید: {jalali_date_display_from_iso(r['due_date'])}")
        if due_today:
            lines.append('⏰ چک‌های با سررسید امروز:')
            for r in due_today[:10]:
                lines.append(f"  • {r['check_no'] or '-'} | {int(r['amount'] or 0):,} ریال")
        QMessageBox.warning(self, 'هشدار سررسید چک‌ها', '\n'.join(lines))        

    def _selected_id(self):
        r = self.checks_table.currentRow()
        if r < 0: return None
        return int(self.checks_table.item(r, 0).text())

    def _load_trace(self):
        cid = self._selected_id()
        if not cid: return
        chk = self.repo.get_check(cid)
        self.trace_lbl.setText(f"چک {chk['check_no']} | {int(chk['amount'] or 0):,} ریال | وضعیت: {STATUS_FA.get(chk['status'])}")
        rows = self.repo.movements(cid)
        if not rows:
            rows = [{
                'move_date': chk.get('created_at') or chk.get('issue_date') or chk.get('due_date'),
                'move_type': 'RECEIVE',
                'from_person_id': chk.get('issuer_person_id'),
                'to_person_id': None,
                'note': 'ثبت اولیه چک',
            }]
        self.trace_table.setRowCount(len(rows))
        for i, m in enumerate(rows):
            vals = [jalali_date_display_from_iso(m['move_date']) if m['move_date'] else '-',
                    MOVE_FA.get(m['move_type'], m['move_type']),
                    self.repo.person_name(m['from_person_id']) if m['from_person_id'] else '—',
                    self.repo.person_name(m['to_person_id']) if m['to_person_id'] else '—',
                    m['note'] or '-']
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v); self.trace_table.setItem(i, c, it)

    def _format_amount(self, txt):
        digits = ''.join(ch for ch in txt if ch.isdigit())
        formatted = f"{int(digits):,}" if digits else ''
        if formatted != txt:
            self.amount_edit.blockSignals(True)
            self.amount_edit.setText(formatted)
            self.amount_edit.blockSignals(False)
        if digits:
            self.amount_words_lbl.setText(self._amount_to_words_fa(int(digits)) + ' ریال')
        else:
            self.amount_words_lbl.setText('-')

    def _amount_to_words_fa(self, num):
        if num == 0:
            return 'صفر'
        yekan = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده',
                 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
        dahgan = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
        sadgan = ['', 'یکصد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']
        scale = ['', 'هزار', 'میلیون', 'میلیارد', 'هزار میلیارد']
        def three(x):
            parts = []
            sd, x = divmod(x, 100)
            dg, y = divmod(x, 10)
            if sd:
                parts.append(sadgan[sd])
            if dg == 1:
                parts.append(yekan[10 + y])
            else:
                if dg:
                    parts.append(dahgan[dg])
                if y:
                    parts.append(yekan[y])
            return ' و '.join(parts)
        groups, i = [], 0
        while num:
            num, g = divmod(num, 1000)
            if g:
                groups.append(three(g) + (' ' + scale[i] if scale[i] else ''))
            i += 1
        return ' و '.join(reversed(groups))

    def _register(self):
        if not self.issuer_combo.currentData():
            QMessageBox.warning(self, 'ثبت چک', 'صادرکننده را انتخاب کنید.'); return
        amt = int(''.join(ch for ch in self.amount_edit.text() if ch.isdigit()) or 0)
        if amt <= 0:
            QMessageBox.warning(self, 'ثبت چک', 'مبلغ معتبر وارد کنید.'); return
        self.repo.create_check({
            'check_no': self.check_no_edit.text(), 'sayyad_no': self.sayyad_edit.text(),
            'bank_name': self.bank_edit.currentText(), 'branch': self.branch_edit.text(),
            'amount': amt, 'issue_date': self.issue_date.date().toString('yyyy-MM-dd'),
            'due_date': self.due_date.date().toString('yyyy-MM-dd'),
            'issuer_person_id': self.issuer_combo.currentData(),
            'source_type': 'FREE', 'source_id': None,
            'note': (('دریافت به‌صورت پشت‌نویسی از ' + (self.endorser_combo.currentText() or '-')) if self.receive_type_combo.currentData() == 'ENDORSED' else 'دریافت چک')
                    + ' | جهت: ' + self.spend_dir_combo.currentText()
                    + ((' | ' + self.desc_edit.text().strip()) if self.desc_edit.text().strip() else ''),
        }, self.user_data.get('id', 1))
        QMessageBox.information(self, 'ثبت چک', 'چک با موفقیت ثبت و به «چک‌های من» اضافه شد.')
        self.refresh()

    def _spend(self):
        if not getattr(self, 'can_manage', True):
            QMessageBox.warning(self, 'خرج چک', 'خرج/انتقال فقط با مجوز مدیر مالی ممکن است.')
            return
        cid = self._selected_id()
        if not cid:
            QMessageBox.information(self, 'خرج چک', 'ابتدا یک چک از جدول انتخاب کنید.')
            return
        chk = self.repo.get_check(cid)
        if chk.get('status') != 'IN_HAND':
            QMessageBox.warning(self, 'خرج چک', 'فقط چک «در دست» قابل خرج/انتقال است.')
            return
        dlg = SpendDialog(self.db, self.repo, chk, self)
        if dlg.exec_() != QDialog.Accepted or not dlg.result_data:
            return
        res = dlg.result_data
        if res['mode'] == 'DEPOSIT':
            self.repo.spend_check(cid, None, 'SETTLE', res['account_id'], 'سپرده به بانک: ' + res['note'], self.user_data.get('id', 1))
            msg = 'چک به حساب بانکی سپرده شد.'
        else:
            self.repo.spend_check(cid, res['person_id'], 'SETTLE', None, 'پشت‌نویسی به ' + res['person_name'] + ': ' + res['note'], self.user_data.get('id', 1))
            msg = 'چک به «' + res['person_name'] + '» پشت‌نویسی شد.'
        QMessageBox.information(self, 'خرج چک', msg + chr(10) + 'وضعیت: خرج‌شده | در کارت چک (ردپا) قابل ردیابی است.')
        self.refresh()

    def _open_finance_for_doc(self):
        cid = self._selected_id()
        if not cid:
            QMessageBox.information(self, 'سند مالی', 'ابتدا یک چک انتخاب کنید.')
            return
        chk = self.repo.get_check(cid)
        if chk.get('status') != 'SPENT':
            QMessageBox.information(self, 'سند مالی', 'سند مالی فقط برای چک «خرج‌شده» ثبت می‌شود.')
            return
        from app.ui.finance_window import FinanceWindow
        QMessageBox.information(self, 'سند مالی',
            'اکنون امور مالی باز می‌شود؛ سند پرداخت با روش «چک» ثبت کنید.' + chr(10) + 'شماره چک: ' + (chk.get('check_no') or '-'))
        w = FinanceWindow(self.db, self.user_data)
        w.exec_()
        self.refresh()

    def _edit_check(self):
        from PyQt5.QtWidgets import QDialogButtonBox
        cid = self._selected_id()
        if not cid:
            QMessageBox.information(self, 'ویرایش', 'ابتدا یک چک از جدول انتخاب کنید.')
            return
        chk = self.repo.get_check(cid)
        dlg = QDialog(self)
        dlg.setWindowTitle('ویرایش چک')
        dlg.setLayoutDirection(Qt.RightToLeft)
        f = QFormLayout(dlg)
        bank_e = QLineEdit(chk.get('bank_name') or '')
        branch_e = QLineEdit(chk.get('branch') or '')
        checkno_e = QLineEdit(chk.get('check_no') or '')
        amount_e = QLineEdit(str(int(chk.get('amount') or 0)))
        due_e = QDateEdit()
        due_e.setDisplayFormat('yyyy-MM-dd')
        due_e.setCalendarPopup(True)
        if chk.get('due_date'):
            due_e.setDate(QDate.fromString(chk['due_date'], 'yyyy-MM-dd'))
        f.addRow('بانک:', bank_e)
        f.addRow('شعبه:', branch_e)
        f.addRow('شماره چک:', checkno_e)
        f.addRow('مبلغ (ریال):', amount_e)
        f.addRow('تاریخ سررسید:', due_e)
        status_combo = QComboBox()
        for k, v in STATUS_FA.items():
            status_combo.addItem(v, k)
        status_combo.setCurrentText(STATUS_FA.get(chk.get('status'), 'در دست'))
        f.addRow('وضعیت (اصلاح):', status_combo)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec_() != QDialog.Accepted:
            return
        amt = int(''.join(ch for ch in amount_e.text() if ch.isdigit()) or 0)
        with self.db.connect() as conn:
            conn.execute("UPDATE checkbook_checks SET bank_name=?, branch=?, check_no=?, amount=?, due_date=?, status=? WHERE id=?",
                         (bank_e.text().strip(), branch_e.text().strip(), checkno_e.text().strip(),
                          amt, due_e.date().toString('yyyy-MM-dd'), status_combo.currentData(), cid))
            conn.commit()
        QMessageBox.information(self, 'ویرایش', 'چک با موفقیت اصلاح شد.')
        self.refresh()

    def _collect(self):
        cid = self._selected_id()
        if not cid:
            return
        chk = self.repo.get_check(cid)
        due = chk.get('due_date')
        today = today_iso_date()
        if due and due > today:
            ans = QMessageBox.question(
                self, 'وصول زودتر از سررسید',
                f'سررسید این چک {jalali_date_display_from_iso(due)} است و هنوز نرسیده.\n'
                'آیا با این حال وصول می‌کنید؟',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
        self.repo.collect_check(cid, 'وصول چک', self.user_data.get('id', 1))
        self.refresh()

    def _bounce(self):
        cid = self._selected_id()
        if not cid: return
        self.repo.bounce_check(cid, 'برگشت چک', self.user_data.get('id', 1))
        self.refresh()