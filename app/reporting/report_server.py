import threading
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from app.core.database import DatabaseManager
from app.repositories.report_repository import ReportRepository
from app.services.report_export_service import build_aggregate_stock_html, build_kardex_html, build_stock_value_html

_HOST = '127.0.0.1'
_PORT = 5057
_server_thread: Optional[threading.Thread] = None
_server_started = False
_server_lock = threading.Lock()


def _create_flask_app(db_path: Path):
    try:
        from flask import Flask, abort, request
    except Exception as exc:  # pragma: no cover
        raise RuntimeError('Flask is not installed. Please run: pip install -r requirements.txt') from exc

    app = Flask(__name__)
    app.config['DB_PATH'] = str(db_path)

    @app.get('/reports/stock-value')
    def stock_value_report():
        warehouse_id = request.args.get('warehouse_id', type=int)
        if not warehouse_id:
            abort(400, 'warehouse_id is required')
        repository = ReportRepository(DatabaseManager(Path(app.config['DB_PATH'])))
        report = repository.get_warehouse_stock_value_report(warehouse_id)
        return build_stock_value_html(report)

    @app.get('/reports/kardex')
    def kardex_report():
        warehouse_id = request.args.get('warehouse_id', type=int)
        pallet_id = request.args.get('pallet_id', type=int)
        if not warehouse_id:
            abort(400, 'warehouse_id is required')
        repository = ReportRepository(DatabaseManager(Path(app.config['DB_PATH'])))
        report = repository.get_inventory_kardex_report(warehouse_id, pallet_id)
        return build_kardex_html(report)

    @app.get('/reports/aggregate-stock')
    def aggregate_stock_report():
        repository = ReportRepository(DatabaseManager(Path(app.config['DB_PATH'])))
        report = repository.get_all_warehouses_stock_value_report()
        return build_aggregate_stock_html(report)

    return app


def ensure_report_server_running(db_path: Path) -> str:
    global _server_started, _server_thread
    with _server_lock:
        if _server_started:
            return f'http://{_HOST}:{_PORT}'

        app = _create_flask_app(db_path)

        def run_server():
            app.run(host=_HOST, port=_PORT, debug=False, use_reloader=False)

        _server_thread = threading.Thread(target=run_server, daemon=True)
        _server_thread.start()
        _server_started = True
        return f'http://{_HOST}:{_PORT}'


def open_stock_value_report(db_path: Path, warehouse_id: int) -> str:
    base_url = ensure_report_server_running(db_path)
    url = f"{base_url}/reports/stock-value?{urlencode({'warehouse_id': warehouse_id})}"
    webbrowser.open(url)
    return url


def open_kardex_report(db_path: Path, warehouse_id: int, pallet_id: Optional[int] = None) -> str:
    base_url = ensure_report_server_running(db_path)
    params = {'warehouse_id': warehouse_id}
    if pallet_id is not None:
        params['pallet_id'] = pallet_id
    url = f"{base_url}/reports/kardex?{urlencode(params)}"
    webbrowser.open(url)
    return url


def open_aggregate_stock_report(db_path: Path) -> str:
    base_url = ensure_report_server_running(db_path)
    url = f"{base_url}/reports/aggregate-stock"
    webbrowser.open(url)
    return url
