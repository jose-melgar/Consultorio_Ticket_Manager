import React, { useState, useEffect, useMemo } from 'react';
import '../styles.css';

interface ServicioAPI {
  "ID_General"?: string;
  "ID_Dental"?: string;
  "Categoría": string;
  "Nombre Específico": string;
  "Precio Unitario": number;
}

interface TicketItem {
  id: string;
  nombre: string;
  cantidad: number;
  precioUnitario: number;
  subtotal: number;
}

// Interfaz para la lista dinámica de pagos (Boceto de José)
interface PagoMetodo {
  metodo: string;
  monto: number;
}

const ServiceForm: React.FC = () => {
  const [patientName, setPatientName] = useState('');
  const [patientDNI, setPatientDNI] = useState('');
  const [catalogos, setCatalogos] = useState<{ general: ServicioAPI[], dental: ServicioAPI[] }>({ general: [], dental: [] });
  const [selectedDestino, setSelectedDestino] = useState<'general' | 'dental'>('general');
  const [selectedCategoria, setSelectedCategoria] = useState('');
  const [selectedServicio, setSelectedServicio] = useState('');
  const [cantidad, setCantidad] = useState<number>(1);
  const [ticketItems, setTicketItems] = useState<TicketItem[]>([]);
  const [observaciones, setObservaciones] = useState('');

  // --- NUEVOS ESTADOS PARA CONCEPTO "OTROS" ---
  const [customNombre, setCustomNombre] = useState('');
  const [customPrecio, setCustomPrecio] = useState<number | ''>('');

  const [hasSpecialDiscount, setHasSpecialDiscount] = useState(false);
  const [specialDiscountType, setSpecialDiscountType] = useState<'percent' | 'fixed'>('percent');
  const [specialDiscountValue, setSpecialDiscountValue] = useState<number | ''>('');
  const [specialDiscountReason, setSpecialDiscountReason] = useState('');

  // --- ESTADOS PARA MÚLTIPLES MÉTODOS DE PAGO (BOCETO DE JOSÉ) ---
  const [metodoSeleccionado, setMetodoSeleccionado] = useState('');
  const [listaPagos, setListaPagos] = useState<PagoMetodo[]>([]);

  useEffect(() => {
    fetch('http://localhost:5000/api/catalogos')
      .then(response => response.json())
      .then(data => setCatalogos(data))
      .catch(err => console.error("Error al cargar catalogos:", err));
  }, []);

  const { categoriasDisponibles, serviciosDisponibles, servicioSeleccionadoInfo } = useMemo(() => {
    const catalogoActual = catalogos[selectedDestino] || [];
    const categorias = [...new Set(catalogoActual.map(s => s.Categoría))];
    
    if (!categorias.includes("OTROS")) {
      categorias.push("OTROS");
    }

    const servicios = selectedCategoria ? catalogoActual.filter(s => s.Categoría === selectedCategoria) : [];
    const servicioInfo = selectedServicio ? servicios.find(s => (s["ID_General"] || s["ID_Dental"]) === selectedServicio) : undefined;
    
    return { categoriasDisponibles: categorias, serviciosDisponibles: servicios, servicioSeleccionadoInfo: servicioInfo };
  }, [selectedDestino, selectedCategoria, selectedServicio, catalogos]);

  const subtotalServicios = useMemo(() => ticketItems.reduce((acc, item) => acc + item.subtotal, 0), [ticketItems]);
  
  const totalCalculado = useMemo(() => {
    let total = subtotalServicios;
    if (hasSpecialDiscount && specialDiscountValue) {
      const val = Number(specialDiscountValue);
      if (specialDiscountType === 'percent') {
        total = subtotalServicios - (subtotalServicios * (val / 100));
      } else {
        total = subtotalServicios - val;
      }
    }
    return Math.max(0, total);
  }, [subtotalServicios, hasSpecialDiscount, specialDiscountType, specialDiscountValue]);

  // --- CÁLCULOS MATEMÁTICOS DE CAJA EN TIEMPO REAL ---
  const totalIngresado = useMemo(() => listaPagos.reduce((acc, p) => acc + p.monto, 0), [listaPagos]);
  const diferenciaCaja = useMemo(() => totalCalculado - totalIngresado, [totalCalculado, totalIngresado]);
  const vueltoEntregar = useMemo(() => Math.max(0, totalIngresado - totalCalculado), [totalIngresado, totalCalculado]);

  // Formatear la celda única del Excel automáticamente: "Yape(100), Efectivo(-50)"
  const metodoPagoExcelString = useMemo(() => {
    let base = listaPagos.map(p => `${p.metodo}(${p.monto})`).join(', ');
    if (vueltoEntregar > 0) {
      base += `, Vuelto(-${vueltoEntregar})`;
    }
    return base;
  }, [listaPagos, vueltoEntregar]);

  const handleAddPaymentMethod = () => {
    if (!metodoSeleccionado) return;
    if (listaPagos.some(p => p.metodo === metodoSeleccionado)) {
      alert("Este método de pago ya está en la lista. Modifique su monto directamente.");
      return;
    }
    // Sugerir automáticamente el saldo restante que falta cobrar
    const restante = Math.max(0, diferenciaCaja);
    setListaPagos([...listaPagos, { metodo: metodoSeleccionado, monto: restante }]);
    setMetodoSeleccionado('');
  };

  const handleUpdatePaymentAmount = (index: number, val: number) => {
    const nuevaLista = [...listaPagos];
    nuevaLista[index].monto = Math.max(0, val);
    setListaPagos(nuevaLista);
  };

  const handleRemovePaymentMethod = (index: number) => {
    setListaPagos(listaPagos.filter((_, i) => i !== index));
  };

  const handleAddItem = () => {
    if (selectedCategoria === "OTROS") {
      if (!customNombre.trim() || customPrecio === '' || Number(customPrecio) < 0) {
        alert("Por favor ingrese el nombre del concepto y un precio válido.");
        return;
      }
      const newItem: TicketItem = {
        id: "OTROS",
        nombre: customNombre.trim().toUpperCase(),
        cantidad: cantidad,
        precioUnitario: Number(customPrecio),
        subtotal: Number(customPrecio) * cantidad
      };
      setTicketItems(prev => [...prev, newItem]);
      setCustomNombre('');
      setCustomPrecio('');
      setSelectedCategoria('');
      setSelectedServicio('');
      setCantidad(1);
      return;
    }

    if (!servicioSeleccionadoInfo || cantidad <= 0) return;
    const newItem: TicketItem = {
      id: servicioSeleccionadoInfo["ID_General"] || servicioSeleccionadoInfo["ID_Dental"]!,
      nombre: servicioSeleccionadoInfo["Nombre Específico"],
      cantidad: cantidad,
      precioUnitario: servicioSeleccionadoInfo["Precio Unitario"],
      subtotal: servicioSeleccionadoInfo["Precio Unitario"] * cantidad
    };
    setTicketItems(prev => [...prev, newItem]);
    setSelectedServicio('');
    setCantidad(1);
  };

  const handleRemoveItem = (idToRemove: string) => {
    setTicketItems(prev => prev.filter(item => item.id !== idToRemove));
  };

  const handleAnularVenta = () => {
    if (window.confirm("¿Está seguro de que desea anular esta operación? Se borrarán todos los datos actuales.")) {
      setTicketItems([]);
      setListaPagos([]);
      setPatientName('');
      setPatientDNI('');
      setHasSpecialDiscount(false);
      setSpecialDiscountValue('');
      setSpecialDiscountReason('');
      setObservaciones('');
      setSelectedCategoria('');
      setSelectedServicio('');
      setCustomNombre('');
      setCustomPrecio('');
      setCantidad(1);
    }
  };

  const handleFinalizarVenta = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketItems.length || !patientName || patientDNI.length !== 8) return;
    if (diferenciaCaja > 0) return; // Bloqueo de seguridad secundario

    if (hasSpecialDiscount && !specialDiscountReason.trim()) {
        alert("Por favor, ingrese el motivo del descuento especial.");
        return;
    }

    const ventaData = {
      paciente: { nombre: patientName, dni: patientDNI },
      items: ticketItems.map(item => ({ 
        id: item.id, 
        nombre: item.nombre, 
        cantidad: item.cantidad,
        precio_unitario: item.precioUnitario 
      })),
      metodo_pago: metodoPagoExcelString, // Cadena formateada para el Excel
      pago_con: totalIngresado,
      vuelto: vueltoEntregar,
      desglose_pagos: listaPagos, // Enviado para que la ticketera imprima el desglose
      destino: selectedDestino,
      descuento_especial_activo: hasSpecialDiscount,
      descuento_especial_tipo: specialDiscountType,
      descuento_especial_valor: Number(specialDiscountValue) || 0,
      descuento_especial_monto_soles: subtotalServicios - totalCalculado,
      descuento_especial_razon: specialDiscountReason,
      observaciones: observaciones
    };

    try {
      const response = await fetch('http://localhost:5000/api/registrar-venta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ventaData)
      });

      if (response.ok) {
          const result = await response.json();
          alert(`Ticket ${result.ticket_id} generado correctamente.`);
          setTicketItems([]);
          setListaPagos([]);
          setPatientName('');
          setPatientDNI('');
          setHasSpecialDiscount(false);
          setSpecialDiscountValue('');
          setSpecialDiscountReason('');
          setObservaciones('');
      } else {
          alert("Error al registrar la venta.");
      }
    } catch (error) {
      alert("Error de conexión con el servidor.");
    }
  };

  return (
    <div className="form-container">
      <form onSubmit={handleFinalizarVenta}>
        <fieldset>
          <legend>Datos del Paciente</legend>
          <label>Nombre: <input type="text" value={patientName} onChange={e => setPatientName(e.target.value.toUpperCase())} required/></label>
          <label>DNI: <input type="text" value={patientDNI} onChange={e => setPatientDNI(e.target.value.replace(/\D/g, ''))} maxLength={8} placeholder="8 dígitos" required/></label>
        </fieldset>

        <fieldset>
          <legend>Añadir Servicio</legend>
          <label>Destino:
            <select value={selectedDestino} onChange={e => { setSelectedDestino(e.target.value as any); setSelectedCategoria(''); setSelectedServicio(''); }}>
              <option value="general">Las Marianas</option>
              <option value="dental">Dental</option>
            </select>
          </label>
          <label>Categoría:
            <select value={selectedCategoria} onChange={e => { setSelectedCategoria(e.target.value); setSelectedServicio(e.target.value === "OTROS" ? "OTROS" : ""); }}>
              <option value="">Seleccione...</option>
              {categoriasDisponibles.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>

          {selectedCategoria === "OTROS" ? (
            <>
              <label>Concepto Personalizado:
                <input type="text" placeholder="Ej. RECARGO MATERIAL" value={customNombre} onChange={e => setCustomNombre(e.target.value)} required />
              </label>
              <label>Precio (S/.):
                <input type="number" min="0" step="0.01" placeholder="0.00" value={customPrecio} onChange={e => setCustomPrecio(e.target.value === '' ? '' : Number(e.target.value))} required />
              </label>
            </>
          ) : (
            <label>Servicio:
              <select value={selectedServicio} onChange={e => setSelectedServicio(e.target.value)}>
                <option value="">Seleccione...</option>
                {serviciosDisponibles.map(s => <option key={s["ID_General"] || s["ID_Dental"]} value={s["ID_General"] || s["ID_Dental"]}>{s["Nombre Específico"]}</option>)}
              </select>
            </label>
          )}

          <label>Cantidad: 
            <input type="number" value={cantidad === 0 ? '' : cantidad} onChange={e => setCantidad(e.target.value === '' ? 0 : Number(e.target.value))} onFocus={(e) => e.target.select()} min="1" />
          </label>
          <button type="button" onClick={handleAddItem} disabled={!selectedServicio && selectedCategoria !== "OTROS"}>Añadir</button>
        </fieldset>

        <fieldset className="special-discount-section">
          <legend>
            <input type="checkbox" checked={hasSpecialDiscount} onChange={(e) => setHasSpecialDiscount(e.target.checked)} /> Descuento Especial
          </legend>
          {hasSpecialDiscount && (
            <div className="discount-controls">
              <div className="dual-button">
                <button type="button" className={specialDiscountType === 'percent' ? 'active' : ''} onClick={() => setSpecialDiscountType('percent')}>%</button>
                <button type="button" className={specialDiscountType === 'fixed' ? 'active' : ''} onClick={() => setSpecialDiscountType('fixed')}>S/.</button>
              </div>
              <input type="number" min="0" step="0.01" placeholder={specialDiscountType === 'percent' ? "Porcentaje %" : "Monto Fijo S/."} value={specialDiscountValue} onChange={(e) => setSpecialDiscountValue(e.target.value === '' ? '' : Number(e.target.value))} required/>
              <input type="text" placeholder="Razón del descuento" value={specialDiscountReason} onChange={(e) => setSpecialDiscountReason(e.target.value)} required/>
            </div>
          )}
        </fieldset>

        <fieldset>
          <legend>Observaciones Adicionales</legend>
          <textarea placeholder="Detalles adicionales..." value={observaciones} onChange={(e) => setObservaciones(e.target.value)} className="observaciones-input" rows={3}/>
        </fieldset>

        <fieldset>
          <legend>Resumen de Venta</legend>
          <table>
            <thead><tr><th>Servicio</th><th>Cant.</th><th>Total</th><th>Acción</th></tr></thead>
            <tbody>
              {ticketItems.map((item, i) => (
                <tr key={i}>
                  <td>{item.nombre}</td>
                  <td>{item.cantidad}</td>
                  <td>S/. {item.subtotal.toFixed(2)}</td>
                  <td><button type="button" onClick={() => handleRemoveItem(item.id)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>❌</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {hasSpecialDiscount ? (
             <div className="summary-totals">
                <p>Subtotal: S/. {subtotalServicios.toFixed(2)}</p>
                <p className="discount-text">Descuento: - S/. {(subtotalServicios - totalCalculado).toFixed(2)}</p>
                <h3>Total a Pagar: S/. {totalCalculado.toFixed(2)}</h3>
             </div>
          ) : (
             <h3>Total a Pagar: S/. {totalCalculado.toFixed(2)}</h3>
          )}

          {/* --- SUBMÓDULO: GESTIÓN DE MÚLTIPLES MÉTODOS DE PAGO (BOCETO DE JOSÉ) --- */}
          <div style={{ border: '1px solid #ccc', padding: '12px', borderRadius: '6px', marginTop: '15px', backgroundColor: '#f9f9f9' }}>
            <h4 style={{ margin: '0 0 10px 0', color: '#333' }}>Control de Caja y Métodos de Pago</h4>
            
            <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
              <select 
                value={metodoSeleccionado} 
                onChange={e => setMetodoSeleccionado(e.target.value)}
                style={{ flex: 1, padding: '5px' }}
              >
                <option value="">Seleccione Método Pago...</option>
                <option value="Efectivo">Efectivo</option>
                <option value="Yape">Yape</option>
                <option value="Plin">Plin</option>
                <option value="Tarjeta">Tarjeta</option>
              </select>
              <button 
                type="button" 
                onClick={handleAddPaymentMethod}
                style={{ backgroundColor: '#28a745', color: 'white', padding: '5px 15px', fontSize: '16px', fontWeight: 'bold', cursor: 'pointer' }}
                title="Añadir método de pago"
              >
                ✓
              </button>
            </div>

            {/* Lista dinámicos de métodos agregados */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '10px' }}>
              {listaPagos.map((pago, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#fff', padding: '6px', borderRadius: '4px', border: '1px solid #ddd' }}>
                  <span style={{ fontWeight: 'bold', minWidth: '80px', fontSize: '13px' }}>{pago.metodo}:</span>
                  <input 
                    type="number" 
                    min="0" 
                    step="0.01"
                    value={pago.monto === 0 ? '' : pago.monto}
                    onChange={e => handleUpdatePaymentAmount(idx, e.target.value === '' ? 0 : Number(e.target.value))}
                    placeholder="S/. 0.00"
                    style={{ flex: 1, padding: '4px', fontSize: '13px' }}
                    required
                  />
                  <button 
                    type="button" 
                    onClick={() => handleRemovePaymentMethod(idx)}
                    style={{ backgroundColor: 'transparent', border: 'none', color: '#dc3545', cursor: 'pointer', fontSize: '16px', fontWeight: 'bold' }}
                  >
                    ❌
                  </button>
                </div>
              ))}
            </div>

            {/* Alertas dinámicas y cálculo del vuelto absoluto en vivo */}
            <div style={{ marginTop: '10px', fontSize: '14px', fontWeight: 'bold' }}>
              <p style={{ margin: '3px 0', color: '#555' }}>Monto Registrado: S/. {totalIngresado.toFixed(2)}</p>
              {diferenciaCaja > 0 ? (
                <p style={{ margin: '3px 0', color: '#dc3545' }}>⚠️ Falta completar: S/. {diferenciaCaja.toFixed(2)}</p>
              ) : (
                <div style={{ borderTop: '1px dashed #ccc', paddingTop: '5px', marginTop: '5px' }}>
                  <p style={{ margin: '3px 0', color: '#28a745' }}>✅ Monto Cubierto</p>
                  {vueltoEntregar > 0 && (
                    <p style={{ margin: '3px 0', color: '#007bff', fontSize: '16px' }}>💵 Entregar Vuelto Físico: S/. {vueltoEntregar.toFixed(2)}</p>
                  )}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '15px', marginTop: '20px' }}>
            <button type="button" onClick={handleAnularVenta} style={{ backgroundColor: '#dc3545', color: 'white', cursor: 'pointer' }} disabled={!ticketItems.length && !patientName && !patientDNI}>Anular Operación</button>
            <button type="submit" style={{ backgroundColor: diferenciaCaja > 0 ? '#ccc' : '#007bff', cursor: diferenciaCaja > 0 ? 'not-allowed' : 'pointer' }} disabled={!ticketItems.length || !patientName || diferenciaCaja > 0}>Generar Ticket</button>
          </div>
        </fieldset>
      </form>
    </div>
  );
};

export default ServiceForm;