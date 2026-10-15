"""Durable, single-worker document/print queue; no automatic print retries."""
import logging
import threading
from pathlib import Path

from catalog_manager import CatalogError, atomic_bytes, sync_accounting
from escpos_printer import imprimir_ticket_escpos
from pdf_generator import generar_ticket_pdf

logger = logging.getLogger(__name__)
logging.getLogger('fontTools.subset').setLevel(logging.WARNING)


class JobWorker:
    def __init__(self, store, printer=None):
        self.store = store
        self.printer = printer or imprimir_ticket_escpos
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._process_lock = threading.Lock()

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name='ticket-documents', daemon=True)
            self._thread.start()

    def notify(self):
        self._wake.set()

    def stop(self):
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=10)

    def process_one(self):
        with self._process_lock:
            job = self.store.claim_job()
            if not job:
                return False
            try:
                sale = self.store.get(job['ticket_id'])
                if job['kind'] == 'excel':
                    sync_accounting(self.store.data_dir, sale)
                elif job['kind'] == 'pdf':
                    atomic_bytes(Path(self.store.tickets_dir) / f"{sale['id_ticket_global']}.pdf", generar_ticket_pdf(sale))
                elif sale.get('habilitado') is False:
                    raise RuntimeError('Ticket anulado; no se imprimió.')
                elif not self.printer(sale):
                    raise RuntimeError('La impresora no confirmó el envío.')
                self.store.finish_job(job, True)
            except Exception as exc:
                # Keep diagnostics free of patient information and local paths.
                logger.error('Document job %s failed (%s)', job['id'], type(exc).__name__)
                message = {'excel': 'El ticket está guardado, pero falta actualizar el archivo contable. Reintente la actualización.',
                           'pdf': 'No se pudo generar el PDF. Reintente los documentos.',
                           'print': 'No se confirmó la impresión. Compruebe el papel antes de reimprimir.'}[job['kind']]
                if job['kind'] == 'excel' and isinstance(exc, CatalogError):
                    message = str(exc)
                    logger.error('Accounting job %s: %s', job['id'], message)
                elif job['kind'] == 'excel' and isinstance(exc, PermissionError):
                    message = 'El ticket está guardado. Cierre el archivo contable en Excel y reintente la actualización.'
                self.store.finish_job(job, False, message)
            return True

    def _run(self):
        while not self._stop.is_set():
            try:
                if self.process_one():
                    continue
            except Exception as exc:
                logger.error('Queue unavailable (%s)', type(exc).__name__)
            self._wake.wait(1)
            self._wake.clear()
