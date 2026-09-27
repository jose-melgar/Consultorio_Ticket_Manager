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
  habilitado?: boolean;
  motivo_eliminacion?: string;
}

interface TicketHistoryProps {
  onCargarPaciente?: (nombre: string, dni: string) => void;
}

const TicketHistory: React.FC<TicketHistoryProps> = ({ onCargarPaciente }) => {
  const [tickets, setTickets] = useState<TicketHistorial[]>([]);
  const [ticketModal, setTicketModal] = useState<TicketHistorial | null>(null);
  const [vistaActual, setVistaActual] = useState<'activos' | 'eliminados'>('activos');

  // Estados para el Input Box Modal de eliminación
  const [ticketAEliminar, setTicketAEliminar] = useState<string | null>(null);
  const [motivoEliminacion, setMotivoEliminacion] = useState<string>('');
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

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

  // Función que procesa la eliminación al presionar "Aceptar" en el Input Box Modal
  const handleConfirmarEliminacion = async () => {
    if (!ticketAEliminar) return;

    setIsDeleting(true);
    try {
      const motivoFinal = motivoEliminacion.trim() || 'No se especificó motivo';

      const response = await fetch(`http://localhost:5000/api/eliminar-ticket/${ticketAEliminar}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motivo: motivoFinal })
      });
      
      if (response.ok) {
        setTicketAEliminar(null);
        setMotivoEliminacion('');
        fetchTickets();
      } else {
        alert("Hubo un problema al intentar eliminar el ticket.");
      }
    } catch (error) {
      alert("Error de conexión al intentar eliminar.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelarEliminacion = () => {
    setTicketAEliminar(null);
    setMotivoEliminacion('');
  };

  // Filtrado reactivo según pestaña
  const ticketsMostrados = tickets.filter(t => 
    vistaActual === 'activos' ? t.habilitado !== false : t.habilitado === false
  );

  return (
    <div className="history-container">
      <h2>Historial de Tickets Generados</h2>

      {/* Pestañas de cambio de vista */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={() => setVistaActual('activos')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '5px',
              fontWeight: 'bold',
              cursor: 'pointer',
              backgroundColor: vistaActual === 'activos' ? '#007bff' : '#e0e0e0',
              color: vistaActual === 'activos' ? '#fff' : '#333'
            }}
          >
            🟢 Tickets Activos
          </button>
          <button 
            onClick={() => setVistaActual('eliminados')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '5px',
              fontWeight: 'bold',
              cursor: 'pointer',
              backgroundColor: vistaActual === 'eliminados' ? '#dc3545' : '#e0e0e0',
              color: vistaActual === 'eliminados' ? '#fff' : '#333'
            }}
          >
            🔴 Tickets Eliminados
          </button>
        </div>

        <button className="refresh-button" onClick={fetchTickets}>🔄 Actualizar Lista</button>
      </div>
      
      <table className="history-table">
        <thead>
          <tr>
            <th>Ticket Global</th>
            <th>Operación</th>
            <th>Fecha</th>
            <th>Paciente</th>
            <th>Total (S/.)</th>
            {vistaActual === 'eliminados' ? <th>Motivo de Eliminación</th> : <th>Acciones</th>}
          </tr>
        </thead>
        <tbody>
          {ticketsMostrados.length === 0 ? (
            <tr><td colSpan={6} style={{ textAlign: 'center' }}>No hay tickets {vistaActual} registrados aún.</td></tr>
          ) : (
            [...ticketsMostrados].reverse().map((ticket, index) => (
              <tr key={index} style={{ backgroundColor: vistaActual === 'eliminados' ? '#fff3f3' : 'inherit' }}>
                <td>
                  <button
                    onClick={() => setTicketModal(ticket)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: vistaActual === 'eliminados' ? '#dc3545' : '#007bff',
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

                {vistaActual === 'eliminados' ? (
                  <td style={{ color: '#dc3545', fontSize: '13px', textAlign: 'left' }}>
                    {ticket.motivo_eliminacion || 'No se especificó motivo'}
                  </td>
                ) : (
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
                        onClick={() => setTicketAEliminar(ticket.id_ticket_global)} 
                        style={{ backgroundColor: '#dc3545', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                        title="Eliminar del sistema"
                      >
                        🗑️ Borrar
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* ============================================================================== */}
      {/* 🛑 INPUT BOX MODAL: SOLICITUD DE MOTIVO DE ELIMINACIÓN                          */}
      {/* ============================================================================== */}
      {ticketAEliminar && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 10000
          }}
        >
          <div 
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              padding: '24px',
              width: '420px',
              boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '15px'
            }}
          >
            <h3 style={{ margin: 0, color: '#dc3545', fontSize: '18px' }}>
              ⚠️ Eliminar Ticket {ticketAEliminar}
            </h3>
            <p style={{ margin: 0, fontSize: '13px', color: '#555', lineHeight: '1.4' }}>
              Esta acción retirará el ticket de la contabilidad en Excel. Ingrese el motivo de eliminación (opcional):
            </p>
            <input 
              type="text" 
              placeholder="Ej. Paciente canceló atención / Error de digitación..."
              value={motivoEliminacion}
              onChange={(e) => setMotivoEliminacion(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                fontSize: '13px',
                boxSizing: 'border-box'
              }}
              autoFocus
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '5px' }}>
              <button 
                type="button" 
                onClick={handleCancelarEliminacion}
                disabled={isDeleting}
                style={{
                  padding: '8px 16px',
                  borderRadius: '4px',
                  border: '1px solid #ccc',
                  backgroundColor: '#dc3545',
                  cursor: isDeleting ? 'not-allowed' : 'pointer',
                  fontSize: '13px'
                }}
              >
                Cancelar
              </button>
              <button 
                type="button" 
                onClick={handleConfirmarEliminacion}
                disabled={isDeleting}
                style={{
                  padding: '8px 16px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: '#35dc46',
                  color: '#ffffff',
                  fontWeight: 'bold',
                  cursor: isDeleting ? 'not-allowed' : 'pointer',
                  fontSize: '13px'
                }}
              >
                {isDeleting ? 'Eliminando...' : 'Aceptar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================================== */}
      {/* 🧾 MODAL FLOTANTE: VISTA PREVIA SIMULADA DEL TICKET EN PANTALLA                */}
      {/* ============================================================================== */}
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

            {ticketModal.habilitado === false && (
              <div style={{ backgroundColor: '#dc3545', color: 'white', textAlign: 'center', padding: '4px', fontWeight: 'bold', marginBottom: '8px', borderRadius: '4px', fontSize: '12px' }}>
                *** TICKET ELIMINADO ***
              </div>
            )}

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

            <div style={{ textAlign: 'right', fontWeight: 'bold', fontSize: '15px', margin: '8px 0' }}>
              TOTAL A PAGAR: S/. {parseFloat(String(ticketModal.total_final)).toFixed(2)}
            </div>

            <div style={{ textAlign: 'right', fontSize: '12px', marginBottom: '8px' }}>
              Método de Pago: {ticketModal.metodo_pago || 'Efectivo'}
            </div>

            {ticketModal.motivo_eliminacion && (
              <>
                <div style={{ borderBottom: '1px dashed #000', margin: '8px 0' }} />
                <div style={{ textAlign: 'left', marginBottom: '8px', color: '#dc3545' }}>
                  <p style={{ margin: '0 0 2px 0', fontWeight: 'bold' }}>Motivo de Eliminación:</p>
                  <p style={{ margin: 0, fontSize: '12px' }}>{ticketModal.motivo_eliminacion}</p>
                </div>
              </>
            )}

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