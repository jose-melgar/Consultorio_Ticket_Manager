import React, { useEffect, useState } from 'react';

interface Venta {
    id_ticket_global: string;
    id_ticket_especifico: string;
    fecha: string;
    paciente: {
        nombre: string;
        dni: string;
    };
    total_final: number | string;
    metodo_pago: string;
    destino: string;
}

const TicketHistory: React.FC = () => {
    const [historial, setHistorial] = useState<Venta[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const cargarDatos = async () => {
        try {
            setLoading(true);
            const response = await fetch('http://localhost:5000/api/tickets');
            
            if (!response.ok) {
                throw new Error('No se pudo obtener el historial del servidor');
            }

            const data = await response.json();
            // Validamos que la data sea un arreglo
            setHistorial(Array.isArray(data) ? data : []);
            setError(null);
        } catch (err) {
            console.error("Error al cargar historial:", err);
            setError("Error de conexión con el backend.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        cargarDatos();
    }, []);

    if (loading) return <div className="p-4 text-blue-600 font-bold">Cargando historial desde ventas.json...</div>;
    
    if (error) return (
        <div className="p-4 bg-red-100 text-red-700 rounded-lg mt-6">
            {error} <button onClick={cargarDatos} className="underline ml-2">Reintentar</button>
        </div>
    );

    return (
        <div className="bg-white p-6 rounded-lg shadow-md mt-6">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Historial de Tickets</h2>
                <button onClick={cargarDatos} className="text-sm bg-gray-200 px-3 py-1 rounded hover:bg-gray-300">
                    Actualizar
                </button>
            </div>
            
            <div className="overflow-x-auto">
                <table className="min-w-full table-auto">
                    <thead>
                        <tr className="bg-gray-100 border-b">
                            <th className="px-4 py-2 text-left">Ticket</th>
                            <th className="px-4 py-2 text-left">Fecha</th>
                            <th className="px-4 py-2 text-left">Paciente</th>
                            <th className="px-4 py-2 text-left">Destino</th>
                            <th className="px-4 py-2 text-right">Total</th>
                            <th className="px-4 py-2 text-center">Pago</th>
                        </tr>
                    </thead>
                    <tbody>
                        {historial.map((venta, index) => (
                            <tr key={index} className="border-b hover:bg-gray-50 transition-colors">
                                <td className="px-4 py-2 font-mono text-xs">
                                    <span className="font-bold">{venta.id_ticket_global}</span>
                                    <br />
                                    <span className="text-gray-400">{venta.id_ticket_especifico}</span>
                                </td>
                                <td className="px-4 py-2 text-sm">{venta.fecha}</td>
                                <td className="px-4 py-2 text-sm">
                                    <div className="font-medium">{venta.paciente.nombre}</div>
                                    <div className="text-xs text-gray-500">DNI: {venta.paciente.dni}</div>
                                </td>
                                <td className="px-4 py-2 text-sm">{venta.destino}</td>
                                <td className="px-4 py-2 text-right font-bold text-green-700">
                                    S/. {Number(venta.total_final).toFixed(2)}
                                </td>
                                <td className="px-4 py-2 text-center">
                                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-[10px] uppercase font-bold">
                                        {venta.metodo_pago}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {historial.length === 0 && (
                    <div className="text-center py-10">
                        <p className="text-gray-500 italic">No se encontraron registros en el archivo de ventas.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TicketHistory;