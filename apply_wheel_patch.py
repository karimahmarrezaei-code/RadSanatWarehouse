"""
پچ اعمال اسکرول سراسری موس (Wheel Event Forwarding) بر روی main.py
"""
import py_compile
import sys

TARGET = "main.py"

try:
    with open(TARGET, "r", encoding="utf-8") as f:
        code = f.read()

    # ۱. اصلاح ایمپورت در خطوط اولیه
    old_import = "from PyQt5.QtCore import Qt"
    new_import = "from PyQt5.QtCore import Qt, QObject, QEvent"
    if old_import in code and "QObject" not in code:
        code = code.replace(old_import, new_import, 1)
        print("✓ مرحله ۱: ایمپورت QObject و QEvent اضافه شد.")

    # ۲. افزودن فیلتر هوشمند هدایت چرخ موس به فرم‌ها
    wheel_class_code = '''
class _WheelForward(QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() != QEvent.Wheel:
                return False
            w = obj
            if not isinstance(w, QWidget) or isinstance(w, QScrollArea):
                return False
            # اگر خود کنترل اسکرول داخلی دارد (مثل جداول پرینت یا ادیتور بزرگ)، مداخله نکن
            try:
                v = w.verticalScrollBar() if hasattr(w, 'verticalScrollBar') else None
                if v is not None and v.minimum() != v.maximum():
                    return False
            except Exception:
                pass

            p = w.parentWidget()
            while p is not None and not isinstance(p, QScrollArea):
                p = p.parentWidget()
            if p is None:
                return False
            
            sb = p.verticalScrollBar()
            if sb and sb.isVisible():
                delta = ev.angleDelta().y()
                step = sb.singleStep() or 30
                if delta < 0:
                    sb.setValue(sb.value() + step)
                elif delta > 0:
                    sb.setValue(sb.value() - step)
                return True
        except Exception:
            pass
        return False

_wheel_forwarder = _WheelForward()
'''

    marker_fit = "def _safe_fit(w):"
    if "_WheelForward" not in code and marker_fit in code:
        code = code.replace(marker_fit, wheel_class_code + "\n" + marker_fit, 1)
        print("✓ مرحله ۲: کلاس _WheelForward با موفقیت ثبت شد.")

    # ۳. فعال‌سازی فیلتر در نمونه QApplication
    marker_app = "app = QApplication(sys.argv)"
    app_patch = """app = QApplication(sys.argv)
    try:
        app.installEventFilter(_wheel_forwarder)
    except Exception:
        pass"""
    if marker_app in code and "installEventFilter(_wheel_forwarder)" not in code:
        code = code.replace(marker_app, app_patch, 1)
        print("✓ مرحله ۳: رویداد چرخ موس به اپلیکیشن متصل شد.")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(code)

    py_compile.compile(TARGET, doraise=True)
    print("✓ کامپایل main.py با موفقیت انجام شد و خطایی وجود ندارد.")

except Exception as e:
    print(f"خطا در اعمال پچ: {e}")
    sys.exit(1)
