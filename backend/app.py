import os
import pandas as pd
import time
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
    leer_historial_ventas,
    eliminar_ticket_json,
    eliminar_ticket_excel
)
from pdf_generator import generar_ticket_pdf
from escpos_printer import imprimir_ticket_escpos

load_dotenv()
app = Flask(__name__, static_folder='build', static_url_path='/')
CORS(app)

CATALOGOS = cargar_catalogos()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TICKETS_DIR = os.path.join(BASE_DIR, '..', 'Tickets')

if not os.path.exists(TICKETS_DIR): 
    os.makedirs(TICKETS_DIR)

# ==============================================================================
# 🌐 DESTRUCCIÓN DE CACHÉ PARA EVITAR CONGELAMIENTO EN EL NAVEGADOR
# ==============================================================================
@app.route("/")
def serve_index(): 
    response = send_from_directory(app.static_folder, 'index.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/api/catalogos", methods=["GET"])
def get_catalogos():
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
        
        def to_decimal(value):
            if pd.isna(value) or str(value).strip() == "":
                return Decimal("0.00")
            clean_value = str(value).strip().replace(',', '.')
            clean_value = "".join(c for c in clean_value if c.isdigit() or c == '.')
            try: return Decimal(clean_value)
            except: return Decimal("0.00")

        items_objs = []
        for it in data["items"]:
            # --- INTERCEPCIÓN COMODÍN "OTROS" ---
            if it["id"] == "OTROS":
                precio_libre = to_decimal(it.get("precio_unitario", 0))
                item = ServicioItem(
                    categoria="OTROS",
                    nombre_especifico=it["nombre"],
                    precio_unitario=precio_libre,
                    costo_unitario=Decimal("0.00"),
                    cantidad=int(it["cantidad"]),
                    descuento=Decimal("0.00")
                )
                item.costo_lab = Decimal("0.00")
                item.costo_insumo = Decimal("0.00")
                items_objs.append(item)
                continue

            # Búsqueda normal si no es un ítem comodín libre
            row = cat[cat[id_col] == it["id"]].iloc[0]
            precio = to_decimal(row.get("Precio Unitario", 0))
            descuento_p = to_decimal(row.get("Descuento", 0))
            
            if destino.lower() == 'general':
                c_lab = to_decimal(row.get("Costo Laboratorio", 0))
                c_ins = to_decimal(row.get("Costo Insumos", 0))
                costo_para_modelo = c_lab + c_ins
            else:
                costo_para_modelo = to_decimal(row.get("Costo", 0))
                c_lab = Decimal("0.00")
                c_ins = Decimal("0.00")

            item = ServicioItem(
                categoria=row.get("Categoría", ""),
                nombre_especifico=it["nombre"],
                precio_unitario=precio,
                costo_unitario=costo_para_modelo,
                cantidad=int(it["cantidad"]),
                descuento=descuento_p
            )

            if destino.lower() == 'general':
                item.costo_lab = c_lab
                item.costo_insumo = c_ins
            
            items_objs.append(item)

        ticket = Ticket(paciente=paciente, items=items_objs, metodo_pago=data["metodo_pago"], destino=destino)
        id_glob, id_esp = generar_nuevos_ids(destino)
        
        subtotal_servicios = sum(i.subtotal for i in items_objs)
        desc_valor = to_decimal(data.get("descuento_especial_valor", 0))
        monto_descuento_especial = to_decimal(data.get("descuento_especial_monto_soles", 0))
        
        desc_activo = data.get("descuento_especial_activo", False)
        desc_tipo = data.get("descuento_especial_tipo", "percent")
        desc_razon = data.get("descuento_especial_razon", "")
                
        total_final_calculado = max(Decimal("0.00"), subtotal_servicios - monto_descuento_especial)
        ticket.total_final = total_final_calculado 
        
        # --- INYECCIÓN DE DATOS DE MÚLTIPLES MÉTODOS DE PAGO ---
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
            "pago_con": str(data.get("pago_con", 0)),
            "vuelto": str(data.get("vuelto", 0)),
            "desglose_pagos": data.get("desglose_pagos", []),
            "destino": ticket.destino,
            "atendido_por": "José Melgar"
        }

        # Guarda en el Excel correspondiente (General -> Las Marianas | Dental -> Dental)
        registrar_venta_excel(ticket, id_glob, id_esp, venta_final)
        guardar_historial_json(venta_final)
        
        nombre_limpio = "".join(x for x in paciente.nombre if x.isalnum() or x == " ").replace(" ", "_").upper()
        pdf_name = f"{nombre_limpio}_{id_glob}.pdf"
        pdf_path = os.path.join(TICKETS_DIR, pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(generar_ticket_pdf(venta_final))
        
        # Impresión térmica en físico
        imprimir_ticket_escpos(venta_final)
        time.sleep(2.5)
        imprimir_ticket_escpos(venta_final)
        
        return jsonify({"message": "Venta exitosa", "ticket_id": id_glob, "path": pdf_name}), 200

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/eliminar-ticket/<id_global>", methods=["DELETE"])
def eliminar_ticket(id_global):
    try:
        json_ok = eliminar_ticket_json(id_global)
        excel_ok = eliminar_ticket_excel(id_global)
        
        pdf_ok = False
        if os.path.exists(TICKETS_DIR):
            for archivo in os.listdir(TICKETS_DIR):
                if archivo.endswith(f"_{id_global}.pdf"):
                    os.remove(os.path.join(TICKETS_DIR, archivo))
                    pdf_ok = True
                    break
                    
        if json_ok or excel_ok:
            return jsonify({
                "message": f"Ticket {id_global} removido con éxito del sistema.",
                "historial_json": json_ok,
                "libro_excel": excel_ok,
                "archivo_pdf": pdf_ok
            }), 200
        else:
            return jsonify({"error": "El ID de ticket no existe en el sistema."}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/reimprimir-ticket", methods=["POST"])
def reimprimir_ticket():
    data = request.json
    id_global = data.get("id_ticket_global")
    cantidad_copias = int(data.get("cantidad", 1))

    try:
        tickets = leer_historial_ventas()
        
        ticket_encontrado = None
        for t in tickets:
            if t["id_ticket_global"] == id_global:
                ticket_encontrado = t
                break
        
        if not ticket_encontrado:
            return jsonify({"error": "Ticket no encontrado en el archivo de ventas."}), 404

        for i in range(cantidad_copias):
            imprimir_ticket_escpos(ticket_encontrado) 
            if i < cantidad_copias - 1:
                time.sleep(2.5)

        return jsonify({"message": f"Se enviaron {cantidad_copias} copias correctamente."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)