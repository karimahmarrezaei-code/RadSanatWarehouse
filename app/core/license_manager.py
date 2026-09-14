# -*- coding: utf-8 -*-
import os, json, base64, hmac, hashlib, uuid, platform
from datetime import date, timedelta

SECRET = base64.b64decode('UmFkU2FuYXROb3ZpbkxpY2Vuc2VLZXkxNDA1').decode()

def _lic_path():
    from app.core.config import DB_PATH
    base = os.path.dirname(os.path.dirname(os.path.abspath(str(DB_PATH))))
    return os.path.join(base, 'data', 'license.key')

def _hidden_path():
    return os.path.join(os.path.expanduser('~'), '.rsn_license_ts')

def machine_fingerprint():
    parts = [uuid.getnode(), platform.node(), platform.processor() or platform.machine()]
    try:
        import subprocess
        out = subprocess.check_output('wmic diskdrive get serialnumber', shell=True, stderr=subprocess.DEVNULL).decode()
        parts.append(out.strip())
    except Exception:
        pass
    return hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:32]

def _sign(b):
    return hmac.new(SECRET.encode(), b.encode(), hashlib.sha256).hexdigest()

def make_code(company, start_iso, end_iso, machine='', ltype='full'):
    payload = {'c': company, 's': start_iso, 'e': end_iso, 'm': machine, 't': ltype, 'n': uuid.uuid4().hex[:8]}
    b = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()
    return b + '.' + _sign(b)

def parse_code(code):
    try:
        b, sig = code.strip().split('.', 1)
        if not hmac.compare_digest(_sign(b), sig):
            return None
        return json.loads(base64.urlsafe_b64decode(b.encode()).decode())
    except Exception:
        return None

def _read_hidden():
    try:
        with open(_hidden_path()) as f:
            return base64.b64decode(f.read().strip()).decode()
    except Exception:
        return '1970-01-01'

def _write_hidden(iso):
    try:
        with open(_hidden_path(), 'w') as f:
            f.write(base64.b64encode(iso.encode()).decode())
    except Exception:
        pass

def _now_iso():
    return max(date.today().isoformat(), _read_hidden())

def save_license(code):
    with open(_lic_path(), 'w', encoding='utf-8') as f:
        f.write(code)

def load_license():
    try:
        with open(_lic_path(), encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def check():
    code = load_license()
    if not code:
        return None
    p = parse_code(code)
    if not p:
        return None
    if p.get('m') and p['m'] != machine_fingerprint():
        return None
    now = _now_iso(); _write_hidden(now)
    return {'valid': (p['s'] <= now <= p['e']), 'payload': p, 'now': now}

def start_demo():
    t = date.today()
    code = make_code('دمو', t.isoformat(), (t + timedelta(days=7)).isoformat(), machine=machine_fingerprint(), ltype='demo')
    save_license(code); _write_hidden(t.isoformat())
    return code

def ensure_license(qapp):
    while True:
        st = check()
        if st and st['valid']:
            return True
        from app.ui.license_activation_dialog import LicenseActivationDialog
        dlg = LicenseActivationDialog(None, expired=bool(st))
        dlg.exec_()
        if dlg.action == 'exit':
            return False
        if dlg.action == 'demo':
            start_demo()
