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
        
        # Función para limpiar y convertir a Decimal con seguridad (evita InvalidOperation)
        def to_decimal(value):
            if pd.isna(value) or str(value).strip() == "":
                return Decimal("0.00")
            # Limpieza de caracteres: manejamos comas, espacios y símbolos
            clean_value = str(value).strip().replace(',', '.')
            clean_value = "".join(c for c in clean_value if c.isdigit() or c == '.')
            try:
                return Decimal(clean_value)
            except:
                return Decimal("0.00")

        items_objs = []
        for it in data["items"]:
            # Obtener la fila del Excel mediante el ID
            row = cat[cat[id_col] == it["id"]].iloc[0]
            
            # Limpiar valores comunes
            precio = to_decimal(row.get("Precio Unitario", 0))
            descuento_p = to_decimal(row.get("Descuento", 0))
            
            # Lógica de costos diferenciada por Destino
            if destino.lower() == 'general':
                # Extraemos columnas específicas de Las Marianas
                c_lab = to_decimal(row.get("Costo Laboratorio", 0))
                c_ins = to_decimal(row.get("Costo Insumos", 0))
                # El costo_unitario para el modelo es la suma (para evitar el TypeError)
                costo_para_modelo = c_lab + c_ins
            else:
                # Dental usa la columna "Costo" tradicional
                costo_para_modelo = to_decimal(row.get("Costo", 0))
                c_lab = Decimal("0.00")
                c_ins = Decimal("0.00")

            # Crear el objeto del ítem (cumpliendo con todos los argumentos requeridos)
            item = ServicioItem(
                categoria=row.get("Categoría", ""),
                nombre_especifico=it["nombre"],
                precio_unitario=precio,
                costo_unitario=costo_para_modelo,
                cantidad=int(it["cantidad"]),
                descuento=descuento_p
            )

            # Inyectar propiedades extra para que catalog_manager las use en el Excel
            if destino.lower() == 'general':
                item.costo_lab = c_lab
                item.costo_insumo = c_ins
            
            items_objs.append(item)

        ticket = Ticket(paciente=paciente, items=items_objs, metodo_pago=data["metodo_pago"], destino=destino)
        id_glob, id_esp = generar_nuevos_ids(destino)
        
        # Cálculo de subtotales y Descuento Especial
        subtotal_servicios = sum(i.subtotal for i in items_objs)
        desc_valor = to_decimal(data.get("descuento_especial_valor", 0))
        monto_descuento_especial = Decimal("0.00")
        
        desc_activo = data.get("descuento_especial_activo", False)
        desc_tipo = data.get("descuento_especial_tipo", "percent")
        desc_razon = data.get("descuento_especial_razon", "")

        if desc_activo and desc_valor > 0:
            if desc_tipo == 'percent':
                monto_descuento_especial = subtotal_servicios * (desc_valor / Decimal("100"))
            else:
                monto_descuento_especial = desc_valor
                
        # Calcular total final asegurando que no sea negativo
        total_final_calculado = max(Decimal("0.00"), subtotal_servicios - monto_descuento_especial)
        ticket.total_final = total_final_calculado 
        
        # Estructura para el historial y documentos
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

        # Procesos de guardado e impresión
        registrar_venta_excel(ticket, id_glob, id_esp, venta_final)
        guardar_historial_json(venta_final)
        
        # Respaldo PDF
        nombre_limpio = "".join(x for x in paciente.nombre if x.isalnum() or x == " ").replace(" ", "_").upper()
        pdf_name = f"{nombre_limpio}_{id_glob}.pdf"
        pdf_path = os.path.join(TICKETS_DIR, pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(generar_ticket_pdf(venta_final))
        
        # Impresión térmica directa
        imprimir_ticket_escpos(venta_final)
        
        return jsonify({"message": "Venta exitosa", "ticket_id": id_glob, "path": pdf_name}), 200

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)