import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, amount, cents, operationKey, stored } from '../api';
import '../styles.css';

interface Service { ID_General?: string; ID_Dental?: string; 'Categoría': string; 'Nombre Específico': string; 'Precio Unitario': string; Descuento: string; }
interface CartItem { lineId: string; id: string; nombre: string; cantidad: number; price: number; discount: number; }
interface Payment { metodo: string; monto: string; }
interface Draft { nombre: string; dni: string; destino: 'general' | 'dental'; items: CartItem[]; pagos: Payment[]; observaciones: string; activo: boolean; tipo: 'percent' | 'fixed'; valor: string; razon: string; }
interface Pending { key: string; body: string; }
const EMPTY: Draft = { nombre: '', dni: '', destino: 'general', items: [], pagos: [], observaciones: '', activo: false, tipo: 'percent', valor: '', razon: '' };
const METHODS = ['Efectivo', 'Yape', 'Plin', 'Tarjeta', 'Transferencia'];

const ServiceForm: React.FC<{ prefilledPatient?: { nombre: string; dni: string } | null; onPatientLoaded?: () => void }> = ({ prefilledPatient, onPatientLoaded }) => {
  const [draft, setDraft] = useState<Draft>(() => stored('ticket-draft-v2', EMPTY));
  const [pending, setPending] = useState<Pending | null>(() => stored('ticket-pending-v2', null));
  const [catalogs, setCatalogs] = useState<{ general: Service[]; dental: Service[] }>({ general: [], dental: [] });
  const [category, setCategory] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [customName, setCustomName] = useState('');
  const [customPrice, setCustomPrice] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const sending = useRef(false);
  const update = (value: Partial<Draft>) => setDraft(previous => ({ ...previous, ...value }));
  const locked = busy || pending !== null;
  const loadCatalogs = useCallback(() => api<{ general: Service[]; dental: Service[] }>('/api/catalogos').then(setCatalogs).catch(error => setMessage(error.message)), []);
  useEffect(() => { void loadCatalogs(); }, [loadCatalogs]);
  useEffect(() => { sessionStorage.setItem('ticket-draft-v2', JSON.stringify(draft)); }, [draft]);
  useEffect(() => {
    if (prefilledPatient && !pending) {
      setDraft(previous => ({ ...previous, ...prefilledPatient }));
      onPatientLoaded?.();
    }
  }, [prefilledPatient, pending, onPatientLoaded]);
  const services = catalogs[draft.destino];
  const categories = Array.from(new Set([...services.map(s => s.Categoría), 'OTROS']));
  const subtotal = draft.items.reduce((sum, item) => sum + (item.price - item.discount) * item.cantidad, 0);
  const discount = draft.activo ? (draft.tipo === 'percent' ? Math.round(subtotal * cents(draft.valor) / 10000) : cents(draft.valor)) : 0;
  const total = Math.max(0, subtotal - discount);
  const received = draft.pagos.reduce((sum, p) => sum + cents(p.monto), 0);
  const change = Math.max(0, received - total);
  const cash = draft.pagos.filter(p => p.metodo === 'Efectivo').reduce((sum, p) => sum + cents(p.monto), 0);

  const addItem = () => {
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 999) { setMessage('La cantidad debe ser un entero entre 1 y 999.'); return; }
    const service = services.find(s => (s.ID_General || s.ID_Dental) === serviceId);
    if (category === 'OTROS' && (!customName.trim() || customPrice === '' || Number(customPrice) < 0)) { setMessage('Ingrese concepto y precio válido.'); return; }
    if (category !== 'OTROS' && !service) return;
    const item: CartItem = { lineId: operationKey(), id: service ? (service.ID_General || service.ID_Dental)! : 'OTROS',
      nombre: service ? service['Nombre Específico'] : customName.trim().toUpperCase(), cantidad: quantity,
      price: cents(service ? service['Precio Unitario'] : customPrice), discount: service ? cents(service.Descuento || 0) : 0 };
    update({ items: [...draft.items, item] });
    setQuantity(1); setServiceId(''); setCustomName(''); setCustomPrice(''); setMessage('');
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (sending.current) return;
    if (!pending && (!draft.items.length || received < total || change > cash || discount > subtotal)) { setMessage('Revise servicios, descuento y pagos. El vuelto debe estar cubierto por efectivo.'); return; }
    let operation = pending;
    if (!operation) {
      operation = { key: operationKey(), body: JSON.stringify({ paciente: { nombre: draft.nombre, dni: draft.dni },
        destino: draft.destino, items: draft.items.map(i => ({ id: i.id, nombre: i.nombre, cantidad: i.cantidad, precio_unitario: amount(i.price) })),
        desglose_pagos: draft.pagos.map(p => ({ metodo: p.metodo, monto: amount(cents(p.monto)) })),
        descuento_especial_activo: draft.activo, descuento_especial_tipo: draft.tipo, descuento_especial_valor: draft.valor || '0',
        descuento_especial_razon: draft.razon, observaciones: draft.observaciones, total_esperado: amount(total) }) };
      // Persist the exact request BEFORE sending. A network retry uses the same operation and body.
      sessionStorage.setItem('ticket-pending-v2', JSON.stringify(operation));
      setPending(operation);
    }
    sending.current = true; setBusy(true);
    try {
      const result = await api<{ message: string; ticket_id: string; total_final: string }>('/api/registrar-venta', {
        method: 'POST', headers: { 'Idempotency-Key': operation.key }, body: operation.body });
      sessionStorage.removeItem('ticket-pending-v2'); setPending(null);
      setDraft({ ...EMPTY, items: [], pagos: [] });
      setMessage(`Ticket ${result.ticket_id} registrado por S/. ${result.total_final}. ${result.message}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        sessionStorage.removeItem('ticket-pending-v2'); setPending(null);
        setMessage(error.message);
      } else {
        setMessage(`${error instanceof Error ? error.message : 'Error de conexión.'} Reintente esta misma operación; no vuelva a cobrar.`);
      }
    } finally { sending.current = false; setBusy(false); }
  };
  return <div className="form-container">
    {message && <p role="status" className="status-message">{message}</p>}
    {pending && <p role="alert">Hay una operación pendiente de confirmación. Reintente para recuperar su resultado sin duplicarla.</p>}
    <form onSubmit={submit}>
      <fieldset disabled={locked} className="patient-fields"><legend>Datos del paciente</legend>
        <label className="patient-field"><span>Nombre</span><input type="text" autoComplete="name" required maxLength={200} value={draft.nombre} onChange={e => update({ nombre: e.target.value.toUpperCase() })}/></label>
        <label className="patient-field"><span>DNI</span><input type="text" inputMode="numeric" autoComplete="off" required pattern="[0-9]{8}" maxLength={8} value={draft.dni} onChange={e => update({ dni: e.target.value.replace(/\D/g, '') })}/></label>
      </fieldset>
      <fieldset disabled={locked}><legend>Añadir servicio</legend>
        <label>Destino<select disabled={draft.items.length > 0} value={draft.destino} onChange={e => { update({ destino: e.target.value as Draft['destino'] }); setCategory(''); setServiceId(''); }}><option value="general">Las Marianas</option><option value="dental">Dental</option></select></label>
        <label>Categoría<select value={category} onChange={e => { setCategory(e.target.value); setServiceId(''); }}><option value="">Seleccione…</option>{categories.map(c => <option key={c}>{c}</option>)}</select></label>
        {category === 'OTROS' ? <><label>Concepto<input maxLength={200} value={customName} onChange={e => setCustomName(e.target.value)}/></label><label>Precio<input type="number" min="0" step="0.01" value={customPrice} onChange={e => setCustomPrice(e.target.value)}/></label></> :
          <label>Servicio<select value={serviceId} onChange={e => setServiceId(e.target.value)}><option value="">Seleccione…</option>{services.filter(s => s.Categoría === category).map(s => <option key={s.ID_General || s.ID_Dental} value={s.ID_General || s.ID_Dental}>{s['Nombre Específico']}</option>)}</select></label>}
        <label>Cantidad<input type="number" min="1" max="999" step="1" value={quantity} onChange={e => setQuantity(Number(e.target.value))}/></label>
        <button type="button" onClick={addItem}>Añadir</button>{' '}<button type="button" onClick={loadCatalogs}>Actualizar catálogo</button>
      </fieldset>
      <fieldset disabled={locked}><legend>Resumen y descuento</legend>
        <div className="table-scroll"><table><thead><tr><th>Servicio</th><th>Cantidad</th><th>Total</th><th>Acción</th></tr></thead><tbody>{draft.items.map(i => <tr key={i.lineId}><td>{i.nombre}</td><td>{i.cantidad}</td><td>S/. {amount((i.price - i.discount) * i.cantidad)}</td><td><button type="button" aria-label={`Quitar ${i.nombre}`} onClick={() => update({ items: draft.items.filter(x => x.lineId !== i.lineId) })}>Quitar</button></td></tr>)}</tbody></table></div>
        <label><input type="checkbox" checked={draft.activo} onChange={e => update({ activo: e.target.checked })}/> Descuento especial</label>
        {draft.activo && <><label>Tipo<select value={draft.tipo} onChange={e => update({ tipo: e.target.value as Draft['tipo'] })}><option value="percent">Porcentaje</option><option value="fixed">Monto en soles</option></select></label><label>Valor<input type="number" min="0" max={draft.tipo === 'percent' ? 100 : amount(subtotal)} step="0.01" required value={draft.valor} onChange={e => update({ valor: e.target.value })}/></label><label>Motivo<input required maxLength={300} value={draft.razon} onChange={e => update({ razon: e.target.value })}/></label></>}
        <p>Subtotal: S/. {amount(subtotal)} · Descuento: S/. {amount(discount)}</p><h3>Total: S/. {amount(total)}</h3>
        <label>Observaciones<textarea maxLength={2000} rows={3} className="observaciones-input" value={draft.observaciones} onChange={e => update({ observaciones: e.target.value })}/></label>
      </fieldset>
      <fieldset disabled={locked}><legend>Pagos</legend>
        <label>Método<select value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)}><option value="">Seleccione…</option>{METHODS.filter(m => !draft.pagos.some(p => p.metodo === m)).map(m => <option key={m}>{m}</option>)}</select></label>
        <button type="button" disabled={!paymentMethod} onClick={() => { update({ pagos: [...draft.pagos, { metodo: paymentMethod, monto: amount(Math.max(0, total - received)) }] }); setPaymentMethod(''); }}>Añadir pago</button>
        {draft.pagos.map((p, index) => <div key={p.metodo} className="payment-row"><label>{p.metodo}<input required type="number" min="0.01" step="0.01" value={p.monto} onChange={e => update({ pagos: draft.pagos.map((x, n) => n === index ? { ...x, monto: e.target.value } : x) })}/></label><button type="button" onClick={() => update({ pagos: draft.pagos.filter((_, n) => n !== index) })}>Quitar</button></div>)}
        <p>Recibido: S/. {amount(received)} · Falta: S/. {amount(Math.max(0, total - received))} · Vuelto: S/. {amount(change)}</p>
        {change > cash && <p role="alert">El vuelto supera el efectivo recibido. Revise los pagos.</p>}
      </fieldset>
      <div className="form-actions"><button type="button" disabled={locked} onClick={() => { if (window.confirm('¿Descartar el borrador?')) { setDraft({ ...EMPTY, items: [], pagos: [] }); setCategory(''); setServiceId(''); } }}>Descartar borrador</button>
        <button type="submit" disabled={busy || (!pending && (!draft.items.length || received < total || change > cash || discount > subtotal))}>{busy ? 'Registrando…' : pending ? 'Reintentar operación pendiente' : 'Registrar e imprimir'}</button></div>
    </form>
  </div>;
};
export default ServiceForm;
