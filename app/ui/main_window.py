# -*- coding: utf-8 -*-
"""MainWindow - نسخه نهایی با ثبت لاگ بازدید از هر فرم + منوی ادمین"""
from typing import Tuple, Dict, List, Optional

from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtCore import QDate, Qt, QTimer
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QTextBrowser, QVBoxLayout, QWidget, QAction, QSizePolicy, QApplication,
)
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
from app.ui.theme_manager import apply_theme
from app.core.database import DatabaseManager
from app.core.jalali import format_now_for_display
from app.ui.dashboard_charts import (
    build_activity_chart, build_financial_balance_chart,
    build_treasury_balance_chart, build_warehouse_value_chart,
)

# ثبت استاتیک ماژول‌های گزارش برای بسته‌بندی exe
try:
    from app.ui import issue_report_window as _irw  # noqa
    from app.ui import receipt_report_window as _rrw  # noqa
    from app.ui import proforma_report_window as _prw  # noqa
except Exception:
    pass


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str, color: str = "#2563eb") -> None:
        super().__init__()
        self.setObjectName('Card')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet(f"QFrame#Card {{  border:2px solid {color}; border-radius:8px; padding:6px; min-height:64px; }} QLabel#CardValue {{ font-size:26px; font-weight:bold; }}")
        layout = QVBoxLayout(self); layout.setSpacing(2); layout.setContentsMargins(8, 4, 8, 4)
        t = QLabel(title); t.setObjectName('Muted'); t.setAlignment(Qt.AlignCenter); t.setWordWrap(True)
        v = QLabel(value); v.setObjectName("CardValue"); v.setStyleSheet(f"QLabel{{color:{color};font-size:28px;font-weight:bold;background:transparent;border:none;padding:0;}}"); v.setAlignment(Qt.AlignCenter)
        layout.addWidget(t); layout.addWidget(v)


