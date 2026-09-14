# -*- coding: utf-8 -*-
"""
نقطه ورود اصلی سیستم انبارداری
نسخه تمیز و سازگار با PyQt5
"""

from __future__ import annotations

import importlib
import os
import sys
import traceback
from pathlib import Path


# ----------------------------------------------------------------------
# تنظیم مسیر پروژه
# ----------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# مسیر اصلی پروژه
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# مسیرهای احتمالی نسخه‌های پشتیبان
for extra_path in (
    BASE_DIR / "app",
    BASE_DIR / "ui_patch_work",
):
    if extra_path.exists() and str(extra_path) not in sys.path:
        sys.path.append(str(extra_path))


# ----------------------------------------------------------------------
# تنظیمات PyQt5 و High DPI
# ----------------------------------------------------------------------

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox


try:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
except AttributeError:
    pass

try:
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
except AttributeError:
    pass


# ----------------------------------------------------------------------
# ابزار بارگذاری ماژول
# ----------------------------------------------------------------------

def import_class(module_names: tuple[str, ...], class_name: str):
    """
    کلاس را از اولین مسیر معتبر بارگذاری می‌کند.
    """

    errors = []

    کلاس را از اولین مسیر معتبر بارگذاری می‌کند.
        """

    errors = []

_module(module_name)
            return getattr(module, class_name)

        except (ModuleNotFoundError, ImportError, AttributeError) as exc:
            errors.append(f"{module_name}: {exc}")

    message = (
        f"کلاس {class_name} پیدا نشد.\n\n"
        + "\n".join(errors)
    )

    raise ImportError(message)


# ----------------------------------------------------------------------
# بارگذاری کلاس‌های اصلی
# ----------------------------------------------------------------------

LoginWindow = import_class(
    (
        "app.ui.login_window",
        "ui.login_window",
        "ui.ui.login_window",
        "ui_patch_work.ui.login_window",
    ),
    "LoginWindow",
)

MainWindow = import_class(
    (
        "app.ui.main_window",
        "ui.main_window",
        "ui.ui.main_window",
        "ui_patch_work.ui.main_window",
    ),
    "MainWindow",
)

DatabaseManager = import_class(
    (
        "app.core.database",
        "core.database",
    ),
    "DatabaseManager",
)


    ----------------------------------------------------------------------
# مسیر دیتابیس
# ----------------------------------------------------------------------

def get_database_path() -> str:
    """
    ابتدا دیتابیس داخل data و سپس دیتاب    """
    ابتدا دیتابیس داخل data و سپس دیتاب_paths = (
        BASE_DIR / "data" / "app.db",
        BASE_DIR / "app.db",
    )

    for path in possible_paths:
        if path.exists():
            return str(path)

    # اگر وجود نداشت، مسیر استاندارد ریشه پروژه استفاده می‌شود
    return str(BASE_DIR / "app.db")


# ----------------------------------------------------------------------
# لایسنس
# ----------------------------------------------------------------------

def ensure_license(app: QApplication) -> bool:
    """
    اجرای بررسی لایسنس در صورت وجود license_manager.
    """

    module_names = (
        "app.core.license_manager",
        "core.license_manager",
    )

    license_module = None

    for module_name in module_names:
        try:
            license_module = importlib.import_module(module_name)
            break

        except ModuleNotFoundError as exc:
            missing_name = exc.name or ""

            # اگر خود ماژول وجود نداشته باشد، مسیر بعدی بررسی می‌شود.
            # اما اگر وابستگی داخلی آن خراب باشد، خطا پنهان نمی‌شود.
            if (
                missing_name == module_name
                or module_name.startswith(missing_name + ".")
            ):
                continue

            raise

    # اگر license_manager در این نسخه وجود نداشت،
    # برنامه بدون اجرای مرحله لایسنس ادامه می‌دهد.
    if license_module is None:
        return True

    checker = getattr(license_module, "ensure_license", None)

    if not callable(checker):
        return True

    result = checker(app)

    # None یعنی اجرای موفق بدون مقدار بازگشتی
    if result is None:
        return True

    return bool(result)


# ----------------------------------------------------------------------
# اطلاعات کاربر
# ----------------------------------------------------------------------

def get_login_user_data(login_window):
    """
    دریافت اطلاعات کاربر از LoginWindow.
    """

    getter = getattr(login_window, "get_user_data", None)

    if callable(getter):
        return getter()

    user_data = getattr(login_window, "user_data", None)

    if user_data is not None:
        return user_data

    user_data = getattr(login_window, "user", None)

    return user_data


# ----------------------------------------------------------------------
# اجرای برنامه
# ----------------------------------------------------------------------

def run_application() -> int:
    app = QApplication(sys.argv)

    # آیکون برنامه، در صورت وجود
    icon_candidates = (
        BASE_DIR / "rad_sanat_novin.ico",
        BASE_DIR / "icon.ico",
        BASE_DIR / "app.ico",
    )

    for icon_path in icon_candidates:
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break

    # راست‌چین کردن رابط کاربری
    app.setLayoutDirection(Qt.RightToLeft)

    # اتصال به دیتابیس
    database_path = get_database_path()
    db = DatabaseManager(database_path)

    initialize_database = getattr(db, "initialize", None)

    if callable(initialize_database):
        initialize_database()

    # نمایش صفحه ورود
    login_window = LoginWindow(db)

    exec_method = getattr(login_window, "exec_", None)

    if not callable(exec_method):
        exec_method = getattr(login_window, "exec", None)

    if not callable(exec_method):
        raise RuntimeError(
            "متد exec_ یا exec در LoginWindow پیدا نشد."
        )

    login_result = exec_method()

    if login_result != QDialog.Accepted:
        return 0

    # دریافت اطلاعات کاربر
    user_data = get_login_user_data(login_window)

    if not user_data:
        QMessageBox.critical(
            None,
            "خطا",
            "اطلاعات کاربر دریافت نشد.",
        )
        return 1

    # ایجاد پنجره اصلی
    try:
        main_window = MainWindow(db, user_data)

    except TypeError:
        # سازگاری با نسخه‌هایی که ترتیب پارامترها متفاوت است
        try:
            main_window = MainWindow(user_data, db)

        except TypeError:
            main_window = MainWindow(db)

    # تنظیم عنوان پنجره
    if isinstance(user_data, dict):
        user_name = (
            user_data.get("full_name")
            or user_data.get("username")
            or ""
        )
    else:
        user_name = ""

    if user_name:
        main_window.setWindowTitle(
            f"سیستم انبارداری - {user_name}"
        )

    main_window.show()

    # بررسی لایسنس
    if not ensure_license(app):
        return 0

    return app.exec_()


# ----------------------------------------------------------------------
# نقطه شروع
# ----------------------------------------------------------------------

def main() -> int:
    try:
        return run_application()

    except Exception as exc:
        traceback.print_exc()

        error_text = (
            "خطا هنگام اجرای برنامه:\n\n"
            f"{type(exc).__name__}: {exc}"
        )

        app = QApplication.instance()

        if app is None:
            app = QApplication(sys.argv)

        QMessageBox.critical(
            None,
            "خطای اجرای برنامه",
            error_text,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
