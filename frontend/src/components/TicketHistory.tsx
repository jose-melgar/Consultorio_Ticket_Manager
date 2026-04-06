import React, { useState, useEffect } from 'react';

// --- INTERFACES PARA TIPADO ---
// Estas interfaces deben coincidir con la estructura de datos que guarda el backend
interface TicketItem {
  id: string;
  nombre: string;
  cantidad: number;
  precioUnitario: number;
  descuento: number;
  subtotal: number;
}

interface Venta {
  id_ticket_global: string;
  fecha: string;
  paciente: {
    nombre: string;
    dni: string;
  };
  items: TicketItem[];
  total_final: number;
  metodoPago: string;
  destino: string;
}

// --- COMPONENTE PRINCIPAL ---
const TicketHistory: React.FC = () => {
  const [ventas, setVentas] = useState<Venta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Función para cargar los datos desde la API
    const fetchVentas = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/tickets');
        if (!response.ok) {
          throw new Error('Error al obtener los datos del servidor');
        }
        const data: Venta[] = await response.json();
        // Ordenamos las ventas de la más reciente a la más antigua
        setVentas(data.sort((a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime()));
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchVentas();
  }, []); // El array vacío asegura que se ejecute solo una vez al montar el componente

  // --- RENDERIZADO CONDICIONAL ---
  if (loading) {
    return <p>Cargando historial de tickets...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>Error: {error}</p>;
  }

  return (
    <div className="ticket-history-container">
      <h2>Historial de Tickets Generados</h2>
      {ventas.length === 0 ? (
        <p>Aún no se ha generado ningún ticket.</p>
      ) : (
        <table className="history-table">
          <thead>
            <tr>
              <th>ID Ticket</th>
              <th>Fecha</th>
              <th>Paciente</th>
              <th>DNI</th>
              <th>Total Pagado</th>
              <th>Método de Pago</th>
              <th>Destino</th>
            </tr>
          </thead>
          <tbody>
            {ventas.map((venta) => (
              <tr key={venta.id_ticket_global}>
                <td>{venta.id_ticket_global}</td>
                <td>{new Date(venta.fecha).toLocaleString('es-PE')}</td>
                <td>{venta.paciente.nombre}</td>
                <td>{venta.paciente.dni}</td>
                <td>S/. {venta.total_final.toFixed(2)}</td>
                <td>{venta.metodoPago}</td>
                <td>{venta.destino}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default TicketHistory;