class ChartBrowser(QTextBrowser):
    def __init__(self) -> None:
        super().__init__()
        self.setOpenExternalLinks(False); self.setFrameShape(self.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumHeight(60); self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("QTextBrowser{background-color:transparent;color:#f5f7fa;border:1px solid #d3dce6;border-radius:4px;}")


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager, user_data: dict) -> None:
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.permissions = set(user_data.get('permissions', []))
        self._child_windows = []
        self.dashboard_warehouses: List[Dict] = []
        self.dashboard_persons: List[Dict] = []
        self.setWindowTitle(f'سیستم انبارداری هوشمند - {self._company_name()}')
        self.setLayoutDirection(Qt.RightToLeft)
        self._set_responsive_size()
        self._build_menu()
        self._build_ui()
        self.current_theme = 'dark'  # تم پیش‌فرض
        self._load_dashboard_filters()
        self.refresh_dashboard()
        QTimer.singleShot(300, self._show_about)
        QTimer.singleShot(1000, self._show_due_check_reminder)

    # ---------- لاگ بازدید از فرم‌ها ----------
    def _audit_open(self, title: str) -> None:
        """ثبت «باز شدن فرم» در audit_logs برای پیگیری فعالیت اپراتور"""
        try:
            with self.db.connect() as conn:
                self.db.log_audit(conn, self.user_data.get('id'), 'WINDOW', title, 'OPEN', None, None)
        except Exception:
            pass

    def _set_responsive_size(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(1400, 850); self.setMinimumSize(1024, 680); return
        avail = screen.availableGeometry(); aw, ah = avail.width(), avail.height()
        if ah < 900: wr, hr = 0.94, 0.92
        elif ah < 1200: wr, hr = 0.90, 0.88
        else: wr, hr = 0.85, 0.85
        w = max(1024, min(int(aw * wr), 2560)); h = max(680, min(int(ah * hr), 1500))
        self.resize(w, h); self.setMinimumSize(1024, 680)
        g = self.frameGeometry(); g.moveCenter(avail.center()); self.move(g.topLeft())

    def toggle_theme(self):
        """تغییر بین تم دارک و روشن"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            apply_theme(QApplication.instance(), "dark")
            QMessageBox.information(self, "تم تغییر کرد", "تم دارک فعال شد 🌙")
        else:
            self.current_theme = 'light'
            apply_theme(QApplication.instance(), 'light')
            QMessageBox.information(self, "تم تغییر کرد", "تم روشن فعال شد ☀️")

    def _has_any_permission(self, *codes):
        return self.user_data.get('role_code') == 'ADMIN' or any(c in self.permissions for c in codes)

    def _build_menu(self):
        menubar = self.menuBar(); menubar.setNativeMenuBar(False)

        ops = menubar.addMenu('📋 عملیات')
        io = QMenu('📥 ورودی / خروجی', self)
        a = QAction('📥 رسید انبار (خرید)', self); a.setShortcut('Ctrl+R'); a.triggered.connect(self.open_receipt_manager); io.addAction(a)
        a = QAction('📤 حواله‌های باز (فروش)', self); a.setShortcut('Ctrl+I'); a.triggered.connect(self.open_issue_manager); io.addAction(a)
        io.addSeparator()
        a = QAction('🔄 برگشت کالا', self); a.triggered.connect(self.open_return_manager); io.addAction(a)
        ops.addMenu(io); ops.addSeparator()
        a = QAction('🔧 تولید جعبه', self); a.triggered.connect(self.open_box_production); ops.addAction(a)
        a = QAction('🧾 فروش جعبه', self); a.triggered.connect(self.open_box_sale_form); ops.addAction(a)
        a = QAction('📊 انبارگردانی', self); a.triggered.connect(self.open_stock_take); ops.addAction(a)
        ops.addSeparator()
        a = QAction('📝 پیش‌فاکتور', self); a.triggered.connect(self.open_proforma); ops.addAction(a)
        
        # ✅ اصلاح شده: اضافه کردن گزارش‌ها مستقیماً به منوی عملیات (بدون حلقه و break معیوب)
        ops.addSeparator()
        a = QAction('📤 گزارش خروج کالا (حواله‌ها)', self); a.triggered.connect(self.open_issue_report); ops.addAction(a)
        a = QAction('📥 گزارش ورود کالا (رسیدها)', self); a.triggered.connect(self.open_receipt_report); ops.addAction(a)
        a = QAction('📝 گزارش پیش‌فاکتورها', self); a.triggered.connect(self.open_proforma_report); ops.addAction(a)

        persons = menubar.addMenu('👥 اشخاص')
        persons.addAction('👤 مشتریان'); persons.addAction('🏭 تأمین‌کنندگان'); persons.addSeparator()
        persons.addAction('🚚 رانندگان'); persons.addSeparator()
        a = QAction('👥 همه اشخاص', self); a.triggered.connect(self.open_person_manager); persons.addAction(a)

        wh = menubar.addMenu('🏬 انبار')
        a = QAction('🏗️ تعریف انبارها', self); a.triggered.connect(self.open_warehouse_manager); wh.addAction(a)
        a = QAction('📋 افتتاحیه انبار', self); a.triggered.connect(self.open_opening_inventory); wh.addAction(a)
        wh.addSeparator()
        a = QAction('📦 تعریف پالت‌ها', self); a.triggered.connect(self.open_pallet_manager); wh.addAction(a)
        a = QAction('📏 واحدهای کالا', self); a.triggered.connect(self.open_units_manager); wh.addAction(a)
        a = QAction('🧾 تعریف اقلام مصرفی', self); a.triggered.connect(self.open_consumable_items); wh.addAction(a)
        wh.addSeparator()
        a = QAction('🧰 مصارف مصرفی انبار', self); a.triggered.connect(self.open_consumables); wh.addAction(a)
        a = QAction('📊 گزارش خرید اقلام مصرفی', self); a.triggered.connect(self.open_consumable_report); wh.addAction(a)
        a = QAction('🔄 جابجایی بین انبارها', self); a.triggered.connect(self.open_transfer); wh.addAction(a)

        fin = menubar.addMenu('💰 مالی')
        a = QAction('📄 اسناد مالی', self); a.triggered.connect(self.open_finance_manager); fin.addAction(a)
        fin.addSeparator()
        a = QAction('📒 دفتر کل و معین', self); a.triggered.connect(self.open_general_ledger); fin.addAction(a)
        a = QAction('📊 ترازنامه', self); a.triggered.connect(self.open_balance_sheet); fin.addAction(a) 
        a = QAction('🏦 مغایرت بانکی', self); a.triggered.connect(self.open_bank_reconciliation); fin.addAction(a)               
        a = QAction('🏦 صندوق / بانک', self); a.triggered.connect(self.open_treasury_manager); fin.addAction(a)
        a = QAction('💸 ثبت هزینه', self); a.triggered.connect(self.open_expense_entry); fin.addAction(a)
        a = QAction('💰 مدیریت نقدینگی', self); a.triggered.connect(self.open_cash_transfer); fin.addAction(a)
        a = QAction('🏦 مدیریت حساب‌ها', self); a.triggered.connect(self.open_cash_account_manager); fin.addAction(a)
        a = QAction('📒 دفترچه چک (دریافت/انتقال)', self); a.triggered.connect(self.open_checkbook); fin.addAction(a)
        a = QAction('🪵 فروش ضایعات', self); a.triggered.connect(self.open_scrap_window); fin.addAction(a)
        a = QAction('💧 پیش‌بینی نقدینگی', self); a.triggered.connect(self.open_cashflow); fin.addAction(a)
        a = QAction('🔒 بستن سال مالی', self); a.triggered.connect(self.open_year_end); fin.addAction(a)
        a = QAction('💵 مدیریت پرداختی پرسنل', self); a.triggered.connect(self.open_payroll_manager); fin.addAction(a)
        
        rep = menubar.addMenu('📊 گزارشات')
        fr = QMenu('📈 گزارشات مالی', self)
        a = QAction('سود و زیان', self); a.triggered.connect(self.open_pnl_report); fr.addAction(a)
        a = QAction('📈 سودآوری مشتری/کالا', self); a.triggered.connect(self.open_profitability); fr.addAction(a)
        a = QAction('📊 گزارش ترکیبی (اشخاص / حواله)', self); a.triggered.connect(self.open_combined_report); fr.addAction(a)
        a = QAction('🏆 طرف‌های حساب برتر', self); a.triggered.connect(self.open_top_parties); fr.addAction(a)
        a = QAction('⚖️ مغایرت انبار و مالی', self); a.triggered.connect(self.open_inv_fin_recon); fr.addAction(a)
        a = QAction('💼 خروجی اکسل کامل', self); a.triggered.connect(self.open_full_excel_export); fr.addAction(a)
        a = QAction('📅 سن بدهی‌ها', self); a.triggered.connect(self.open_aging_report); fr.addAction(a)
        rep.addMenu(fr); rep.addSeparator()
        wr = QMenu('🏭 گزارشات انبار', self)
        a = QAction('📦 اقلام راکد', self); a.triggered.connect(self.open_dead_stock); wr.addAction(a)
        a = QAction('🔄 گزارش برگشت کالا', self); a.triggered.connect(self.open_return_report); wr.addAction(a)
        a = QAction('📉 گزارش هزینه‌ها', self); a.triggered.connect(self.open_expense_report); wr.addAction(a)
        a = QAction('گردش صندوق/بانک (حسابرسی)', self); a.triggered.connect(self.open_treasury_ledger); wr.addAction(a)
        rep.addMenu(wr); rep.addSeparator()
        a = QAction('📑 همه گزارشات', self); a.setShortcut('Ctrl+G'); a.triggered.connect(self.open_reports_window); rep.addAction(a)
        rep.addSeparator()
        a = QAction('📅 گزارش فعالیت روزانه', self); a.triggered.connect(self.open_daily_activity); rep.addAction(a)

        st = menubar.addMenu('⚙️ تنظیمات')
        a = QAction('🏢 مشخصات شرکت', self); a.triggered.connect(self.open_company_profile); st.addAction(a)
        st.addSeparator()
        a = QAction('🎨 تغییر تم (دارک/روشن)', self); a.triggered.connect(self.toggle_theme); st.addAction(a)
        st.addSeparator()        
        a = QAction('🗓️ دوره‌های مالی (بستن دوره)', self); a.triggered.connect(self.open_fiscal_periods); st.addAction(a)
        st.addSeparator()        
        a = QAction('ℹ️ درباره برنامه', self); a.triggered.connect(self._show_about); st.addAction(a)
        a = QAction('❌ خروج', self); a.setShortcut('Ctrl+Q'); a.triggered.connect(self.close); st.addAction(a)

        um = menubar.addMenu('مدیریت کاربران')
        a = um.addAction('مدیریت کاربران'); a.triggered.connect(self.open_user_manager)
        if self.user_data.get('role_code') == 'ADMIN':
            a = um.addAction('🔐 سطوح دسترسی (چک‌باکس)'); a.triggered.connect(self.open_permission_manager)
            a = um.addAction('📜 گزارش فعالیت کاربران'); a.triggered.connect(self.open_audit_log)
            a = um.addAction('💾 پشتیبان‌گیری / بازگردانی'); a.triggered.connect(self.open_backup_manager)
        about_menu = menubar.addMenu('ℹ️ درباره')
        a = QAction('درباره برنامه', self); a.triggered.connect(self._show_about); about_menu.addAction(a)

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QVBoxLayout(central); main_layout.setContentsMargins(15, 15, 15, 15); main_layout.setSpacing(12)

        header = QFrame(); header.setObjectName('Card'); hl = QVBoxLayout(header); hl.setSpacing(8)
        t = QLabel('داشبورد مدیریتی انبار پالت'); t.setObjectName('Title'); hl.addWidget(t)
        dash_btn = QPushButton('📊 کاردکس و موجودی انبار'); dash_btn.setObjectName('SecondaryButton'); dash_btn.clicked.connect(self.open_reports_window); dash_btn.setMaximumWidth(280)
        self.dash_user_lbl = QLabel('👤 ' + str(self.user_data.get('full_name') or '-'))
        self.dash_user_lbl.setObjectName('Muted')
        hl.addWidget(self.dash_user_lbl)
        self.dash_today_lbl = QLabel('')
        self.dash_today_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;')
        dash_row = QHBoxLayout(); dash_row.addStretch(); dash_row.addWidget(self.dash_today_lbl); dash_row.addWidget(dash_btn); hl.addLayout(dash_row)
        s = QLabel(f"کاربر: {self.user_data['full_name']} | نقش: {self.user_data['role_name']}\n{format_now_for_display()}")
        s.setObjectName('Muted'); hl.addWidget(s)

        pr = QHBoxLayout(); pr.setSpacing(8)
        self.date_from_edit = QDateEdit(QDate.currentDate().addDays(-6)); self.date_from_edit.setCalendarPopup(True); self.date_from_edit.setDisplayFormat('yyyy-MM-dd')
        self.date_to_edit = QDateEdit(QDate.currentDate()); self.date_to_edit.setCalendarPopup(True); self.date_to_edit.setDisplayFormat('yyyy-MM-dd')
        ap = QPushButton('اعمال بازه'); ap.setObjectName('SecondaryButton'); ap.clicked.connect(self.refresh_dashboard)
        rp = QPushButton('7 روز اخیر'); rp.setObjectName('SecondaryButton'); rp.clicked.connect(self.reset_dashboard_period)
        pr.addWidget(QLabel('از تاریخ:')); pr.addWidget(self.date_from_edit)
        self.dash_from_jalali_lbl = QLabel('-'); self.dash_from_jalali_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;'); pr.addWidget(self.dash_from_jalali_lbl)
        pr.addWidget(QLabel('تا تاریخ:')); pr.addWidget(self.date_to_edit)
        self.dash_to_jalali_lbl = QLabel('-'); self.dash_to_jalali_lbl.setStyleSheet('color:#f59e0b;font-size:16px;font-weight:bold;'); pr.addWidget(self.dash_to_jalali_lbl)
        self.date_from_edit.dateChanged.connect(self._update_dash_jalali_labels)
        self.date_to_edit.dateChanged.connect(self._update_dash_jalali_labels)
        self._update_dash_jalali_labels()
        pr.addWidget(ap); pr.addWidget(rp); pr.addStretch(); hl.addLayout(pr)

        fr = QHBoxLayout(); fr.setSpacing(8)
        self.dashboard_warehouse_combo = QComboBox(); self.dashboard_person_combo = QComboBox(); self.dashboard_operation_combo = QComboBox()
        self.dashboard_operation_combo.addItem('همه عملیات', 'ALL'); self.dashboard_operation_combo.addItem('فقط ورود', 'INBOUND'); self.dashboard_operation_combo.addItem('فقط خروج', 'OUTBOUND')
        af = QPushButton('اعمال فیلتر'); af.setObjectName('SecondaryButton'); af.clicked.connect(self.refresh_dashboard)
        cf = QPushButton('پاک کردن فیلترها'); cf.setObjectName('SecondaryButton'); cf.clicked.connect(self.reset_dashboard_filters)
        self.period_info_label = QLabel('بازه و فیلترها برای کارت‌ها و نمودارها اعمال می‌شوند.')
        self.period_info_label.setObjectName('Muted')
        fr.addWidget(QLabel('انبار:')); fr.addWidget(self.dashboard_warehouse_combo); fr.addWidget(QLabel('شخص:')); fr.addWidget(self.dashboard_person_combo)
        fr.addWidget(QLabel('نوع عملیات:')); fr.addWidget(self.dashboard_operation_combo); fr.addWidget(af); fr.addWidget(cf); fr.addStretch(); fr.addWidget(self.period_info_label)
        hl.addLayout(fr)
        main_layout.addWidget(header)

        # نوار سوییچر پنجره‌های باز (بالای داشبورد)
        self.win_bar_frame = QFrame(); self.win_bar_frame.setObjectName('Card')
        wb = QHBoxLayout(self.win_bar_frame); wb.setContentsMargins(10, 6, 10, 6); wb.setSpacing(6)
        wb.addWidget(QLabel('🪟 پنجره‌های باز:'))
        self.win_bar_layout = QHBoxLayout(); self.win_bar_layout.setSpacing(6)
        wb.addLayout(self.win_bar_layout); wb.addStretch()
        self.win_bar_buttons = {}
        main_layout.addWidget(self.win_bar_frame)

        cards_container = QWidget(); self.cards_layout = QGridLayout(cards_container)
        self.cards_layout.setSpacing(10); self.cards_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(cards_container)

        charts = QWidget(); cl = QVBoxLayout(charts); cl.setSpacing(8); cl.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout(); top.setSpacing(8)
        self.finance_chart = ChartBrowser(); self.finance_chart.setMinimumHeight(65); self.finance_chart.setMaximumHeight(78)
        self.warehouse_chart = ChartBrowser(); self.warehouse_chart.setMinimumHeight(65); self.warehouse_chart.setMaximumHeight(78)
        top.addWidget(self.finance_chart, 1); top.addWidget(self.warehouse_chart, 1)
        bot = QHBoxLayout(); bot.setSpacing(8)
        self.treasury_chart = ChartBrowser(); self.treasury_chart.setMinimumHeight(65); self.treasury_chart.setMaximumHeight(78)
        self.activity_chart = ChartBrowser(); self.activity_chart.setMinimumHeight(65); self.activity_chart.setMaximumHeight(78)
        bot.addWidget(self.treasury_chart, 1); bot.addWidget(self.activity_chart, 1)
        cl.addLayout(top); cl.addLayout(bot); main_layout.addWidget(charts)

        ag = QGroupBox('هشدار موجودی کم'); al = QVBoxLayout(ag)
        self.low_stock_list = QListWidget(); self.low_stock_list.setMaximumHeight(70); al.addWidget(self.low_stock_list)
        main_layout.addWidget(ag)

        main_layout.addStretch()

    def _update_dash_jalali_labels(self, *_args):
        try:
            from app.core.jalali import jalali_date_display_from_iso as _j
            self.dash_from_jalali_lbl.setText(_j(self.date_from_edit.date().toString('yyyy-MM-dd')))
            self.dash_to_jalali_lbl.setText(_j(self.date_to_edit.date().toString('yyyy-MM-dd')))
            if hasattr(self, 'dash_today_lbl'):
                self.dash_today_lbl.setText('امروز: ' + _j(QDate.currentDate().toString('yyyy-MM-dd')))
                self.dash_today_lbl.setWordWrap(True)
                self.dash_today_lbl.setMinimumWidth(320)
                self.dash_today_lbl.setMinimumHeight(56)
                self.dash_today_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                self._dash_time_base = self.dash_today_lbl.text()
                def _tick_dash():
                    try:
                        from datetime import datetime as _dt
                        self.dash_today_lbl.setText(self._dash_time_base + '\nساعت: ' + _dt.now().strftime('%H:%M'))
                    except Exception:
                        pass
                _tick_dash()
                self._dash_timer = QTimer(self)
                self._dash_timer.timeout.connect(_tick_dash)
                self._dash_timer.start(30000)
        except Exception:
            pass

    def _show_due_check_reminder(self):
        try:
            from app.ui.check_due_reminder import CheckDueReminderDialog
            d = CheckDueReminderDialog(self.db, self.user_data, parent=self)
            if d.has_due_checks(): d.exec_()
        except Exception:
            pass

    def _load_dashboard_filters(self):
        self.dashboard_warehouses = self.db.list_dashboard_warehouses()
        self.dashboard_persons = self.db.list_dashboard_persons()
        self.dashboard_warehouse_combo.clear(); self.dashboard_warehouse_combo.addItem('همه انبارها', None)
        self.dashboard_person_combo.clear(); self.dashboard_person_combo.addItem('همه اشخاص', None)
        for w in self.dashboard_warehouses: self.dashboard_warehouse_combo.addItem(f"{w['code']} | {w['name']}", w['id'])
        for p in self.dashboard_persons: self.dashboard_person_combo.addItem(f"{p['first_name']} {p['last_name']}".strip(), p['id'])

    def reset_dashboard_period(self):
        self.date_from_edit.setDate(QDate.currentDate().addDays(-6)); self.date_to_edit.setDate(QDate.currentDate()); self.refresh_dashboard()

    def reset_dashboard_filters(self):
        self.dashboard_warehouse_combo.setCurrentIndex(0); self.dashboard_person_combo.setCurrentIndex(0)
        self.dashboard_operation_combo.setCurrentIndex(0); self.reset_dashboard_period()

    def _current_dashboard_period(self):
        return (self.date_from_edit.date().toString('yyyy-MM-dd'), self.date_to_edit.date().toString('yyyy-MM-dd'))

    # ---------- باز کردن فرم‌ها (همه لاگ می‌شوند) ----------
    def _connect_refresh(self, w) -> None:
        for sig in ('data_changed', 'transfer_completed', 'take_completed', 'accounts_changed', 'users_changed'):
            if hasattr(w, sig):
                try: getattr(w, sig).connect(self.refresh_dashboard)
                except Exception: pass

    def _add_window_button(self, key, title, w):
        if key in self.win_bar_buttons: return
        btn = QPushButton(title); btn.setObjectName('SecondaryButton')
        btn.clicked.connect(lambda _=None, w=w: (w.show(), w.raise_(), w.activateWindow()))
        self.win_bar_layout.addWidget(btn); self.win_bar_buttons[key] = btn

    def _remove_window_button(self, key):
        btn = self.win_bar_buttons.pop(key, None)
        if btn: btn.deleteLater()

    def _safe_show(self, cls, title: str) -> None:
        self.setWindowTitle(f'سیستم انبارداری هوشمند - {self._company_name()}')
        self._audit_open(title)
        if not hasattr(self, '_open_forms'): self._open_forms = {}
        key = cls.__name__
        w = self._open_forms.get(key)
        if w is not None:
            try: w.show(); w.raise_(); w.activateWindow(); return
            except RuntimeError: self._open_forms.pop(key, None)
        try:
            w = cls(self.db, self.user_data)
            w.setWindowFlags(w.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
            self._connect_refresh(w)
            w.setAttribute(Qt.WA_DeleteOnClose, True)
            w.destroyed.connect(lambda _=None, k=key: (self._open_forms.pop(k, None), self._remove_window_button(k)))
            self._open_forms[key] = w; self._add_window_button(key, title, w); w.show()
        except Exception:
            import traceback; QMessageBox.critical(self, 'خطا', f'باز کردن {title}:\n\n{traceback.format_exc()}')

    def _safe_exec(self, cls, title: str) -> None:
        self._audit_open(title)
        try:
            w = cls(self.db, self.user_data); self._connect_refresh(w); w.exec_()
        except Exception:
            import traceback; QMessageBox.critical(self, 'خطا', f'باز کردن {title}:\n\n{traceback.format_exc()}')

    def open_user_manager(self):
        from app.ui.user_manager_window import UserManagerWindow; self._safe_exec(UserManagerWindow, 'مدیریت کاربران')
    def open_company_profile(self):
        if self.user_data.get('role_code') != 'ADMIN': QMessageBox.warning(self, 'عدم دسترسی', 'فقط مدیر سیستم.'); return
        from app.ui.company_form import CompanyProfileDialog; self._safe_exec(CompanyProfileDialog, 'مشخصات شرکت')
    def open_return_manager(self):
        if not self._has_any_permission('receipts.manage', 'issues.manage'): QMessageBox.warning(self, 'عدم دسترسی', 'مجوز ندارید.'); return
        from app.ui.return_management_window import ReturnManagementWindow; self._safe_show(ReturnManagementWindow, 'برگشت کالا')
    def open_fiscal_periods(self):
        from app.ui.fiscal_period_window import FiscalPeriodWindow; self._safe_exec(FiscalPeriodWindow, 'دوره‌های مالی')
    def open_pallet_manager(self):
        from app.ui.pallets_window import PalletManagerWindow; self._safe_show(PalletManagerWindow, 'پالت‌ها')
    def open_person_manager(self):
        from app.ui.person_window import PersonManagerWindow; self._safe_show(PersonManagerWindow, 'اشخاص')
    def open_warehouse_manager(self):
        from app.ui.warehouses_window import WarehouseManagerWindow; self._safe_show(WarehouseManagerWindow, 'انبارها')
    def open_opening_inventory(self):
        from app.ui.opening_inventory_window import OpeningInventoryWindow; self._safe_show(OpeningInventoryWindow, 'افتتاحیه انبار')
    def open_receipt_manager(self):
        if not self._has_any_permission('receipts.manage'): QMessageBox.warning(self, 'عدم دسترسی', 'مجوز ندارید.'); return
        from app.ui.receipt_manager_window import ReceiptManagerWindow; self._safe_show(ReceiptManagerWindow, 'رسید انبار')
    def open_issue_manager(self):
        if not self._has_any_permission('issues.manage'): QMessageBox.warning(self, 'عدم دسترسی', 'مجوز ندارید.'); return
        from app.ui.issue_manager_window import IssueManagerWindow; self._safe_show(IssueManagerWindow, 'حواله‌های باز')
    def open_finance_manager(self):
        from app.ui.finance_window import FinanceManagerWindow; self._safe_show(FinanceManagerWindow, 'اسناد مالی باز')
    def open_general_ledger(self):
        from app.ui.general_ledger_window import GeneralLedgerWindow; self._safe_exec(GeneralLedgerWindow, 'دفتر کل و معین') 
    def open_balance_sheet(self):
        from app.ui.balance_sheet_window import BalanceSheetWindow; self._safe_exec(BalanceSheetWindow, 'ترازنامه')        
    def open_bank_reconciliation(self):
        from app.ui.bank_reconciliation_window import BankReconciliationWindow; self._safe_exec(BankReconciliationWindow, 'مغایرت بانکی')
    def open_treasury_manager(self):
        from app.ui.treasury_window import TreasuryManagementWindow; self._safe_show(TreasuryManagementWindow, 'صندوق/بانک')
    def open_return_report(self):
        from app.ui.return_report_window import ReturnReportWindow; self._safe_show(ReturnReportWindow, 'گزارش برگشت')
    def open_receipt_report(self):
        from app.ui.receipt_report_window import ReceiptReportWindow; self._safe_show(ReceiptReportWindow, 'گزارش ورود کالا')
    def open_issue_report(self):
        from app.ui.issue_report_window import IssueReportWindow; self._safe_show(IssueReportWindow, 'گزارش خروج کالا')
    def open_payroll_manager(self):
        from app.ui.payroll_manager_window import PayrollManagerWindow
        self._safe_show(PayrollManagerWindow, 'مدیریت پرداختی پرسنل')  

 
        
    # ✅ متد جدید برای باز کردن گزارش پیش‌فاکتور
    def open_proforma_report(self):
        from app.ui.proforma_report_window import ProformaReportWindow
        self._safe_show(ProformaReportWindow, 'گزارش پیش‌فاکتورها')

    def open_full_excel_export(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from app.core.jalali import today_iso_date
        path, _ = QFileDialog.getSaveFileName(self, 'خروجی اکسل کامل', f'حسابداری_کامل_{today_iso_date()}.xls', 'Excel XML (*.xml)')
        if not path: return
        if not path.lower().endswith('.xml'): path += '.xml'
        def esc(v): return (str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        sheets = [
            ('اشخاص', "SELECT id, first_name||' '||last_name AS name, mobile, company_name FROM persons"),
            ('پالت ها', "SELECT id, code, name, material_type FROM pallets"),
            ('موجودی انبار', "SELECT p.code, p.name, w.name AS wh, il.quantity FROM inventory_levels il JOIN pallets p ON p.id=il.pallet_id JOIN warehouses w ON w.id=il.warehouse_id"),
            ('رسیدها', "SELECT id, receipt_no, receipt_date, total_amount, status FROM warehouse_receipts"),
            ('اقلام رسید', "SELECT ri.receipt_id, p.code, ri.qty, ri.unit_price FROM warehouse_receipt_items ri JOIN pallets p ON p.id=ri.pallet_id"),
            ('حواله ها', "SELECT id, issue_no, issue_date, total_amount, status FROM warehouse_issues"),
            ('اقلام حواله', "SELECT ii.issue_id, p.code, ii.qty, ii.unit_price FROM warehouse_issue_items ii JOIN pallets p ON p.id=ii.pallet_id"),
            ('اسناد مالی باز', "SELECT finance_no, operation_type, direction, finance_date, total_amount, settled_amount, status FROM financial_documents"),
            ('تراکنش و چک', "SELECT financial_document_id, amount, status, due_date, check_no FROM payment_entries"),
            ('صندوق و بانک', "SELECT code, name, account_type, current_balance FROM treasury_accounts"),
            ('گردش خزانه', "SELECT treasury_account_id, transaction_date, transaction_type, amount, balance_after, description FROM treasury_transactions"),
            ('هزینه ها', "SELECT expense_no, expense_date, amount, paid_amount, status FROM expenses"),
            ('ضایعات', "SELECT sale_no, sale_date, total_amount, status, vehicle_no FROM scrap_sales"),
            ('چک های دستی', "SELECT check_no, amount, status, due_date FROM checkbook_checks"),
            ('خروج کالا', "SELECT wi.issue_no, ol.reference_no AS ref, wi.stage_no, wi.issue_date, (p.first_name||' '||p.last_name) AS customer, (d.first_name||' '||d.last_name) AS driver, wi.waybill_no, SUM(ii.qty) AS stage_qty, ol.total_load_qty, SUM(ii.qty*ii.unit_price) AS amount, wi.issue_status FROM warehouse_issues wi LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id LEFT JOIN persons p ON p.id=wi.customer_id LEFT JOIN persons d ON d.id=wi.driver_id LEFT JOIN warehouse_issue_items ii ON ii.issue_id=wi.id GROUP BY wi.id ORDER BY wi.issue_date"),
            ('ورود کالا', "SELECT wr.receipt_no, il.Reference_no AS ref, wr.stage_no, wr.receipt_date, (p.first_name||' '||p.last_name) AS supplier, (d.first_name||' '||d.last_name) AS driver, wr.waybill_no, SUM(ri.qty) AS stage_qty, il.total_load_qty, SUM(ri.qty*ri.unit_price) AS amount, wr.receipt_status FROM warehouse_receipts wr LEFT JOIN inbound_loads il ON il.id=wr.inbound_load_id LEFT JOIN persons p ON p.id=wr.supplier_id LEFT JOIN persons d ON d.id=wr.driver_id LEFT JOIN warehouse_receipt_items ri ON ri.receipt_id=wr.id GROUP BY wr.id ORDER BY wr.receipt_date"),
        ]
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<?mso-application progid="Excel.Sheet"?>', '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">']
        done = []
        with self.db.connect() as conn:
            for name, sql in sheets:
                try:
                    cur = conn.execute(sql)
                except Exception: continue
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                xml.append(f'<Worksheet ss:Name="{esc(name)}"><Table>')
                xml.append('<Row>' + ''.join(f'<Cell><Data ss:Type="String">{esc(c)}</Data></Cell>' for c in cols) + '</Row>')
                for r in rows:
                    cells = []
                    for v in r:
                        if isinstance(v, (int, float)): cells.append(f'<Cell><Data ss:Type="Number">{v}</Data></Cell>')
                        else: cells.append(f'<Cell><Data ss:Type="String">{esc(v if v is not None else "")}</Data></Cell>')
                    xml.append('<Row>' + ''.join(cells) + '</Row>')
                xml.append('</Table></Worksheet>'); done.append(name)
        xml.append('</Workbook>')
        with open(path, 'w', encoding='utf-8') as f: f.write(''.join(xml))
        QMessageBox.information(self, 'خروجی اکسل', f'فایل با {len(done)} شیت ذخیره شد:\n{path}')

    def open_inv_fin_recon(self):
        from app.ui.inv_fin_recon_window import InvFinReconWindow; self._safe_show(InvFinReconWindow, 'مغایرت انبار و مالی')
    def open_top_parties(self):
        from app.ui.top_parties_window import TopPartiesWindow; self._safe_show(TopPartiesWindow, 'طرف‌های برتر')
    def open_profitability(self):
        from app.ui.profitability_window import ProfitabilityWindow; self._safe_show(ProfitabilityWindow, 'سودآوری')
    def open_pnl_report(self):
        from app.ui.pnl_report_window import PnlReportWindow; self._safe_show(PnlReportWindow, 'سود و زیان')
    def open_aging_report(self):
        from app.ui.aging_report_window import AgingReportWindow; self._safe_show(AgingReportWindow, 'سن بدهی‌ها')
    def open_expense_category(self):
        from app.ui.expense_category_window import ExpenseCategoryManagerWindow; self._safe_exec(ExpenseCategoryManagerWindow, 'دسته‌بندی هزینه')
    def open_expense_entry(self):
        from app.ui.expense_window import ExpenseWindow; self._safe_exec(ExpenseWindow, 'ثبت هزینه')
    def open_expense_report(self):
        from app.ui.expense_report_window import ExpenseReportWindow; self._safe_show(ExpenseReportWindow, 'گزارش هزینه‌ها')
    def open_cash_transfer(self):
        from app.ui.cash_transfer_window import CashTransferWindow; self._safe_show(CashTransferWindow, 'مدیریت نقدینگی')
    def open_cash_account_manager(self):
        from app.ui.cash_account_manager_window import CashAccountManagerWindow; self._safe_show(CashAccountManagerWindow, 'مدیریت حساب‌ها')
    def open_year_end(self):
        from app.ui.year_end_window import YearEndWindow; self._safe_show(YearEndWindow, 'بستن سال مالی')
    def open_cashflow(self):
        from app.ui.cashflow_window import CashflowWindow; self._safe_show(CashflowWindow, 'پیش‌بینی نقدینگی')
    def open_scrap_window(self):
        from app.ui.scrap_window import ScrapWindow; self._safe_show(ScrapWindow, 'فروش ضایعات')
    def open_checkbook(self):
        from app.ui.checkbook_window import CheckbookWindow; self._safe_exec(CheckbookWindow, 'دفترچه چک')    
    def open_dead_stock(self):
        from app.ui.dead_stock_window import DeadStockWindow; self._safe_show(DeadStockWindow, 'اقلام راکد')
    def open_box_production(self):
        from app.ui.box_production_window import BoxDesignCalculator; self._safe_show(BoxDesignCalculator, 'تولید جعبه')
    def open_box_sale_form(self):
        from app.ui.box_sale_form import BoxSaleFormWindow; self._safe_show(BoxSaleFormWindow, 'فروش جعبه')
    def open_stock_take(self):
        from app.ui.stock_take_window import StockTakeWindow; self._safe_show(StockTakeWindow, 'انبارگردانی')
    def open_units_manager(self):
        from app.ui.units_window import UnitsManagerWindow; self._safe_exec(UnitsManagerWindow, 'واحدهای کالا')
    def open_consumables(self):
        from app.ui.consumables_window import ConsumablesWindow; self._safe_exec(ConsumablesWindow, 'مصارف مصرفی')
    def open_consumable_items(self):
        from app.ui.consumable_items_window import ConsumableItemsWindow; self._safe_exec(ConsumableItemsWindow, 'اقلام مصرفی')
    def open_consumable_report(self):
        from app.ui.consumable_report_window import ConsumableReportWindow; self._safe_exec(ConsumableReportWindow, 'گزارش خرید اقلام')
    def open_transfer(self):
        from app.ui.transfer_window import TransferWindow; self._safe_show(TransferWindow, 'جابجایی بین انبارها')
    def open_treasury_ledger(self):
        from app.ui.treasury_ledger_window import TreasuryLedgerWindow
        self._safe_show(TreasuryLedgerWindow, 'گردش صندوق/بانک')

    def open_reports_window(self):
        from app.ui.reports_window import ReportsWindow; self._safe_show(ReportsWindow, 'گزارشات')
    def open_combined_report(self):
        from app.ui.combined_report_window import CombinedReportWindow
        self._safe_exec(CombinedReportWindow, 'گزارش ترکیبی')

    def open_proforma(self):
        from app.ui.proforma_window import ProformaInvoiceWindow; self._safe_exec(ProformaInvoiceWindow, 'پیش‌فاکتور')
    def open_daily_activity(self):
        from app.ui.daily_activity_window import DailyActivityWindow; self._safe_exec(DailyActivityWindow, 'گزارش روزانه')
    def open_permission_manager(self):
        from app.ui.permission_manager_window import PermissionManagerWindow; self._safe_exec(PermissionManagerWindow, 'سطوح دسترسی')
    def open_audit_log(self):
        from app.ui.audit_log_window import AuditLogWindow; self._safe_exec(AuditLogWindow, 'گزارش فعالیت')
    def open_backup_manager(self):
        if self.user_data.get('role_code') != 'ADMIN': QMessageBox.warning(self, 'عدم دسترسی', 'فقط مدیر سیستم.'); return
        from app.ui.backup_manager import BackupManagerDialog; self._safe_exec(BackupManagerDialog, 'پشتیبان‌گیری')

    def closeEvent(self, event):
        open_forms = [w for w in getattr(self, '_open_forms', {}).values() if w is not None]
        if open_forms:
            r = QMessageBox.question(self, 'بستن داشبورد', f'{len(open_forms)} فرم باز است. با بستن داشبورد، همهٔ آن‌ها بسته می‌شوند.\nادامه می‌دهید؟', QMessageBox.Yes | QMessageBox.No)
            if r != QMessageBox.Yes: event.ignore(); return
            for w in open_forms:
                try: w.close()
                except Exception: pass
        event.accept()

    def _company_name(self) -> str:
        try:
            with self.db.connect() as conn:
                r = conn.execute("SELECT company_name FROM company_profile ORDER BY id LIMIT 1").fetchone()
                if r and r[0]: return str(r[0]).strip()
        except Exception: pass
        return 'راد صنعت نوین'

    def _show_about(self) -> None:
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        import os
        
        name = self._company_name()
        dlg = QDialog(self)
        dlg.setWindowTitle('درباره برنامه')
        dlg.setObjectName('AboutDialog')
        dlg.setStyleSheet("QDialog#AboutDialog { background-color: #1e293b; } QLabel { color: #f5f7fa; background: transparent; } QLabel#AboutTitle { color: #ffffff; font-size: 20px; font-weight: bold; } QLabel#AboutCompany { color: #60a5fa; font-size: 16px; font-weight: bold; } QLabel#AboutVersion { color: #f59e0b; } QPushButton { background-color: #2563eb; color: #ffffff; border-radius: 6px; padding: 8px 18px; }")  # about_card2
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.setFixedSize(540, 680)
        
        v = QVBoxLayout(dlg)
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        ico = os.path.join(base, 'icon.png')
        if not os.path.exists(ico): ico = os.path.join(base, 'rad_sanat_novin.ico')
        
        logo = QLabel()
        if os.path.exists(ico): logo.setPixmap(QPixmap(ico).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter); v.addWidget(logo)
        
        t = QLabel('سیستم انبارداری هوشمند'); t.setObjectName('AboutTitle'); t.setAlignment(Qt.AlignCenter); t.setStyleSheet('font-size:21px;font-weight:bold;'); v.addWidget(t)
        s = QLabel(name); s.setObjectName('AboutCompany'); s.setAlignment(Qt.AlignCenter); s.setStyleSheet('font-size:17px;font-weight:bold;color:#2563eb;'); v.addWidget(s)
        ver = QLabel('نسخه: Ver_1405-01'); ver.setObjectName('AboutVersion'); ver.setAlignment(Qt.AlignCenter); ver.setStyleSheet('font-size:14px;'); v.addWidget(ver)
        
        body = QLabel(f"""طراحی و برنامه‌نویسی: کریم رضایی
با همکاری هوش مصنوعی
طراح نرم‌افزار سردخانه رازی
مورد استفاده در سردخانه‌های سراسر ایران

این نرم‌افزار بنا به سفارش جناب آقای بهزاد علیپور
مدیرعامل محترم شرکت {name}
طراحی و تدوین گردیده است.

© کلیه حقوق برای شرکت {name} محفوظ است.""")
        body.setObjectName('AboutBody'); body.setAlignment(Qt.AlignCenter); body.setWordWrap(True); body.setStyleSheet('font-size:15px;'); v.addWidget(body)
        
        b = QPushButton('بستن'); b.setObjectName('PrimaryButton'); b.clicked.connect(dlg.accept); v.addWidget(b)
        dlg.exec_()

    def _tick_dash_time(self):
        try:
            from datetime import datetime
            self.dash_time_lbl.setText('ساعت: ' + datetime.now().strftime('%H:%M'))
        except Exception:
            pass

    def _cap_settled(self):
        try:
            with self.db.connect() as _c:
                _c.execute("UPDATE financial_documents SET settled_amount = total_amount "
                             "WHERE settled_amount > total_amount")
                _c.commit()
        except Exception:
            pass

    def refresh_dashboard(self):
        self._cap_settled()
        self.setWindowTitle(f'سیستم انبارداری هوشمند - {self._company_name()}')
        date_from, date_to = self._current_dashboard_period()
        if date_from > date_to:
            self.period_info_label.setText('خطا: تاریخ شروع بعد از پایان است.'); return
        warehouse_id = self.dashboard_warehouse_combo.currentData()
        person_id = self.dashboard_person_combo.currentData()
        operation_filter = self.dashboard_operation_combo.currentData() or 'ALL'

        while self.cards_layout.count():
            it = self.cards_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        stats = self.db.fetch_stats()
        ps = self.db.fetch_dashboard_period_summary(date_from, date_to, warehouse_id, person_id, operation_filter)
        cards = [
            SummaryCard('پالت‌های فعال', str(stats['pallets']), '#16a34a'),
            SummaryCard('انبارهای فعال', str(stats['warehouses']), '#2563eb'),
            SummaryCard('رسیدهای باز', str(ps['receipts_count']), '#ea580c'),
            SummaryCard('حواله‌های باز', str(ps['issues_count']), '#9333ea'),
            SummaryCard('اسناد مالی باز', str(ps['finance_docs_count']), '#0891b2'),
            SummaryCard('بارهای باز', str(stats['open_shipments']), '#f59e0b'),
        ]
        for i, c in enumerate(cards): self.cards_layout.addWidget(c, i // 3, i % 3)

        fin = self.db.fetch_dashboard_financial_overview(date_from, date_to, warehouse_id, person_id, operation_filter)
        whv = self.db.fetch_dashboard_warehouse_values(date_from, date_to, warehouse_id, person_id, operation_filter)
        trb = self.db.fetch_dashboard_treasury_balances(date_from, date_to, warehouse_id, person_id, operation_filter)
        act = self.db.fetch_dashboard_recent_activity(date_from, date_to, warehouse_id, person_id, operation_filter)

        sw = self.dashboard_warehouse_combo.currentText() if warehouse_id else 'همه انبارها'
        sp = self.dashboard_person_combo.currentText() if person_id else 'همه اشخاص'
        so = self.dashboard_operation_combo.currentText()
        self.period_info_label.setText(f'بازه: {date_from} تا {date_to} | انبار: {sw} | شخص: {sp} | عملیات: {so}')

        self.finance_chart.setHtml(build_financial_balance_chart(fin, title='نمای مالی بازه', subtitle=f'از {date_from} تا {date_to}'))
        self.warehouse_chart.setHtml(build_warehouse_value_chart(whv[:6], title='خالص تغییرات ریالی انبارها', subtitle=f'انبار: {sw}'))
        self.treasury_chart.setHtml(build_treasury_balance_chart(trb[:6], title='گردش صندوق / بانک', subtitle=f'شخص: {sp}'))
        self.activity_chart.setHtml(build_activity_chart(act, title='روند عملیات', subtitle=f'{so}'))

        self.low_stock_list.clear()
        rows = self.db.fetch_low_stock_pallets(warehouse_id)
        if not rows:
            self.low_stock_list.addItem(QListWidgetItem('هشدار موجودی کمی ثبت نشده است.'))
            return
        for r in rows:
            self.low_stock_list.addItem(QListWidgetItem(f"{r['code']} | {r['name']} | موجودی: {r['current_stock']} | حد: {r['low_stock_threshold']}"))