import os
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

from models import Ticket, Paciente, ServicioItem
from catalog_manager import (
    cargar_catalogos, 
    generar_nuevos_ids, 
    registrar_venta_excel, 
    guardar_historial_json, 
    leer_historial_ventas
)
from pdf_generator import generar_ticket_pdf
from escpos_printer import imprimir_ticket_escpos

load_dotenv()
app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

# Cargar los catálogos en memoria al iniciar el servidor
CATALOGOS = cargar_catalogos()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TICKETS_DIR = os.path.join(BASE_DIR, '..', 'Tickets')

if not os.path.exists(TICKETS_DIR): 
    os.makedirs(TICKETS_DIR)

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
    # fillna(0) asegura que si hay celdas vacías en Costo o Descuento, envíe un 0 al frontend
    return jsonify({
        "general": CATALOGOS["General"].fillna(0).to_dict(orient="records"),
        "dental": CATALOGOS["Dental"].fillna(0).to_dict(orient="records")
    })

@app.route("/api/tickets", methods=["GET"])
def get_historial(): 
    return jsonify(leer_historial_ventas())

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
            # Buscar el producto en el dataframe de pandas
            row = cat[cat[id_col] == it["id"]].iloc[0]
            
            # Extraemos el costo unitario (Para ganancias contables)
            costo = row.get("Costo", 0)
            if pd.isna(costo): costo = 0

            # Extraemos el descuento individual del Excel
            descuento_item = row.get("Descuento", 0)
            if pd.isna(descuento_item): descuento_item = 0

            items_objs.append(ServicioItem(
                categoria=row.get("Categoría", ""),
                nombre_especifico=it["nombre"],
                precio_unitario=Decimal(str(row["Precio Unitario"])),
                costo_unitario=Decimal(str(costo)),
                cantidad=int(it["cantidad"]),
                descuento=Decimal(str(descuento_item)) # Descuento por producto
            ))

        ticket = Ticket(paciente=paciente, items=items_objs, metodo_pago=data["metodo_pago"], destino=destino)
        id_glob, id_esp = generar_nuevos_ids(destino)
        
        # --- LÓGICA DE DESCUENTO ESPECIAL ---
        # Sumamos los subtotales (que ya tienen el descuento individual aplicado)
        subtotal_servicios = sum(i.subtotal for i in items_objs)
        monto_descuento_especial = Decimal("0.00")
        
        desc_activo = data.get("descuento_especial_activo", False)
        desc_tipo = data.get("descuento_especial_tipo", "percent")
        desc_valor = Decimal(str(data.get("descuento_especial_valor", 0)))
        desc_razon = data.get("descuento_especial_razon", "")

        if desc_activo and desc_valor > 0:
            if desc_tipo == 'percent':
                monto_descuento_especial = subtotal_servicios * (desc_valor / Decimal("100"))
            else:
                monto_descuento_especial = desc_valor
                
        total_final_calculado = max(Decimal("0.00"), subtotal_servicios - monto_descuento_especial)
        
        # Asignamos el total calculado al ticket mediante el setter
        ticket.total_final = total_final_calculado 
        
        # Preparamos el diccionario de venta final
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
            "descuento_especial_monto_soles": str(monto_descuento_especial),
            "descuento_especial_razon": desc_razon,
            "observaciones": data.get("observaciones", ""),
            "total_final": str(total_final_calculado),
            "metodo_pago": ticket.metodo_pago,
            "destino": ticket.destino,
            "atendido_por": "José Melgar"
        }

        # Guardar en el Excel Maestro de Contabilidad (Saldos y Ganancias)
        registrar_venta_excel(ticket, id_glob, id_esp, venta_final)
        
        # Guardar en el historial de JSON para el Frontend
        guardar_historial_json(venta_final)
        
        # Generar y guardar el respaldo en PDF digital (Sin mandarlo a Sumatra)
        nombre_limpio = "".join(x for x in paciente.nombre if x.isalnum() or x == " ").replace(" ", "_").upper()
        pdf_name = f"{nombre_limpio}_{id_glob}.pdf"
        pdf_path = os.path.join(TICKETS_DIR, pdf_name)
        
        with open(pdf_path, "wb") as f:
            f.write(generar_ticket_pdf(venta_final))
        
        # --- NUEVA IMPRESIÓN FÍSICA VÍA ESC/POS ---
        imprimir_ticket_escpos(venta_final)
        
        return jsonify({"message": "Venta exitosa", "ticket_id": id_glob, "path": pdf_name}), 200

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)