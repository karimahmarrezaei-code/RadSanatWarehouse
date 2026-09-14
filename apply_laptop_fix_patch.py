"""
پچ جراحی رفع مشکل ماکسیمم‌سازی پنجره‌ها و جلوگیری از تغییر ناخواسته کمبوباکس با چرخ موس
"""
import py_compile
import sys

TARGET = "main.py"

try:
    with open(TARGET, "r", encoding="utf-8") as f:
        code = f.read()

    # ۱. اطمینان از ایمپورت‌های QtCore (QObject, QEvent, Qt)
    code = code.replace(
        "from PyQt5.QtCore import Qt",
        "from PyQt5.QtCore import Qt, QObject, QEvent"
    )

    # ۲. اصلاح تابع _safe_flags برای تضمین دکمه Maximize و برداشتن محدودیت FixedSize
    old_flags = """def _safe_flags(w):
    try:
        f = w.windowFlags()
        f |= Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        f &= ~Qt.WindowContextHelpButtonHint
        if f != w.windowFlags():
            w.setWindowFlags(f)
        if w.minimumSize() == w.maximumSize():
            w.setMaximumSize(16777215, 16777215)
    except Exception:
        pass"""

    new_flags = """def _safe_flags(w):
    try:
        f = w.windowFlags()
        f |= Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
        f &= ~Qt.WindowContextHelpButtonHint
        w.setWindowFlags(f)
        # آزاد کردن قفل ماکسیمم‌سازی
        w.setMaximumSize(16777215, 16777215)
    except Exception:
        pass"""

    if old_flags in code:
        code = code.replace(old_flags, new_flags, 1)

    # ۳. اضافه کردن گارد چرخ موس (Wheel Guard) برای کمبوباکس‌ها
    wheel_guard_code = '''
# --- COMBOBOX WHEEL GUARD ---
class _ComboWheelGuard(QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Wheel and isinstance(obj, QComboBox):
                v = obj.view()
                # اگر لیست بازشو بسته است، رویداد چرخ را خنثی کن
                if v is None or not v.isVisible():
                    ev.ignore()
                    return True
        except Exception:
            pass
        return False

_combo_wheel_guard = _ComboWheelGuard()

def _protect_combos(parent_widget):
    try:
        for cb in parent_widget.findChildren(QComboBox):
            if not getattr(cb, '_wheel_guarded', False):
                cb._wheel_guarded = True
                cb.installEventFilter(_combo_wheel_guard)
    except Exception:
        pass
# ----------------------------
'''

    if "_ComboWheelGuard" not in code:
        marker = "def _safe_fit(w):"
        code = code.replace(marker, wheel_guard_code + "\n" + marker, 1)

    # ۴. اعمال گارد کمبوباکس در _safe_show و _safe_fit
    if "_protect_combos(self)" not in code:
        code = code.replace(
            "_safe_flags(self); _compact_window(self);",
            "_safe_flags(self); _compact_window(self); _protect_combos(self);"
        )

    if "_protect_combos(w)" not in code:
        code = code.replace(
            "def _safe_fit(w):",
            "def _safe_fit(w):\n    _protect_combos(w)"
        )

    # ۵. اصلاح NameError در _safe_show
    code = code.replace(
        "if isinstance(w, _QD3):   # SHOW-SKIP\n            w.show(); return",
        "if isinstance(self, _QD3):   # SHOW-SKIP\n            self.show(); return"
    )

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(code)

    py_compile.compile(TARGET, doraise=True)
    print("✓ پچ با موفقیت روی main.py اعمال و کامپایل شد.")

except Exception as e:
    print(f"خطا در اعمال پچ: {e}")
    sys.exit(1)
