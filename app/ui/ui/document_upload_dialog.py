# -*- coding: utf-8 -*-
"""
document_upload_dialog.py - فرم آپلود عکس سند (نسخه اصلاح‌شده برای v2)
"""
import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.core.database import DatabaseManager
from app.core.document_images import (
    save_document_image,
    get_document_images,
    delete_document_image,
    get_last_upload_dir,
    set_last_upload_dir,
    MAX_IMAGES,
)

_DOC_TITLES = {'RECEIPT': 'رسید', 'ISSUE': 'حواله', 'PROFORMA': 'پیش‌فاکتور', 'OTHER': 'سند'}


class DocumentUploadDialog(QDialog):
    """فرم آپلود عکس بعد از ثبت سند"""

    def __init__(
        self,
        db: DatabaseManager,
        doc_type: str,
        doc_id: int,
        person_id: Optional[int] = None,
        person_name: str = '',
        doc_no: str = '',
        user_data: Optional[Dict[str, Any]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.doc_type = doc_type
        self.doc_id = doc_id
        self.person_id = person_id
        self.person_name = person_name
        self.doc_no = doc_no
        self.user_data = user_data or {}
        self.images: list = []
        self._folder = get_last_upload_dir()

        title = _DOC_TITLES.get(doc_type, doc_type)
        self.setWindowTitle('📷 آپلود عکس {}'.format(title))
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(640, 560)

        self._build_ui()
        self._refresh_images()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # اطلاعات سند
        info = QLabel(
            '{} شماره {} — {}{}'.format(
                _DOC_TITLES.get(self.doc_type, self.doc_type),
                self.doc_no or self.doc_id,
                ('کد ' + str(self.person_id) + ' — ') if self.person_id else '',
                self.person_name or '—',
            )
        )
        info.setStyleSheet('')
        root.addWidget(info)

        # پوشه ذخیره
        folder_row = QHBoxLayout()
        self.folder_lbl = QLabel('پوشه: ' + self._folder)
        self.folder_lbl.setStyleSheet('color: #64748b; font-size: 13px;')
        self.folder_lbl.setWordWrap(True)
        folder_row.addWidget(self.folder_lbl, 1)
        self.folder_btn = QPushButton('📁 تغییر پوشه')
        self.folder_btn.setStyleSheet(
            'background-color: #5b6675; color: white; padding: 6px 14px; border-radius: 6px;'
        )
        self.folder_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_btn)
        root.addLayout(folder_row)

        # دکمه آپلود
        up_row = QHBoxLayout()
        self.upload_btn = QPushButton('⬆️ انتخاب عکس از کامپیوتر')
        self.upload_btn.setStyleSheet(
            'background-color: #2563eb; color: white; font-weight: bold; padding: 10px 24px; border-radius: 8px;'
            'font-size: 14px;'
        )
        self.upload_btn.clicked.connect(self._upload_image)
        up_row.addWidget(self.upload_btn)
        up_row.addStretch()
        self.count_lbl = QLabel('۰ / {} عکس'.format(MAX_IMAGES))
        self.count_lbl.setStyleSheet('font-size: 14px; font-weight: bold; color: #64748b;')
        up_row.addWidget(self.count_lbl)
        root.addLayout(up_row)

        # لیست عکس‌ها
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # ✅ اصلاح خط ناقص
        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(10)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        # دکمه پایان
        self.done_btn = QPushButton('✔ پایان')
        self.done_btn.setStyleSheet(
            'background-color: #10b981; color: white; font-weight: bold; padding: 10px 30px; border-radius: 8px;'
        )
        self.done_btn.clicked.connect(self.accept)
        root.addWidget(self.done_btn, 0, Qt.AlignLeft)

    def _choose_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, 'انتخاب پوشه ذخیره عکس‌ها', self._folder)
        if d:
            self._folder = d
            set_last_upload_dir(d)
            self.folder_lbl.setText('پوشه: ' + d)

    def _refresh_images(self) -> None:
        # پاک کردن قبلی
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        try:
            with self.db.connect() as conn:
                self.images = get_document_images(conn, self.doc_type, self.doc_id)
        except Exception:
            self.images = []

        for i, img in enumerate(self.images):
            card = self._make_image_card(img)
            self.grid.addWidget(card, i // 2, i % 2)

        shown = len(self.images)
        self.count_lbl.setText('{} / {} عکس'.format(shown, MAX_IMAGES))
        self.upload_btn.setEnabled(shown < MAX_IMAGES)

    def _make_image_card(self, img: Dict[str, Any]) -> QWidget:
        card = QWidget()
        lay = QVBoxLayout(card)
        lay.setSpacing(6)

        pix_label = QLabel()
        pix_label.setFixedSize(180, 140)
        pix_label.setStyleSheet(
            'border: 1px solid #5b6675; border-radius: 6px; background: #39424f;'
        )
        pix_label.setAlignment(Qt.AlignCenter)
        try:
            path = img['file_path']
            if not os.path.isabs(path):
                base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                path = os.path.join(base, 'data', 'uploads', path)
            pix = self._load_pix(path)
            if not pix.isNull():
                pix_label.setPixmap(pix.scaled(180, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                pix_label.setText('(نمایش ممکن نیست)')
        except Exception:
            pix_label.setText('(خطا)')
        lay.addWidget(pix_label)

        name = QLabel(os.path.basename(img['file_path']))
        name.setStyleSheet('font-size: 10px; color: #64748b;')
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        lay.addWidget(name)

        del_btn = QPushButton('🗑 حذف')
        del_btn.setStyleSheet('background-color: #ef4444; color: white; padding: 4px 12px; border-radius: 4px;')  # ✅ اصلاح خط ناقص
        del_btn.clicked.connect(lambda checked, iid=img['id']: self._delete_image(iid))
        lay.addWidget(del_btn)

        return card

    def _load_pix(self, path):
        from PyQt5.QtGui import QPixmap
        import os
        cands = [str(path)]
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            cands.append(os.path.join(base, '..', '..', str(path)))
        except Exception:
            pass
        try:
            cands.append(os.path.join('uploads', 'documents', os.path.basename(str(path))))
        except Exception:
            pass
        for c in cands:
            try:
                px = QPixmap(c)
                if not px.isNull():
                    return px
            except Exception:
                continue
        try:
            with open(str(path), 'rb') as f:
                px = QPixmap()
                px.loadFromData(f.read())
                if not px.isNull():
                    return px
        except Exception:
            pass
        return QPixmap()

    def _upload_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'انتخاب عکس', '',
            'Images (*.jpg *.jpeg *.png *.bmp *.webp)',
        )
        if not file_path:
            return

        try:
            with self.db.connect() as conn:
                save_document_image(
                    conn, self.doc_type, self.doc_id, file_path,
                    person_id=self.person_id, person_name=self.person_name,
                    target_dir=self._folder, uploaded_by=self.user_data.get('id'),
                )
            QMessageBox.information(self, 'موفق', 'عکس ذخیره شد.')
            self._refresh_images()
        except ValueError as e:
            QMessageBox.warning(self, 'خطا', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در ذخیره عکس:\n{}'.format(e))

    def _delete_image(self, img_id: int) -> None:
        reply = QMessageBox.question(
            self, 'حذف عکس', 'آیا مطمئن هستید این عکس حذف شود؟',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db.connect() as conn:
                delete_document_image(conn, img_id)
            self._refresh_images()
        except Exception as e:
            QMessageBox.critical(self, 'خطا', 'خطا در حذف:\n{}'.format(e))