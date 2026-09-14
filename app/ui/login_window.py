from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.core.config import APP_NAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.core.database import DatabaseManager


class LoginWindow(QDialog):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        # LOGIN-MIN-SIZE: تضمین کفِ اندازه برای هر رزولوشن
        self.setMinimumSize(520, 420)

        self.db = db
        self.user_data = None
        self.setWindowTitle(f'ورود | {APP_NAME}')
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel('راد صنعت نوین')
        title.setObjectName('Title')
        subtitle = QLabel('سامانهٔ مدیریت انبار پالت')
        subtitle.setObjectName('Muted')

        card = QFrame()
        card.setObjectName('Card')
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('نام کاربری')
        self.username_edit.setPlaceholderText(DEFAULT_ADMIN_USERNAME)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText('رمز عبور')
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(DEFAULT_ADMIN_PASSWORD)

        form.addRow('نام کاربری:', self.username_edit)
        form.addRow('رمز عبور:', self.password_edit)

        hint = QLabel('')
        hint.hide()
        hint.setObjectName('Muted')

        buttons = QHBoxLayout()
        buttons.addStretch()
        login_button = QPushButton('ورود به برنامه')
        login_button.setStyleSheet('background:#2563eb; color:#ffffff; font-weight:bold; font-size:14px; border-radius:8px; padding:9px;')
        login_button.clicked.connect(self._handle_login)
        buttons.addWidget(login_button)

        card_layout.addLayout(form)
        card_layout.addWidget(hint)
        card_layout.addLayout(buttons)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(card)

    def _handle_login(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            QMessageBox.warning(self, 'ورود', 'نام کاربری و رمز عبور الزامی است.')
            return

        user = self.db.authenticate_user(username, password)
        if not user:
            QMessageBox.critical(self, 'ورود ناموفق', 'اطلاعات ورود صحیح نیست یا کاربر غیرفعال است.')
            return

        self.user_data = user
        self.accept()

    def get_user_data(self):
        """دریافت اطلاعات کاربر پس از Login موفق"""
        return self.user_data

    def is_login_successful(self):
        """بررسی موفقیت Login"""
        return self.login_successful

