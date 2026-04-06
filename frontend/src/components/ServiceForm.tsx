import React, { useState, useEffect, useMemo } from 'react';

// --- INTERFACES PARA TIPADO ---
interface ServicioAPI {
  "ID_General"?: string;
  "ID_Dental"?: string;
  "Categoría": string;
  "Nombre Específico": string;
  "Precio Unitario": number;
}

interface TicketItem {
  id: string; // ID único para el item en el ticket (ej: DEN-001)
  nombre: string;
  cantidad: number;
  precioUnitario: number;
  descuento: number;
  subtotal: number;
}

// --- COMPONENTE PRINCIPAL ---
const ServiceForm: React.FC = () => {
  // --- ESTADOS DEL FORMULARIO Y DATOS ---
  const [patientName, setPatientName] = useState('');
  const [patientDNI, setPatientDNI] = useState('');

  const [catalogos, setCatalogos] = useState<{ general: ServicioAPI[], dental: ServicioAPI[] }>({ general: [], dental: [] });
  const [selectedDestino, setSelectedDestino] = useState<'general' | 'dental'>('general');
  const [selectedCategoria, setSelectedCategoria] = useState('');
  const [selectedServicio, setSelectedServicio] = useState(''); // Estado para el Nombre Específico
  const [cantidad, setCantidad] = useState(1);
  const [descuento, setDescuento] = useState(0);

  const [ticketItems, setTicketItems] = useState<TicketItem[]>([]); // Items agregados al ticket
  const [metodoPago, setMetodoPago] = useState('Efectivo');

  // --- EFECTO PARA CARGAR DATOS DE LA API ---
  useEffect(() => {
    fetch('http://localhost:5000/api/catalogos')
      .then(response => response.json())
      .then(data => setCatalogos(data))
      .catch(error => console.error("Error al cargar catálogos:", error));
  }, []);

  // --- LÓGICA DE SELECTORES DINÁMICOS (MEMOIZED) ---
  const { categoriasDisponibles, serviciosDisponibles, servicioSeleccionadoInfo } = useMemo(() => {
    const catalogoActual = catalogos[selectedDestino] || [];
    
    // Categorías únicas
    const categorias = [...new Set(catalogoActual.map(s => s.Categoría))];
    
    // Servicios filtrados por categoría
    const servicios = selectedCategoria 
      ? catalogoActual.filter(s => s.Categoría === selectedCategoria)
      : [];
      
    // Información completa del servicio seleccionado
    const servicioInfo = selectedServicio
      ? servicios.find(s => (s["ID_General"] || s["ID_Dental"]) === selectedServicio)
      : undefined;

    return { 
      categoriasDisponibles: categorias, 
      serviciosDisponibles: servicios,
      servicioSeleccionadoInfo: servicioInfo
    };
  }, [selectedDestino, selectedCategoria, selectedServicio, catalogos]);

  // --- MANEJADORES DE EVENTOS ---
  const handleAddItem = () => {
    if (!servicioSeleccionadoInfo || cantidad <= 0) {
      alert("Por favor, seleccione un servicio válido y una cantidad mayor a cero.");
      return;
    }

    const newItem: TicketItem = {
      id: servicioSeleccionadoInfo["ID_General"] || servicioSeleccionadoInfo["ID_Dental"]!,
      nombre: servicioSeleccionadoInfo["Nombre Específico"],
      cantidad: cantidad,
      precioUnitario: servicioSeleccionadoInfo["Precio Unitario"],
      descuento: descuento,
      subtotal: (servicioSeleccionadoInfo["Precio Unitario"] - descuento) * cantidad
    };

    setTicketItems(prevItems => [...prevItems, newItem]);

    // Resetear campos del item
    setSelectedServicio('');
    setCantidad(1);
    setDescuento(0);
  };
  
  const handleFinalizarVenta = () => {
      // Lógica para enviar los datos al backend
      console.log("Venta finalizada. Datos a enviar:");
      console.log({
          paciente: { nombre: patientName, dni: patientDNI },
          items: ticketItems,
          metodoPago: metodoPago,
          destino: selectedDestino
      });
      // Aquí iría la llamada fetch con método POST al backend
  }

  // --- CÁLCULO DEL TOTAL ---
  const totalTicket = useMemo(() => {
    return ticketItems.reduce((acc, item) => acc + item.subtotal, 0);
  }, [ticketItems]);

  return (
    <div>
      {/* SECCIÓN DATOS DEL PACIENTE */}
      <fieldset>
        <legend>Datos del Paciente</legend>
        <label>Nombre: <input type="text" value={patientName} onChange={e => setPatientName(e.target.value)} required /></label>
        <label>DNI: <input type="text" value={patientDNI} onChange={e => setPatientDNI(e.target.value)} maxLength={8} required /></label>
      </fieldset>

      {/* SECCIÓN PARA AÑADIR SERVICIOS */}
      <fieldset>
        <legend>Añadir Servicio</legend>
        <label>Destino:
          <select value={selectedDestino} onChange={e => setSelectedDestino(e.target.value as 'general' | 'dental')}>
            <option value="general">Las Marianas (General)</option>
            <option value="dental">Dental</option>
          </select>
        </label>
        <label>Categoría:
          <select value={selectedCategoria} onChange={e => setSelectedCategoria(e.target.value)} disabled={!categoriasDisponibles.length}>
            <option value="">Seleccione...</option>
            {categoriasDisponibles.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label>Nombre Específico:
          <select value={selectedServicio} onChange={e => setSelectedServicio(e.target.value)} disabled={!serviciosDisponibles.length}>
            <option value="">Seleccione...</option>
            {serviciosDisponibles.map(s => <option key={s["ID_General"] || s["ID_Dental"]} value={s["ID_General"] || s["ID_Dental"]}>{s["Nombre Específico"]}</option>)}
          </select>
        </label>
        <label>Cantidad: <input type="number" value={cantidad} onChange={e => setCantidad(Number(e.target.value))} min="1" /></label>
        <label>Descuento (S/.): <input type="number" value={descuento} onChange={e => setDescuento(Number(e.target.value))} min="0" /></label>
        <button type="button" onClick={handleAddItem} disabled={!selectedServicio}>Añadir al Ticket</button>
      </fieldset>
      
      {/* SECCIÓN DESGLOSE DEL TICKET */}
      <fieldset>
        <legend>Ticket Actual</legend>
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Cant.</th>
              <th>P. Unit.</th>
              <th>Desc.</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {ticketItems.map((item, index) => (
              <tr key={index}>
                <td>{item.nombre}</td>
                <td>{item.cantidad}</td>
                <td>S/. {item.precioUnitario.toFixed(2)}</td>
                <td>S/. {item.descuento.toFixed(2)}</td>
                <td>S/. {item.subtotal.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Total: S/. {totalTicket.toFixed(2)}</h3>
      </fieldset>
      
      {/* SECCIÓN FINALIZAR VENTA */}
      <fieldset>
        <legend>Finalizar Venta</legend>
        <label>Método de Pago:
          <select value={metodoPago} onChange={e => setMetodoPago(e.target.value)}>
            <option value="Efectivo">Efectivo</option>
            <option value="Yape">Yape</option>
            <option value="Plin">Plin</option>
            <option value="Tarjeta">Tarjeta</option>
            <option value="Transferencia">Transferencia</option>
          </select>
        </label>
        <button type="button" onClick={handleFinalizarVenta} disabled={!ticketItems.length || !patientName || !patientDNI}>Generar Ticket</button>
      </fieldset>
    </div>
  );
};

export default ServiceForm;