import React, { useEffect, useState } from 'react';
import '../styles.css';
import logoColor from '../assets/Ocupasalud Logo a color.png';

interface TicketItem {
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal?: number;
}

interface PagoMetodo {
  metodo: string;
  monto: number;
}

interface TicketHistorial {
  id_ticket_global: string;
  id_ticket_especifico: string;
  fecha: string;
  paciente: {
    nombre: string;
    dni: string;
  };
  total_final: string | number;
  items?: TicketItem[];
  metodo_pago?: string;
  desglose_pagos?: PagoMetodo[];
  vuelto?: number;
  descuento_especial_activo?: boolean;
  descuento_especial_monto_soles?: number;
  descuento_especial_razon?: string;
  observaciones?: string;
}

interface TicketHistoryProps {
  onCargarPaciente?: (nombre: string, dni: string) => void;
}

const TicketHistory: React.FC<TicketHistoryProps> = ({ onCargarPaciente }) => {
  const [tickets, setTickets] = useState<TicketHistorial[]>([]);
  const [ticketModal, setTicketModal] = useState<TicketHistorial | null>(null);

  const fetchTickets = () => {
    fetch('http://localhost:5000/api/tickets')
      .then(res => res.json())
      .then(data => setTickets(data))
      .catch(err => console.error("Error al cargar historial", err));
  };

  useEffect(() => {
    fetchTickets();
  }, []);

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
                <td>
                  <button
                    onClick={() => setTicketModal(ticket)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#007bff',
                      textDecoration: 'underline',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                    title="Haz clic para visualizar el ticket en pantalla"
                  >
                    👁️ {ticket.id_ticket_global}
                  </button>
                </td>
                <td>{ticket.id_ticket_especifico}</td>
                <td>{ticket.fecha}</td>
                <td>{ticket.paciente?.nombre || 'Desconocido'}</td>
                <td>S/. {parseFloat(String(ticket.total_final)).toFixed(2)}</td>
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', alignItems: 'center' }}>
                    <button 
                      onClick={() => {
                        if (onCargarPaciente && ticket.paciente) {
                          onCargarPaciente(ticket.paciente.nombre || '', ticket.paciente.dni || '');
                        }
                      }}
                      style={{ backgroundColor: '#28a745', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                      title="Cargar Nombre y DNI para un nuevo ticket"
                    >
                      👤 Cargar
                    </button>

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

      {/* MODAL CON ANCHO COMPLETO PARA CADA DESCRIPCIÓN */}
      {ticketModal && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 9999,
            padding: '20px'
          }}
          onClick={() => setTicketModal(null)}
        >
          <div 
            style={{
              backgroundColor: '#ffffff',
              width: '360px',
              maxHeight: '90vh',
              overflowY: 'auto',
              borderRadius: '8px',
              padding: '20px',
              boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
              fontFamily: "'Courier New', Courier, monospace",
              color: '#000000',
              fontSize: '13px',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              onClick={() => setTicketModal(null)}
              style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                background: '#dc3545',
                color: '#fff',
                border: 'none',
                borderRadius: '50%',
                width: '26px',
                height: '26px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '14px'
              }}
              title="Cerrar vista previa"
            >
              ✕
            </button>

            {/* Logo y Encabezado */}
            <div style={{ textAlign: 'center', marginBottom: '12px' }}>
              <img 
                src={logoColor} 
                alt="Ocupasalud Logo" 
                style={{ width: '160px', height: 'auto', margin: '0 auto 8px auto', display: 'block' }} 
              />
              <p style={{ margin: '2px 0', fontSize: '11px' }}>Calle Pisac 113 Mz B2 Lt 46</p>
              <p style={{ margin: '2px 0', fontSize: '11px' }}>WhatsApp: 921 689 864</p>
            </div>

            <div style={{ borderBottom: '1px dashed #000', margin: '8px 0' }} />

            {/* Datos del Paciente */}
            <div style={{ marginBottom: '10px' }}>
              <p style={{ margin: '2px 0', fontWeight: 'bold' }}>TICKET: {ticketModal.id_ticket_global}</p>
              <p style={{ margin: '2px 0' }}>Op: {ticketModal.id_ticket_especifico}</p>
              <p style={{ margin: '2px 0' }}>Fecha: {ticketModal.fecha}</p>
              <br />
              <p style={{ margin: '2px 0', fontWeight: 'bold' }}>Paciente:</p>
              <p style={{ margin: '2px 0' }}>{ticketModal.paciente?.nombre || 'Desconocido'}</p>
              <p style={{ margin: '2px 0' }}>DNI: {ticketModal.paciente?.dni || 'N/A'}</p>
            </div>

            <div style={{ borderBottom: '1px dashed #000', margin: '8px 0' }} />

            {/* Lista de Servicios (Ancho Completo) */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ borderBottom: '1px solid #000', paddingBottom: '3px', fontWeight: 'bold', fontSize: '12px' }}>
                DETALLE DE SERVICIOS
              </div>
              {ticketModal.items && ticketModal.items.length > 0 ? (
                ticketModal.items.map((it, idx) => {
                  const cant = it.cantidad || 1;
                  const precio = parseFloat(String(it.precio_unitario || 0));
                  const subtotal = parseFloat(String((it as any).subtotal || (precio * cant)));
                  return (
                    <div key={idx} style={{ padding: '6px 0', borderBottom: '1px dotted #ccc' }}>
                      <div style={{ fontWeight: 'bold', wordBreak: 'break-word', fontSize: '12px' }}>
                        {it.nombre}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginTop: '2px' }}>
                        <span>Cant: {cant}</span>
                        <span>Total: S/. {subtotal.toFixed(2)}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign: 'center', padding: '6px 0', fontSize: '12px' }}>
                  Detalle no disponible
                </div>
              )}
            </div>

            <div style={{ borderBottom: '1px dashed #000', margin: '8px 0' }} />

            {/* Descuentos */}
            {ticketModal.descuento_especial_activo && (
              <div style={{ textAlign: 'right', marginBottom: '6px', fontSize: '12px' }}>
                {ticketModal.descuento_especial_monto_soles && (
                  <p style={{ margin: '2px 0' }}>
                    Dcto: - S/. {parseFloat(String(ticketModal.descuento_especial_monto_soles)).toFixed(2)}
                  </p>
                )}
                {ticketModal.descuento_especial_razon && (
                  <p style={{ margin: '2px 0', fontStyle: 'italic', fontSize: '11px' }}>
                    ({ticketModal.descuento_especial_razon})
                  </p>
                )}
              </div>
            )}

            {/* Total y Método de Pago */}
            <div style={{ textAlign: 'right', fontWeight: 'bold', fontSize: '15px', margin: '8px 0' }}>
              TOTAL A PAGAR: S/. {parseFloat(String(ticketModal.total_final)).toFixed(2)}
            </div>

            <div style={{ textAlign: 'right', fontSize: '12px', marginBottom: '8px' }}>
              Método de Pago: {ticketModal.metodo_pago || 'Efectivo'}
            </div>

            {/* Observaciones */}
            {ticketModal.observaciones && ticketModal.observaciones.trim() !== '' && (
              <>
                <div style={{ borderBottom: '1px dashed #000', margin: '8px 0' }} />
                <div style={{ textAlign: 'left', marginBottom: '8px' }}>
                  <p style={{ margin: '0 0 2px 0', fontWeight: 'bold' }}>Observaciones:</p>
                  <p style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {ticketModal.observaciones}
                  </p>
                </div>
              </>
            )}

            <div style={{ borderBottom: '1px dashed #000', margin: '8px 0' }} />

            <div style={{ textAlign: 'center', fontWeight: 'bold', marginTop: '12px' }}>
              *** GRACIAS ***
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TicketHistory;