"""مقیاس خودکار فقط برای صفحه‌های کوچک - SCREEN-FIT"""
import os, sys
def apply():
    try:
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sf = None
        p = os.path.join(base, "scale.txt")
        if os.path.exists(p):
            sf = open(p, encoding="utf-8").read().strip() or None
        if not sf:
            import ctypes
            w = ctypes.windll.user32.GetSystemMetrics(0)
            if w and w < 1600:
                sf = str(round(max(0.62, w / 1920.0), 2))
        if sf:
            os.environ["QT_SCALE_FACTOR"] = sf
        return sf
    except Exception:
        return None
