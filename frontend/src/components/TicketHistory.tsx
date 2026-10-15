import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import '../styles.css';

interface Job { id: number; kind: 'excel' | 'pdf' | 'print'; state: string; error?: string; }
interface Sale { id_ticket_global: string; id_ticket_especifico: string; fecha: string; paciente: { nombre: string; dni: string }; total_final: string; habilitado?: boolean; motivo_eliminacion?: string; observaciones?: string; metodo_pago?: string; vuelto?: string; items: { nombre: string; cantidad: number; subtotal: string }[]; }
const latestJob = (jobs: Job[], kind: Job['kind']) => [...jobs].reverse().find(job => job.kind === kind);

const ticketNotice = (jobs: Job[]): string => {
  const excel = latestJob(jobs, 'excel');
  const pdf = latestJob(jobs, 'pdf');
  const print = latestJob(jobs, 'print');
  if (excel?.state === 'failed') return 'Ticket guardado; falta actualizar el archivo contable.';
  if (pdf?.state === 'failed') return 'Ticket guardado; falta preparar su PDF.';
  if (print && ['failed', 'uncertain'].includes(print.state)) return 'Compruebe el papel antes de solicitar otra copia.';
  return '';
};

const TicketHistory: React.FC<{ onCargarPaciente?: (nombre: string, dni: string) => void }> = ({ onCargarPaciente }) => {
  const [sales, setSales] = useState<Sale[]>([]);
  const [selected, setSelected] = useState<Sale | null>(null);
  const [statuses, setStatuses] = useState<Record<string, Job[]>>({});
  const [inactive, setInactive] = useState(false);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [clinic, setClinic] = useState({ nombre: '', direccion: '', whatsapp: '' });
  const dialog = useRef<HTMLDialogElement>(null);
  const actionRunning = useRef(false);
  const load = useCallback(async () => {
    setLoading(true);
    try { setSales(await api<Sale[]>('/api/tickets')); setMessage(''); }
    catch (error) { setMessage((error as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); api<{ nombre: string; direccion: string; whatsapp: string }>('/api/configuracion').then(setClinic).catch(() => {}); }, [load]);
  useEffect(() => {
    if (selected) dialog.current?.showModal();
  }, [selected]);
  const act = async (action: () => Promise<unknown>) => {
    if (actionRunning.current) return;
    actionRunning.current = true;
    setBusy(true);
    try { const result = await action() as { message?: string }; setMessage(result.message || 'Operación completada.'); }
    catch (error) { setMessage((error as Error).message); }
    finally { actionRunning.current = false; setBusy(false); }
  };
  const cancel = (sale: Sale) => {
    const reason = window.prompt(`Motivo obligatorio para anular ${sale.id_ticket_global}:`);
    if (!reason?.trim()) return;
    void act(async () => { await api(`/api/eliminar-ticket/${sale.id_ticket_global}`, { method: 'DELETE', body: JSON.stringify({ motivo: reason }) }); await load(); return { message: 'Ticket anulado.' }; });
  };
  const reprint = (sale: Sale) => {
    if (actionRunning.current) return;
    const answer = window.prompt(`¿Cuántas copias de ${sale.id_ticket_global} desea imprimir? (1 a 5)\nCompruebe primero las copias que ya salieron.`, '1');
    if (answer === null) return;
    if (!/^[1-5]$/.test(answer.trim())) { setMessage('Ingrese un número entero entre 1 y 5 copias.'); return; }
    void act(async () => {
      await api('/api/reimprimir-ticket', { method: 'POST', body: JSON.stringify({ id_ticket_global: sale.id_ticket_global, cantidad: Number(answer.trim()) }) });
      return { message: 'Se solicitó la impresión. Compruebe la salida del papel.' };
    });
  };
  const retryFile = (sale: Sale) => void act(async () => {
    await api(`/api/tickets/${sale.id_ticket_global}/reintentar-documentos`, { method: 'POST' });
    return { message: 'Se solicitó actualizar el archivo del ticket.' };
  });
  const filtered = useMemo(() => sales.filter(s => (s.habilitado === false) === inactive &&
    `${s.id_ticket_global} ${s.paciente.nombre} ${s.paciente.dni}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())).reverse(), [sales, inactive, query]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / 25));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleSales = useMemo(() => filtered.slice(currentPage * 25, (currentPage + 1) * 25), [filtered, currentPage]);
  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;
    const refresh = async () => {
      if (refreshing || controller.signal.aborted) return;
      refreshing = true;
      try {
        const updates = await Promise.all(visibleSales.map(async sale => {
          try {
            const result = await api<{ jobs: Job[] }>(`/api/tickets/${sale.id_ticket_global}/estado`, { signal: controller.signal });
            return { id: sale.id_ticket_global, jobs: result.jobs };
          } catch { return null; }
        }));
        if (!controller.signal.aborted) setStatuses(previous => {
          const next = { ...previous };
          updates.forEach(update => { if (update) next[update.id] = update.jobs; });
          return next;
        });
      } finally { refreshing = false; }
    };
    void refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [visibleSales]);
  return <div className="history-container"><h2>Historial de tickets</h2>
    {message && <p role="status" className="status-message">{message}</p>}
    <div className="form-actions history-toolbar"><button aria-pressed={!inactive} onClick={() => { setInactive(false); setPage(0); }}>Activos</button><button aria-pressed={inactive} onClick={() => { setInactive(true); setPage(0); }}>Anulados</button><button onClick={load} disabled={loading}>Actualizar</button></div>
    <label className="history-search"><span>Buscar ticket, nombre o DNI</span><input type="text" value={query} onChange={e => { setQuery(e.target.value); setPage(0); }}/></label>
    {loading ? <p role="status">Cargando historial…</p> : <><div className="table-scroll"><table className="history-table"><thead><tr><th>Ticket</th><th>Operación</th><th>Fecha</th><th>Paciente</th><th>Total</th><th>Acciones</th></tr></thead>
      <tbody>{visibleSales.map(sale => {
        const jobs = statuses[sale.id_ticket_global] || [];
        const pdfReady = latestJob(jobs, 'pdf')?.state === 'sent';
        const printPending = jobs.some(job => job.kind === 'print' && ['pending', 'running'].includes(job.state));
        const canRetry = jobs.some(job => job.kind !== 'print' && job.state === 'failed');
        const notice = ticketNotice(jobs);
        return <tr key={sale.id_ticket_global}>
          <td className="ticket-id"><button className="ticket-link" title="Ver ticket" onClick={() => setSelected(sale)}>{sale.id_ticket_global}</button></td>
          <td className="ticket-operation">{sale.id_ticket_especifico}</td><td>{sale.fecha}</td><td>{sale.paciente.nombre}</td>
          <td className="ticket-total">S/. {Number(sale.total_final).toFixed(2)}</td>
          <td><div className="ticket-actions">
            {sale.habilitado !== false && <button type="button" className="icon-button" title="Cargar paciente" aria-label="Cargar paciente" disabled={busy || !onCargarPaciente} onClick={() => onCargarPaciente?.(sale.paciente.nombre, sale.paciente.dni)}>👤</button>}
            {pdfReady ? <a className="icon-button" title="Abrir PDF" aria-label="Abrir PDF" target="_blank" rel="noreferrer" href={`/api/tickets/${sale.id_ticket_global}/pdf`}>📄</a> : <button type="button" className="icon-button" title="PDF todavía no disponible" aria-label="PDF todavía no disponible" disabled>📄</button>}
            {sale.habilitado !== false && <><button type="button" className="icon-button" title={printPending ? 'Impresión en curso' : 'Imprimir copias'} aria-label="Imprimir copias" disabled={busy || printPending} onClick={() => reprint(sale)}>🖨️</button><button type="button" className="icon-button cancel-button" title="Anular ticket" aria-label="Anular ticket" disabled={busy} onClick={() => cancel(sale)}>❌</button></>}
            {canRetry && <button type="button" className="icon-button" title="Reintentar actualización del archivo" aria-label="Reintentar actualización del archivo" disabled={busy} onClick={() => retryFile(sale)}>🔄</button>}
          </div>{notice && <p className="ticket-notice" role="status">{notice}</p>}{sale.habilitado === false && <p className="ticket-notice">{sale.motivo_eliminacion}</p>}</td>
        </tr>;
      })}
      {!filtered.length && <tr><td colSpan={6}>No hay tickets para estos filtros.</td></tr>}</tbody></table></div>
      <div className="form-actions history-pagination"><button disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Anterior</button><span>Página {currentPage + 1} de {pageCount}</span><button disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Siguiente</button></div></>}
    {selected && <dialog ref={dialog} className="ticket-dialog" aria-labelledby="ticket-dialog-title" onCancel={() => setSelected(null)} onClose={() => setSelected(null)}>
      <div className="ticket-dialog-header"><h3 id="ticket-dialog-title">{selected.habilitado === false ? 'Ticket anulado' : 'Ticket'} {selected.id_ticket_global}</h3><button className="close-dialog" onClick={() => { dialog.current?.close(); setSelected(null); }} aria-label="Cerrar ticket">Cerrar</button></div>
      <p>{clinic.nombre}<br/>{clinic.direccion}<br/>WhatsApp: {clinic.whatsapp}</p>
      <p>{selected.fecha}<br/>{selected.paciente.nombre}<br/>DNI: {selected.paciente.dni}</p>
      {selected.items?.map((item, index) => <p key={index}>{item.nombre}<br/>Cantidad: {item.cantidad} · S/. {Number(item.subtotal).toFixed(2)}</p>)}
      <h3 className="ticket-summary-total">Total: S/. {Number(selected.total_final).toFixed(2)}</h3><p>{selected.metodo_pago}</p>
      {selected.vuelto && <p>Vuelto: S/. {Number(selected.vuelto).toFixed(2)}</p>}
      {selected.observaciones && <p className="preserve-text">Observaciones: {selected.observaciones}</p>}
      {selected.motivo_eliminacion && <p>Motivo de anulación: {selected.motivo_eliminacion}</p>}
    </dialog>}
  </div>;
};
export default TicketHistory;
