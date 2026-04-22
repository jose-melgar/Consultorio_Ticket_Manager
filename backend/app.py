import os
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

# Tus módulos internos
from models import Ticket, Paciente, ServicioItem
from catalog_manager import (
    cargar_catalogos, generar_nuevos_ids, registrar_venta_csv, 
    guardar_historial_json, leer_historial_ventas
)
from pdf_generator import generar_ticket_pdf

load_dotenv()

app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

CATALOGOS = cargar_catalogos()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TICKETS_DIR = os.path.join(BASE_DIR, '..', 'Tickets')

if not os.path.exists(TICKETS_DIR):
    os.makedirs(TICKETS_DIR)

def enviar_a_impresora(ruta_pdf):
    """Usa SumatraPDF para una impresión silenciosa perfecta en ticketeras"""
    try:
        abs_path = os.path.abspath(ruta_pdf)
        
        # Como pegaste SumatraPDF.exe en la misma carpeta que app.py, lo buscamos ahí
        sumatra_path = os.path.join(BASE_DIR, "SumatraPDF.exe")
        
        if not os.path.exists(sumatra_path):
            print("❌ Error: No se encontró SumatraPDF.exe en la carpeta backend.")
            return False

        # Comando de Sumatra: -print-to-default lo manda a la POS-58 silenciosamente
        comando = [
            sumatra_path, 
            "-print-to-default", 
            "-silent", 
            abs_path
        ]
        
        subprocess.Popen(comando)
        print(f"✅ Ticket enviado a impresión usando SumatraPDF")
        return True
        
    except Exception as e:
        print(f"❌ Error crítico al enviar a impresión: {e}")
        return False

# --- RUTAS ---

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

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
    try:
        # Lógica de creación de ticket
        paciente = Paciente(nombre=data["paciente"]["nombre"], dni=data["paciente"]["dni"])
        items_objs = []
        destino = data["destino"].capitalize()
        cat = CATALOGOS[destino]
        id_col = "ID_General" if data["destino"].lower() == "general" else "ID_Dental"

        for it in data["items"]:
            row = cat[cat[id_col] == it["id"]].iloc[0]
            items_objs.append(ServicioItem(
                categoria=row["Categoría"],
                nombre_especifico=it["nombre"],
                precio_unitario=Decimal(str(row["Precio Unitario"])),
                cantidad=int(it["cantidad"]),
                descuento=Decimal("0.00")
            ))

        ticket = Ticket(paciente=paciente, items=items_objs, metodo_pago=data["metodo_pago"], destino=destino)
        id_glob, id_esp = generar_nuevos_ids(destino)
        registrar_venta_csv(ticket, id_glob, id_esp)
        
        venta_final = {
            "id_ticket_global": id_glob,
            "id_ticket_especifico": id_esp,
            "fecha": datetime.now().strftime("%H:%M:%S %d/%m/%y"),
            "paciente": {"nombre": paciente.nombre, "dni": paciente.dni},
            "items": [{"nombre": i.nombre_especifico, "cantidad": i.cantidad, "precio_unitario": i.precio_unitario, "subtotal": i.subtotal} for i in items_objs],
            "total_final": ticket.total_final,
            "metodo_pago": ticket.metodo_pago,
            "destino": ticket.destino,
            "atendido_por": "José Melgar"
        }

        guardar_historial_json(venta_final)
        
        # --- GENERAR NOMBRE DE ARCHIVO PERSONALIZADO ---
        # Limpia caracteres especiales para que Windows no tenga problemas al guardar
        nombre_paciente_limpio = "".join(x for x in venta_final['paciente']['nombre'] if x.isalnum() or x == " ").replace(" ", "_").upper()
        pdf_name = f"{nombre_paciente_limpio}_{id_glob}.pdf"
        
        # Generar y guardar el PDF
        pdf_bytes = generar_ticket_pdf(venta_final)
        pdf_path = os.path.join(TICKETS_DIR, pdf_name)
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        # ACCIÓN: IMPRIMIR
        enviar_a_impresora(pdf_path)
        
        return jsonify({
            "message": "Venta exitosa e imprimiendo", 
            "ticket_id": id_glob,
            "path": pdf_name
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)