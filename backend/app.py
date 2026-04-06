from flask import Flask, jsonify, request
from flask_cors import CORS
from decimal import Decimal
import io
import os
from models import Ticket, Paciente, ServicioItem
from catalog_manager import (
    cargar_catalogos, generar_nuevos_ids, registrar_venta_csv, 
    guardar_historial_json, leer_historial_ventas
)
from pdf_generator import generar_ticket_pdf
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN DE RUTAS ---
CATALOGOS = cargar_catalogos()
BASE_DIR = os.path.dirname(__file__)
TICKETS_DIR = os.path.join(BASE_DIR, '..', 'Tickets')

# Asegurar que la carpeta Tickets exista
if not os.path.exists(TICKETS_DIR):
    os.makedirs(TICKETS_DIR)

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
        paciente = Paciente(nombre=data["paciente"]["nombre"], dni=data["paciente"]["dni"])
        items_objs = []
        destino = data["destino"].capitalize()
        cat = CATALOGOS[destino]
        id_col = "ID_General" if data["destino"] == "general" else "ID_Dental"

        for it in data["items"]:
            row = cat[cat[id_col] == it["id"]].iloc[0]
            items_objs.append(ServicioItem(
                categoria=row["Categoría"],
                nombre_especifico=it["nombre"],
                precio_unitario=Decimal(str(row["Precio Unitario"])),
                cantidad=int(it["cantidad"]),
                descuento=Decimal("0.00") # Eliminado manejo de descuento manual
            ))

        ticket = Ticket(paciente=paciente, items=items_objs, metodo_pago=data["metodo_pago"], destino=destino)
        
        id_glob, id_esp = generar_nuevos_ids(destino)
        registrar_venta_csv(ticket, id_glob, id_esp)
        
        venta_final = {
            "id_ticket_global": id_glob,
            "id_ticket_especifico": id_esp,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "paciente": {"nombre": paciente.nombre, "dni": paciente.dni},
            "items": [{"nombre": i.nombre_especifico, "cantidad": i.cantidad, "precio_unitario": i.precio_unitario, "subtotal": i.subtotal} for i in items_objs],
            "total_final": ticket.total_final,
            "metodo_pago": ticket.metodo_pago,
            "destino": ticket.destino
        }

        guardar_historial_json(venta_final)
        
        # Generar PDF y GUARDAR en la carpeta Tickets en lugar de enviarlo
        pdf_bytes = generar_ticket_pdf(venta_final)
        pdf_path = os.path.join(TICKETS_DIR, f"{id_glob}.pdf")
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        return jsonify({
            "message": "Venta registrada con éxito",
            "ticket_id": id_glob,
            "path": pdf_path
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)