# -*- coding: utf-8 -*-
"""
document_images_window.py - فرم مدیریت تصاویر اسناد

- انتخاب مشتری/تامین‌کننده + تاریخ سند
- بارگذاری حداکثر ۳ عکس (اختیاری)
- ذخیره در uploads/documents + مسیر در دیتابیس
- پیش‌نمایش و حذف عکس‌ها

استفاده:
  از منوی مالی: DocumentImagesWindow(db, user_data).exec_()
"""
import os
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFileDialog, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.core.database import DatabaseManager
from app.core.jalali import jalali_date_display_from_iso
from app.core.document_images import (
    save_document_image,
    get_document_images,
    delete_document_image,
    get_person_documents,
    MAX_IMAGES,
)


class DocumentImagesWindow(QDialog):
    """فرم بارگذاری و مدیریت تصاویر اسناد"""

    def __init__(self, db: DatabaseManager, user_data: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.persons: List[Dict[str, Any]] = []
        self.images: List[Dict[str, Any]] = []

        self.setWindowTitle('📷 مدیریت تصاویر اسناد')
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(900, 700)

        self._load_persons()
        self._build_ui()
        self._refresh_images()

    # ------------------------------------------------------------------
    # بارگذاری اشخاص (مشتری/تامین‌کننده)
    # ------------------------------------------------------------------

    def _load_persons(self) -> None:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("""
                    SELECT p.id, p.first_name, p.last_name,
                           (SELECT GROUP_CONCAT(role_type) FROM person_roles pr
                            WHERE pr.person_id = p.id) AS roles
                    FROM persons p
                    WHERE p.is_active = 1
                      AND EXISTS (SELECT 1 FROM person_roles pr
                                  WHERE pr.person_id = p.id
                                    AND pr.role_type IN ('CUSTOMER', 'SUPPLIER'))
                    ORDER BY p.first_name, p.last_name
                """).fetchall()
                self.persons = [
                    {
                        'id': r[0],
                        'first_name': r[1] or '',
                        'last_name': r[2] or '',
                        'roles': (r[3] or ''),
                    }
                    for r in rows
                ]
        except Exception:
            self.persons = []

    def _person_label(self, p: Dict[str, Any]) -> str:
        name = f"{p['first_name']} {p['last_name']}".strip()
        role = ''
        if 'CUSTOMER' in p['roles']:
            role = 'مشتری'
        elif 'SUPPLIER' in p['roles']:
            role = 'تامین‌کننده'
        return f"{name} [{role}]".strip()

    # ------------------------------------------------------------------
    # ساخت UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # هدر
        header = QFrame()
        header.setObjectName('Card')
        hl = QVBoxLayout(header)
        title = QLabel('📷  تصاویر اسناد (رسید / حواله)')
        title.setStyleSheet('font-size: 18px; font-weight: bold;')
        subtitle = QLabel('بارگذاری حداکثر ۳ عکس برای هر سند (اختیاری) — از کامپیوتر یا گوشی (USB/WiFi)')
        subtitle.setStyleSheet('color: #64748b; font-size: 11px;')
        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        # فیلترها
        filter_group = QGroupBox('انتخاب سند')
        fl = QGridLayout(filter_group)
        fl.setHorizontalSpacing(12)
        fl.setVerticalSpacing(10)

        self.person_combo = QComboBox()
        self.person_combo.addItem('انتخاب مشتری / تامین‌کننده', None)
        for p in self.persons:
            self.person_combo.addItem(self._person_label(p), p['id'])
        self.person_combo.currentIndexChanged.connect(self._refresh_images)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('yyyy-MM-dd')

        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItem('نوع سند', '')
        self.doc_type_combo.addItem('رسید انبار', 'RECEIPT')
        self.doc_type_combo.addItem('حواله خروج', 'ISSUE')
        self.doc_type_combo.addItem('پیش‌فاکتور', 'PROFORMA')
        self.doc_type_combo.addItem('سایر', 'OTHER')

        self.doc_no_edit = QLineEdit()
        self.doc_no_edit.setPlaceholderText('شماره سند (اختیاری)')

        self.date_jalali_label = QLabel('-')
        self.date_jalali_label.setStyleSheet('color: #f59e0b; font-size: 14px; font-weight: bold;')
        self.date_edit.dateChanged.connect(self._update_jalali)

        fl.addWidget(QLabel('مشتری / تامین‌کننده:'), 0, 0)
        fl.addWidget(self.person_combo, 0, 1, 1, 3)
        fl.addWidget(QLabel('تاریخ سند:'), 1, 0)
        fl.addWidget(self.date_edit, 1, 1)
        fl.addWidget(self.date_jalali_label, 1, 2)
        fl.addWidget(QLabel('نوع سند:'), 2, 0)
        fl.addWidget(self.doc_type_combo, 2, 1)
        fl.addWidget(QLabel('شماره سند:'), 2, 2)
        fl.addWidget(self.doc_no_edit, 2, 3)
        root.addWidget(filter_group)

        # دکمه بارگذاری
        upload_group = QGroupBox('بارگذاری عکس')
        ul = QHBoxLayout(upload_group)
        self.upload_btn = QPushButton('📤 بارگذاری عکس')
        self.upload_btn.setStyleSheet(
            'background-color: #2563eb; color: white; font-weight: bold; padding: 10px 24px;'
        )
        self.upload_btn.clicked.connect(self._upload_image)
        ul.addWidget(self.upload_btn)
        ul.addStretch()
        self.count_label = QLabel('0 / 3 عکس')
        self.count_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #64748b;')
        ul.addWidget(self.count_label)
        root.addWidget(upload_group)

        # پیش‌نمایش عکس‌ها
        preview_group = QGroupBox('عکس‌های بارگذاری‌شده')
        pl = QVBoxLayout(preview_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(12)
        scroll.setWidget(container)
        pl.addWidget(scroll)
        root.addWidget(preview_group, 1)

    # ------------------------------------------------------------------
    # به‌روزرسانی تاریخ شمسی
    # ------------------------------------------------------------------

    def _update_jalali(self) -> None:
        iso = self.date_edit.date().toString('yyyy-MM-dd')
        self.date_jalali_label.setText(jalali_date_display_from_iso(iso))

    # ------------------------------------------------------------------
    # بارگذاری و نمایش عکس‌ها
    # ------------------------------------------------------------------

    def _refresh_images(self) -> None:
        """نمایش عکس‌های شخص انتخاب‌شده"""
        # پاک کردن گرید
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        person_id = self.person_combo.currentData()
        if not person_id:
            self.count_label.setText('0 / 3 عکس')
            return

        try:
            with self.db.connect() as conn:
                self.images = get_person_documents(conn, int(person_id))
        except Exception:
            self.images = []

        # نمایش
        for i, img in enumerate(self.images):
            card = self._make_image_card(img)
            self.grid.addWidget(card, i // 3, i % 3)

        shown = len(self.images)
        self.count_label.setText(f'{shown} عکس بارگذاری‌شده')

    def _make_image_card(self, img: Dict[str, Any]) -> QWidget:
        card = QWidget()
        lay = QVBoxLayout(card)
        lay.setSpacing(6)

        # تصویر
        img_label = QLabel()
        img_label.setFixedSize(180, 140)

        img_label.setAlignment(Qt.AlignCenter)
        try:
            pix = QPixmap(os.path.join(os.getcwd(), img['file_path']))
            if not pix.isNull():
                img_label.setPixmap(pix.scaled(180, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img_label.setText('(خوانده نشد)')
        except Exception:
            img_label.setText('(خطا)')
        lay.addWidget(img_label)

        # توضیح
        info = QLabel(f"{img.get('doc_type') or '-'} | {img.get('uploaded_at', '')[:10]}")
        info.setStyleSheet('font-size: 10px; color: #64748b;')
        info.setAlignment(Qt.AlignCenter)
        lay.addWidget(info)

        # دکمه حذف
        del_btn = QPushButton('🗑 حذف')

        del_btn.clicked.connect(lambda checked, iid=img['id']: self._delete_image(iid))
        lay.addWidget(del_btn)

        return card

    def _upload_image(self) -> None:
        person_id = self.person_combo.currentData()
        if not person_id:
            QMessageBox.warning(self, 'خطا', 'لطفاً مشتری / تامین‌کننده را انتخاب کنید.')
            return

        # انتخاب فایل
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'انتخاب عکس',
            '', 'Images (*.jpg *.jpeg *.png *.bmp *.webp)'
        )
        if not file_path:
            return

        doc_type = self.doc_type_combo.currentData() or 'OTHER'
        doc_no = self.doc_no_edit.text().strip()
        doc_id = 0
        if doc_no:
            try:
                doc_id = int(doc_no)
            except ValueError:
                doc_id = 0

        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                save_document_image(
                    conn, doc_type, doc_id,
                    file_path, person_id=int(person_id),
                    uploaded_by=self.user_data.get('id'),
                )
            QMessageBox.information(self, 'موفق', 'عکس با موفقیت بارگذاری شد.')
            self._refresh_images()
        except ValueError as e:
            QMessageBox.warning(self, 'خطا', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در بارگذاری:\n{e}')

    def _delete_image(self, img_id: int) -> None:
        reply = QMessageBox.question(
            self, 'حذف عکس', 'آیا از حذف این عکس مطمئن هستید؟',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db.connect() as conn:
                delete_document_image(conn, img_id)
            self._refresh_images()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در حذف:\n{e}')
