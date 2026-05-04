import os
import subprocess
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

from models import Ticket, Paciente, ServicioItem
from catalog_manager import cargar_catalogos, generar_nuevos_ids, registrar_venta_csv, guardar_historial_json, leer_historial_ventas
from pdf_generator import generar_ticket_pdf

load_dotenv()
app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

CATALOGOS = cargar_catalogos()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TICKETS_DIR = os.path.join(BASE_DIR, '..', 'Tickets')

if not os.path.exists(TICKETS_DIR): os.makedirs(TICKETS_DIR)

def enviar_a_impresora(ruta_pdf):
    try:
        sumatra_path = os.path.join(BASE_DIR, "SumatraPDF.exe")
        comando = [sumatra_path, "-print-to-default", "-silent", os.path.abspath(ruta_pdf)]
        subprocess.Popen(comando)
        return True
    except Exception as e:
        print(f"Error: {e}"); return False

@app.route("/")
def serve_index(): return send_from_directory(app.static_folder, 'index.html')

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
def get_historial(): return jsonify(leer_historial_ventas())

@app.route("/api/registrar-venta", methods=["POST"])
def registrar():
    data = request.json
    try:
        paciente = Paciente(nombre=data["paciente"]["nombre"], dni=data["paciente"]["dni"])
        destino = data["destino"].capitalize()
        cat = CATALOGOS[destino]
        id_col = "ID_General" if data["destino"].lower() == "general" else "ID_Dental"
        
        items_objs = []
        for it in data["items"]:
            # Cambié 'Categoría' a 'Servicio' o lo que uses en tu Excel (usa la col correspondiente al servicio)
            # Asumo que catalog_manager usa 'Categoría' para agrupar y 'Nombre Específico'
            row = cat[cat[id_col] == it["id"]].iloc[0]
            items_objs.append(ServicioItem(
                categoria=row.get("Categoría", ""),
                nombre_especifico=it["nombre"],
                precio_unitario=Decimal(str(row["Precio Unitario"])),
                cantidad=int(it["cantidad"]),
                descuento=Decimal("0.00")
            ))

        ticket = Ticket(paciente=paciente, items=items_objs, metodo_pago=data["metodo_pago"], destino=destino)
        id_glob, id_esp = generar_nuevos_ids(destino)
        
        # --- LÓGICA DE DESCUENTO ESPECIAL ---
        subtotal_servicios = sum(i.subtotal for i in items_objs)
        monto_descuento = Decimal("0.00")
        
        desc_activo = data.get("descuento_especial_activo", False)
        desc_tipo = data.get("descuento_especial_tipo", "percent")
        desc_valor = Decimal(str(data.get("descuento_especial_valor", 0)))
        desc_razon = data.get("descuento_especial_razon", "")

        if desc_activo and desc_valor > 0:
            if desc_tipo == 'percent':
                monto_descuento = subtotal_servicios * (desc_valor / Decimal("100"))
            else:
                monto_descuento = desc_valor
                
        total_final_calculado = max(Decimal("0.00"), subtotal_servicios - monto_descuento)
        
        # Reemplazamos el total del ticket antes de ir a registrar al CSV
        ticket.total_final = total_final_calculado 
        registrar_venta_csv(ticket, id_glob, id_esp)
        
        venta_final = {
            "id_ticket_global": id_glob,
            "id_ticket_especifico": id_esp,
            "fecha": datetime.now().strftime("%H:%M:%S %d/%m/%y"),
            "paciente": {"nombre": paciente.nombre, "dni": paciente.dni},
            "items": [{"nombre": i.nombre_especifico, "cantidad": i.cantidad, "precio_unitario": str(i.precio_unitario), "subtotal": str(i.subtotal)} for i in items_objs],
            "subtotal_servicios": str(subtotal_servicios),
            "descuento_especial_activo": desc_activo,
            "descuento_especial_tipo": desc_tipo,
            "descuento_especial_valor": str(desc_valor),
            "descuento_especial_monto_soles": str(monto_descuento),
            "descuento_especial_razon": desc_razon,
            "total_final": str(total_final_calculado),
            "metodo_pago": ticket.metodo_pago,
            "destino": ticket.destino,
            "atendido_por": "José Melgar"
        }

        guardar_historial_json(venta_final)
        
        nombre_limpio = "".join(x for x in paciente.nombre if x.isalnum() or x == " ").replace(" ", "_").upper()
        pdf_name = f"{nombre_limpio}_{id_glob}.pdf"
        pdf_path = os.path.join(TICKETS_DIR, pdf_name)
        
        with open(pdf_path, "wb") as f:
            f.write(generar_ticket_pdf(venta_final))
        
        enviar_a_impresora(pdf_path)
        
        return jsonify({"message": "Venta exitosa", "ticket_id": id_glob, "path": pdf_name}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)