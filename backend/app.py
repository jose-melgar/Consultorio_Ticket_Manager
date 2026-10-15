"""Local single-operator API. Importing this module never migrates live data."""
import atexit
import logging
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from catalog_manager import CatalogError, cargar_catalogos
from jobs import JobWorker
from models import ValidationError, build_sale, now, quantity, text
from receipt import clinic
from storage import ConflictError, StorageError, Store, request_hash

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

def create_app(config=None):
    app = Flask(__name__, static_folder='build', static_url_path='/')
    app.config.update(DATA_DIR=os.getenv('CONSULTORIO_DATA_DIR', str(ROOT / 'data')),
                      TICKETS_DIR=os.getenv('CONSULTORIO_TICKETS_DIR', str(ROOT / 'Tickets')),
                      START_WORKER=True, AUTO_BACKUP=True, PRINT_COPIES=2,
                      MAX_CONTENT_LENGTH=256 * 1024, DEVELOPMENT_ORIGIN=os.getenv('CONSULTORIO_DEV_ORIGIN'))
    if config:
        app.config.update(config)
    store = Store(app.config['DATA_DIR'], app.config['TICKETS_DIR'])
    worker = JobWorker(store, app.config.get('PRINTER'))
    app.extensions.update(store=store, worker=worker)
    ready_lock = threading.Lock()
    prepared = False

    def prepare():
        nonlocal prepared
        with ready_lock:
            if prepared:
                return
            cargar_catalogos(store.data_dir)
            store.initialize()
            if app.config['AUTO_BACKUP']:
                destination = store.data_dir / 'backups' / ('daily-' + now().strftime('%Y%m%d'))
                if not (destination / 'BACKUP_COMPLETE').exists():
                    # A failed/incomplete backup is never silently considered successful.
                    if destination.exists():
                        destination = destination.with_name(destination.name + '-' + uuid.uuid4().hex[:8])
                    store.backup(destination)
            if app.config['START_WORKER']:
                worker.start()
                atexit.register(worker.stop)
            prepared = True
    app.extensions['prepare'] = prepare

    @app.before_request
    def protect_local_api():
        if request.path.startswith('/api/'):
            if urlsplit('http://' + request.host).hostname not in ('localhost', '127.0.0.1', '[::1]', '::1'):
                return jsonify(error='Acceso permitido únicamente desde este equipo.'), 403
            origin = request.headers.get('Origin')
            if origin and origin not in (request.host_url.rstrip('/'), app.config['DEVELOPMENT_ORIGIN']):
                return jsonify(error='Origen de solicitud no permitido.'), 403
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                if request.headers.get('X-Local-Request') != '1':
                    return jsonify(error='Solicitud local inválida. Actualice la interfaz.'), 403
            prepare()

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        if request.path.startswith('/api/') or request.path == '/':
            response.headers['Cache-Control'] = 'no-store'
        return response

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError('Se requiere un objeto JSON válido.')
        return data

    @app.errorhandler(ValidationError)
    def invalid(exc):
        return jsonify(error=str(exc)), 409 if isinstance(exc, ConflictError) else 422

    @app.errorhandler(CatalogError)
    @app.errorhandler(StorageError)
    def unavailable(exc):
        app.logger.error('Local data unavailable (%s)', type(exc).__name__)
        return jsonify(error=str(exc)), 503

    @app.errorhandler(Exception)
    def unexpected(exc):
        if isinstance(exc, HTTPException):
            return jsonify(error=exc.description), exc.code
        error_id = uuid.uuid4().hex[:12]
        app.logger.error('Operation %s failed (%s)', error_id, type(exc).__name__)
        return jsonify(error=f'No se pudo completar la operación. Referencia: {error_id}.'), 500

    @app.get('/api/health')
    def health():
        return jsonify(status='ok', application='consultorio-ticket-manager', storage='sqlite', version=2)

    @app.get('/api/catalogos')
    def catalogs():
        return jsonify(cargar_catalogos(store.data_dir))

    @app.get('/api/configuracion')
    def configuration():
        return jsonify(clinic())

    @app.get('/api/tickets')
    def history():
        # Keep the existing response shape for compatibility; filtering is also available.
        sales = store.history()
        query = request.args.get('q', '').strip().casefold()
        if query:
            sales = [s for s in sales if query in (s['id_ticket_global'] + ' ' + s['paciente'].get('nombre', '') + ' ' + s['paciente'].get('dni', '')).casefold()]
        return jsonify(sales)

    @app.post('/api/registrar-venta')
    def register():
        data = body()
        key = text(request.headers.get('Idempotency-Key'), 'Clave de operación', 80)
        try:
            uuid.UUID(key)
        except ValueError:
            raise ValidationError('Clave de operación inválida.') from None
        fingerprint = request_hash(data)
        # Look up before catalog validation: a retry must survive later price changes.
        sale = store.existing(key, fingerprint)
        replay = sale is not None
        if sale is None:
            sale, created = store.register(build_sale(data, cargar_catalogos(store.data_dir)), key, fingerprint,
                                           quantity(app.config['PRINT_COPIES'], 5))
            replay = not created
        worker.notify()
        return jsonify(message='Venta registrada. Consulte el estado de documentos e impresión en el historial.',
                       ticket_id=sale['id_ticket_global'], total_final=sale['total_final'],
                       path=sale['id_ticket_global'] + '.pdf', replayed=replay,
                       jobs=store.jobs(sale['id_ticket_global']))

    @app.delete('/api/eliminar-ticket/<ident>')
    def cancel(ident):
        reason = text(body().get('motivo'), 'Motivo de anulación', 300)
        if not store.cancel(ident, reason):
            return jsonify(error='Ticket no encontrado.'), 404
        worker.notify()
        return jsonify(message='Ticket anulado; la actualización de Excel se ha encolado.', jobs=store.jobs(ident))

    @app.get('/api/tickets/<ident>/estado')
    def status(ident):
        if store.get(ident) is None:
            return jsonify(error='Ticket no encontrado.'), 404
        return jsonify(jobs=store.jobs(ident))

    @app.post('/api/tickets/<ident>/reintentar-documentos')
    def retry(ident):
        if store.get(ident) is None:
            return jsonify(error='Ticket no encontrado.'), 404
        store.retry_documents(ident)
        worker.notify()
        return jsonify(message='Documentos pendientes de actualización.')

    @app.post('/api/reimprimir-ticket')
    def reprint():
        data = body()
        ident = text(data.get('id_ticket_global'), 'Ticket', 80)
        copies = quantity(data.get('cantidad', 1), 5)
        sale = store.get(ident)
        if sale is None:
            return jsonify(error='Ticket no encontrado.'), 404
        if sale.get('habilitado') is False:
            raise ValidationError('No se puede reimprimir un ticket anulado.')
        store.queue_print(ident, copies)
        worker.notify()
        return jsonify(message='Reimpresión encolada. Consulte su estado en el historial.')

    @app.get('/api/tickets/<ident>/pdf')
    def pdf(ident):
        if store.get(ident) is None:
            return jsonify(error='Ticket no encontrado.'), 404
        return send_from_directory(store.tickets_dir, ident + '.pdf', mimetype='application/pdf')

    @app.get('/')
    def index():
        if not (Path(app.static_folder) / 'index.html').exists():
            return 'Falta compilar la interfaz. Consulte docs/README.md.', 503
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/<path:path>')
    def static_or_index(path):
        if path.startswith('api/'):
            return jsonify(error='Endpoint no encontrado.'), 404
        candidate = (Path(app.static_folder) / path).resolve()
        if candidate.is_relative_to(Path(app.static_folder).resolve()) and candidate.is_file():
            return send_from_directory(app.static_folder, path)
        if '.' in path:
            return '', 404
        return index()
    return app

app = create_app()

if __name__ == '__main__':
    import argparse
    import socket
    import sys
    from waitress import create_server
    parser = argparse.ArgumentParser()
    parser.add_argument('--open-browser', action='store_true')
    options = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    # Bind before migration, so a second launch cannot reset in-flight jobs.
    try:
        server = create_server(app, host='127.0.0.1', port=5000, threads=4)
    except OSError:
        print('El puerto 5000 está ocupado. Cierre la otra instancia antes de iniciar.')
        sys.exit(1)
    try:
        app.extensions['prepare']()
        if options.open_browser:
            import webbrowser
            threading.Timer(1, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
        print('Sistema activo en http://127.0.0.1:5000. Use Ctrl+C para apagar.')
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.extensions['worker'].stop()
        server.close()
        server.task_dispatcher.shutdown()
