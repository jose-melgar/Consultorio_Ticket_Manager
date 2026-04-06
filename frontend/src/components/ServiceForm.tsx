import React, { useState, useEffect, useMemo } from 'react';

// ... Interfaces existentes ...
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

const ServiceForm: React.FC = () => {
  const [patientName, setPatientName] = useState('');
  const [patientDNI, setPatientDNI] = useState('');
  const [catalogos, setCatalogos] = useState<{ general: ServicioAPI[], dental: ServicioAPI[] }>({ general: [], dental: [] });
  const [selectedDestino, setSelectedDestino] = useState<'general' | 'dental'>('general');
  const [selectedCategoria, setSelectedCategoria] = useState('');
  const [selectedServicio, setSelectedServicio] = useState('');
  const [cantidad, setCantidad] = useState<number>(1);
  const [ticketItems, setTicketItems] = useState<TicketItem[]>([]);
  const [metodoPago, setMetodoPago] = useState('Efectivo');

  useEffect(() => {
    fetch('http://localhost:5000/api/catalogos')
      .then(response => response.json())
      .then(data => setCatalogos(data));
  }, []);

  const { categoriasDisponibles, serviciosDisponibles, servicioSeleccionadoInfo } = useMemo(() => {
    const catalogoActual = catalogos[selectedDestino] || [];
    const categorias = [...new Set(catalogoActual.map(s => s.Categoría))];
    const servicios = selectedCategoria ? catalogoActual.filter(s => s.Categoría === selectedCategoria) : [];
    const servicioInfo = selectedServicio ? servicios.find(s => (s["ID_General"] || s["ID_Dental"]) === selectedServicio) : undefined;
    return { categoriasDisponibles: categorias, serviciosDisponibles: servicios, servicioSeleccionadoInfo: servicioInfo };
  }, [selectedDestino, selectedCategoria, selectedServicio, catalogos]);

  const handleAddItem = () => {
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

  const handleFinalizarVenta = async () => {
    const ventaData = {
      paciente: { nombre: patientName, dni: patientDNI },
      items: ticketItems.map(item => ({ id: item.id, nombre: item.nombre, cantidad: item.cantidad })),
      metodo_pago: metodoPago,
      destino: selectedDestino
    };

    try {
      const response = await fetch('http://localhost:5000/api/registrar-venta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ventaData)
      });

      if (response.ok) {
          const result = await response.json();
          alert(`Ticket ${result.ticket_id} guardado correctamente en la carpeta Tickets.`);
          // Limpiar formulario
          setTicketItems([]);
          setPatientName('');
          setPatientDNI('');
      } else {
          alert("Error al registrar la venta.");
      }
    } catch (error) {
      alert("Error de conexión con el servidor.");
    }
  };

  const totalTicket = useMemo(() => ticketItems.reduce((acc, item) => acc + item.subtotal, 0), [ticketItems]);

  return (
    <div className="form-container">
      <fieldset>
        <legend>Datos del Paciente</legend>
        <label>Nombre: <input type="text" value={patientName} onChange={e => setPatientName(e.target.value)} /></label>
        <label>DNI: <input type="text" value={patientDNI} onChange={e => setPatientDNI(e.target.value)} maxLength={8} /></label>
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
          <select value={selectedCategoria} onChange={e => setSelectedCategoria(e.target.value)}>
            <option value="">Seleccione...</option>
            {categoriasDisponibles.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label>Servicio:
          <select value={selectedServicio} onChange={e => setSelectedServicio(e.target.value)}>
            <option value="">Seleccione...</option>
            {serviciosDisponibles.map(s => <option key={s["ID_General"] || s["ID_Dental"]} value={s["ID_General"] || s["ID_Dental"]}>{s["Nombre Específico"]}</option>)}
          </select>
        </label>
        <label>Cantidad: 
          <input 
            type="number" 
            value={cantidad === 0 ? '' : cantidad} 
            onChange={e => setCantidad(e.target.value === '' ? 0 : Number(e.target.value))} 
            onFocus={(e) => e.target.select()} // Soluciona el problema de sobreescritura rápida
            min="1" 
          />
        </label>
        <button type="button" onClick={handleAddItem} disabled={!selectedServicio}>Añadir</button>
      </fieldset>

      <fieldset>
        <legend>Resumen</legend>
        <table>
          <thead><tr><th>Servicio</th><th>Cant.</th><th>Total</th></tr></thead>
          <tbody>
            {ticketItems.map((item, i) => (
              <tr key={i}><td>{item.nombre}</td><td>{item.cantidad}</td><td>S/. {item.subtotal.toFixed(2)}</td></tr>
            ))}
          </tbody>
        </table>
        <h3>Total: S/. {totalTicket.toFixed(2)}</h3>
        <label>Pago:
          <select value={metodoPago} onChange={e => setMetodoPago(e.target.value)}>
            <option value="Efectivo">Efectivo</option>
            <option value="Yape">Yape</option>
            <option value="Plin">Plin</option>
            <option value="Tarjeta">Tarjeta</option>
          </select>
        </label>
        <button onClick={handleFinalizarVenta} disabled={!ticketItems.length || !patientName}>Generar Ticket</button>
      </fieldset>
    </div>
  );
};

export default ServiceForm;