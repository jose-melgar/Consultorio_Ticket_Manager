from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from decimal import Decimal
import os
from models import Ticket, Paciente, ServicioItem
from catalog_manager import (
    cargar_catalogos, generar_nuevos_ids, registrar_venta_csv, 
    guardar_historial_json, leer_historial_ventas
)
from pdf_generator import generar_ticket_pdf
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
# Definimos la carpeta 'build' como la carpeta de archivos estáticos para producción
app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

# --- CONFIGURACIÓN DE RUTAS DE DATOS ---
CATALOGOS = cargar_catalogos()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Tickets se guardará en una carpeta al mismo nivel que el backend/ejecutable
TICKETS_DIR = os.path.join(BASE_DIR, '..', 'Tickets')

if not os.path.exists(TICKETS_DIR):
    os.makedirs(TICKETS_DIR)

# --- RUTAS PARA SERVIR EL FRONTEND (REACT) ---

@app.route("/")
def serve_index():
    """Sirve el archivo principal de la aplicación React."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Sirve archivos estáticos (JS, CSS, imágenes) o redirige a index si no existe."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Esto permite que el routing de React funcione correctamente (SPA)
        return send_from_directory(app.static_folder, 'index.html')

# --- RUTAS DE LA API ---

@app.route("/api/catalogos", methods=["GET"])
def get_catalogos():
    return jsonify({
        "general": CATALOGOS["General"].to_dict(orient="records"),
        "dental": CATALOGOS["Dental"].to_dict(orient="records")
    })

@app.route("/api/tickets", methods=["GET"])
def get_historial():
    return jsonify(leer_historial_ventas())

@app.route("/api/registrar-venta", methods=["POST"])
def registrar():
    data = request.json
    
    if not data.get('items'):
        return jsonify({"error": "No hay servicios seleccionados"}), 400

    try:
        # Validación y reconstrucción de objetos
        paciente = Paciente(nombre=data["paciente"]["nombre"], dni=data["paciente"]["dni"])
        items_objs = []
        destino = data["destino"].capitalize()
        cat = CATALOGOS[destino]
        id_col = "ID_General" if data["destino"].lower() == "general" else "ID_Dental"

        for it in data["items"]:
            # Localizar el ítem en el catálogo cargado en memoria
            row = cat[cat[id_col] == it["id"]].iloc[0]
            items_objs.append(ServicioItem(
                categoria=row["Categoría"],
                nombre_especifico=it["nombre"],
                precio_unitario=Decimal(str(row["Precio Unitario"])),
                cantidad=int(it["cantidad"]),
                descuento=Decimal("0.00") # Manejo de descuento manual eliminado según requerimiento
            ))

        ticket = Ticket(
            paciente=paciente, 
            items=items_objs, 
            metodo_pago=data["metodo_pago"], 
            destino=destino
        )
        
        # Generar IDs y registrar en CSV para persistencia administrativa
        id_glob, id_esp = generar_nuevos_ids(destino)
        registrar_venta_csv(ticket, id_glob, id_esp)
        
        # Preparar data unificada para el historial JSON y el Generador de PDF
        venta_final = {
            "id_ticket_global": id_glob,
            "id_ticket_especifico": id_esp,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "paciente": {"nombre": paciente.nombre, "dni": paciente.dni},
            "items": [
                {
                    "nombre": i.nombre_especifico, 
                    "cantidad": i.cantidad, 
                    "precio_unitario": i.precio_unitario, 
                    "subtotal": i.subtotal
                } for i in items_objs
            ],
            "total_final": ticket.total_final,
            "metodo_pago": ticket.metodo_pago,
            "destino": ticket.destino,
            "atendido_por": "José Melgar" # Nombre del cajero/operador para el PDF profesional
        }

        guardar_historial_json(venta_final)
        
        # Generar PDF y guardarlo localmente con el ID Global en la carpeta Tickets
        pdf_bytes = generar_ticket_pdf(venta_final)
        pdf_name = f"{id_glob}.pdf"
        pdf_path = os.path.join(TICKETS_DIR, pdf_name)
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        return jsonify({
            "message": "Venta registrada con éxito",
            "ticket_id": id_glob,
            "path": pdf_name
        }), 200

    except Exception as e:
        print(f"Error al procesar venta: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # En producción, puedes usar debug=False
    app.run(host='0.0.0.0', port=5000, debug=True)