import React, { useEffect, useState } from 'react';
import '../styles.css';

interface TicketHistorial {
  id_ticket_global: string;
  id_ticket_especifico: string;
  fecha: string;
  paciente: {
    nombre: string;
    dni: string;
  };
  total_final: string;
}

const TicketHistory: React.FC = () => {
  const [tickets, setTickets] = useState<TicketHistorial[]>([]);

  const fetchTickets = () => {
    fetch('http://localhost:5000/api/tickets')
      .then(res => res.json())
      .then(data => setTickets(data))
      .catch(err => console.error("Error al cargar historial", err));
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  // --- NUEVA FUNCIÓN PARA ENVIAR LA REIMPRESIÓN AL BACKEND ---
  const handleReimprimir = async (id_global: string, cantidad: number) => {
    try {
      const response = await fetch('http://localhost:5000/api/reimprimir-ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_ticket_global: id_global, cantidad: cantidad })
      });
      
      if (response.ok) {
        alert(`Enviando ${cantidad} copia(s) del ticket ${id_global} a la ticketera térmica.`);
      } else {
        alert("Hubo un error al intentar mandar la reimpresión.");
      }
    } catch (error) {
      alert("Error de conexión con el servidor de la ticketera.");
    }
  };

  const handleEliminarTicket = async (id_global: string) => {
    if (window.confirm(`⚠️ ADVERTENCIA ⚠️\n\n¿Estás absolutamente seguro de eliminar el ticket ${id_global}?\n\nEsto lo borrará del sistema, eliminará el PDF y reajustará el archivo de contabilidad en Excel. Esta acción no se puede deshacer.`)) {
      try {
        const response = await fetch(`http://localhost:5000/api/eliminar-ticket/${id_global}`, {
          method: 'DELETE',
        });
        
        if (response.ok) {
          alert(`Ticket ${id_global} eliminado correctamente de la contabilidad.`);
          fetchTickets();
        } else {
          alert("Hubo un problema al intentar eliminar el ticket.");
        }
      } catch (error) {
        alert("Error de conexión al intentar eliminar.");
      }
    }
  };

  return (
    <div className="history-container">
      <h2>Historial de Tickets Generados</h2>
      <button className="refresh-button" onClick={fetchTickets}>🔄 Actualizar Lista</button>
      
      <table className="history-table">
        <thead>
          <tr>
            <th>Ticket Global</th>
            <th>Operación</th>
            <th>Fecha</th>
            <th>Paciente</th>
            <th>Total (S/.)</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {tickets.length === 0 ? (
            <tr><td colSpan={6} style={{ textAlign: 'center' }}>No hay tickets registrados aún.</td></tr>
          ) : (
            [...tickets].reverse().map((ticket, index) => (
              <tr key={index}>
                <td>{ticket.id_ticket_global}</td>
                <td>{ticket.id_ticket_especifico}</td>
                <td>{ticket.fecha}</td>
                <td>{ticket.paciente?.nombre || 'Desconocido'}</td>
                <td>S/. {parseFloat(ticket.total_final).toFixed(2)}</td>
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}>
                    
                    {/* Control de cantidad de copias integrado en la fila */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                      <label htmlFor={`copias-${ticket.id_ticket_global}`} style={{ fontSize: '11px', margin: 0 }}>Cops:</label>
                      <input 
                        type="number" 
                        min="1" 
                        max="5" 
                        defaultValue="1" 
                        id={`copias-${ticket.id_ticket_global}`}
                        style={{ width: '40px', padding: '2px', textAlign: 'center', fontSize: '12px' }}
                      />
                    </div>

                    {/* Botón de Reimpresión */}
                    <button 
                      onClick={() => {
                        const input = document.getElementById(`copias-${ticket.id_ticket_global}`) as HTMLInputElement;
                        const cant = input ? parseInt(input.value) : 1;
                        handleReimprimir(ticket.id_ticket_global, cant);
                      }}
                      style={{ backgroundColor: '#007bff', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Reimprimir este ticket automáticamente"
                    >
                      🖨️ Imprimir
                    </button>

                    {/* Botón de Borrado */}
                    <button 
                      onClick={() => handleEliminarTicket(ticket.id_ticket_global)} 
                      style={{ backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                      title="Eliminar del sistema"
                    >
                      🗑️ Borrar
                    </button>

                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default TicketHistory;