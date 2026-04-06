from flask import Flask, jsonify, request, Response, send_file
from flask_cors import CORS
from catalog_manager import cargar_catalogos, guardar_nueva_venta, leer_historial_ventas
from pdf_generator import generar_ticket_pdf
from datetime import datetime
import io

from models import Ticket, Paciente, ServicioItem # <-- Importar los modelos
from catalog_manager import registrar_venta_excel # <-- Importar la función de registro
from pdf_generator import generar_ticket_pdf # <-- Importar el generador de PDF

app = Flask(__name__)
CORS(app)

CATALOGOS = cargar_catalogos()

# Endpoint para OBTENER los catálogos (sin cambios)
@app.route("/api/catalogos", methods=["GET"])
def get_catalogos():
    # ... (código existente sin cambios)
    general_json = CATALOGOS["General"].to_dict(orient="records")
    dental_json = CATALOGOS["Dental"].to_dict(orient="records")
    return jsonify({"general": general_json, "dental": dental_json})

# Endpoint para OBTENER el historial de tickets
@app.route("/api/tickets", methods=["GET"])
def get_tickets():
    historial = leer_historial_ventas()
    return jsonify(historial)

# Endpoint para CREAR un nuevo ticket/venta
@app.route("/api/registrar-venta", methods=["POST"])
def registrar_nueva_venta():
    """
    Recibe los datos del ticket desde el frontend, registra la venta
    y devuelve el ticket en formato PDF.
    """
    data = request.json
    print(f"Datos recibidos para registrar venta: {data}")

    try:
        # 1. Reconstruir los objetos del ticket a partir del JSON recibido
        paciente = Paciente(nombre=data["paciente"]["nombre"], dni=data["paciente"]["dni"])
        
        items_ticket = []
        for item_data in data["items"]:
            # Buscamos la info completa del item en nuestros catálogos para asegurar la integridad de los precios
            catalogo_actual = CATALOGOS[data["destino"]]
            id_col_name = "ID_General" if data["destino"] == "general" else "ID_Dental"
            
            info_catalogo = catalogo_actual[catalogo_actual[id_col_name] == item_data["id"]].iloc[0]

            item = ServicioItem(
                categoria=info_catalogo["Categoría"],
                nombre_especifico=item_data["nombre"],
                precio_unitario=float(info_catalogo["Precio Unitario"]),
                cantidad=int(item_data["cantidad"]),
                descuento=float(info_catalogo["Descuento"])
            )
            items_ticket.append(item)

        ticket = Ticket(
            paciente=paciente,
            items=items_ticket,
            metodo_pago=data["metodo_pago"],
            destino=data["destino"].capitalize() # "General" o "Dental"
        )
        
        # 2. Registrar la venta en el archivo Excel correspondiente
        # Esta función también generará los nuevos IDs de ticket
        ticket_id_global, ticket_id_especifico = registrar_venta_excel(ticket)
        
        # 3. Generar el PDF del ticket
        pdf_bytes = generar_ticket_pdf(ticket, ticket_id_global, ticket_id_especifico)
        
        # 4. Devolver el PDF al frontend
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Ticket-{ticket_id_global}.pdf'
        )

    except Exception as e:
        print(f"Error al procesar la venta: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
