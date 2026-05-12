import pandas as pd
import os
import json
from datetime import datetime
from typing import List, Dict
from decimal import Decimal
from openpyxl import load_workbook

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CATALOGO_GENERAL = os.path.join(DATA_DIR, "Lista de Precios-Las Marianas.xlsx")
CATALOGO_DENTAL = os.path.join(DATA_DIR, "Lista de Precios-Dental.xlsx")
HISTORIAL_JSON = os.path.join(DATA_DIR, "ventas.json")
ID_COUNTER_FILE = os.path.join(DATA_DIR, "id_counters.json")
LIBRO_CONTABLE = os.path.join(DATA_DIR, "Contabilidad_Marianas.xlsx")

def cargar_catalogos():
    return {
        "General": pd.read_excel(CATALOGO_GENERAL),
        "Dental": pd.read_excel(CATALOGO_DENTAL)
    }

def generar_nuevos_ids(destino: str):
    if not os.path.exists(ID_COUNTER_FILE):
        counters = {"global": 0, "general": 0, "dental": 0}
    else:
        with open(ID_COUNTER_FILE, 'r') as f:
            counters = json.load(f)

    counters["global"] += 1
    if destino.lower() == 'general':
        counters["general"] += 1
        id_esp = f'LM-{counters["general"]:04d}'
    else:
        counters["dental"] += 1
        id_esp = f'DEN-{counters["dental"]:04d}'
    
    id_glob = f'TK-{counters["global"]:04d}'
    with open(ID_COUNTER_FILE, 'w') as f:
        json.dump(counters, f)
    return id_glob, id_esp

def registrar_venta_excel(ticket, id_global, id_especifico, venta_final):
    """
    Registra la venta en el formato de Contabilidad (Libro de Ingresos y Egresos).
    """
    columnas = [
        "Fecha", "nota de venta", "Pago", "Descripción", "A cuenta", 
        "ingresos", "Egresos - gastos", "LABORATORIO", "Insumos de lab", 
        "Ganancia", "Saldos", "observaciones"
    ]
    
    fecha = datetime.now().strftime("%d.%m.%y")
    num_nota = f"{id_global} | {id_especifico}"
    
    pago = ticket.metodo_pago.capitalize()

    descripcion_items = ", ".join([f"{item.nombre_especifico} {item.cantidad}" for item in ticket.items])
    ingresos = float(ticket.total_final)
    
    egresos_servicios = 0.0
    egresos_insumos = 0.0
    
    # --- NUEVA LÓGICA DE COSTOS POR DESTINO ---
    if ticket.destino.lower() == 'dental':
        # Lógica original para Dental: se basa en palabras clave de la categoría
        for item in ticket.items:
            if "insumo" in item.categoria.lower() or "medicamento" in item.categoria.lower():
                egresos_insumos += float(item.costo_unitario) * item.cantidad
            else:
                egresos_servicios += float(item.costo_unitario) * item.cantidad
    else:
        # Lógica para Las Marianas (General): usa columnas específicas
        for item in ticket.items:
            # costo_lab y costo_insumo deben ser asignados en app.py al leer el Excel
            egresos_servicios += float(getattr(item, 'costo_lab', 0)) * item.cantidad
            egresos_insumos += float(getattr(item, 'costo_insumo', 0)) * item.cantidad

    # Cálculo de ganancia: ingresos - suma de ambos costos
    ganancia = ingresos - (egresos_servicios + egresos_insumos)
    
    # Calcular Saldo
    saldo_anterior = 0.0
    if os.path.exists(LIBRO_CONTABLE):
        try:
            df_existente = pd.read_excel(LIBRO_CONTABLE)
            if not df_existente.empty and pd.notna(df_existente["Saldos"].iloc[-1]):
                saldo_anterior = float(df_existente["Saldos"].iloc[-1])
        except Exception as e:
            print(f"Aviso al leer Saldo: {e}")
            
    nuevo_saldo = saldo_anterior + ganancia 

    obs = venta_final.get('observaciones', '')
    if venta_final.get('descuento_especial_activo'):
        obs += f" | Desc: {venta_final['descuento_especial_razon']}"

    nueva_fila = {
        "Fecha": fecha,
        "nota de venta": num_nota,
        "Pago": pago,
        "Descripción": descripcion_items,
        "A cuenta": 0,
        "ingresos": ingresos,
        "Egresos - gastos": 0,
        "LABORATORIO": egresos_servicios,
        "Insumos de lab": egresos_insumos,
        "Ganancia": ganancia,
        "Saldos": nuevo_saldo,
        "observaciones": obs
    }

    if not os.path.exists(LIBRO_CONTABLE):
        df = pd.DataFrame([nueva_fila], columns=columnas)
        df.to_excel(LIBRO_CONTABLE, index=False)
    else:
        with pd.ExcelWriter(LIBRO_CONTABLE, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            df_nuevo = pd.DataFrame([nueva_fila])
            start_row = writer.sheets['Sheet1'].max_row
            df_nuevo.to_excel(writer, index=False, header=False, startrow=start_row)

def guardar_historial_json(venta_data):
    def default_serializer(obj):
        if isinstance(obj, Decimal): return str(obj)
        raise TypeError
    
    historial = []
    if os.path.exists(HISTORIAL_JSON):
        with open(HISTORIAL_JSON, 'r', encoding='utf-8') as f:
            historial = json.load(f)
    
    historial.append(venta_data)
    with open(HISTORIAL_JSON, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=4, default=default_serializer, ensure_ascii=False)

def leer_historial_ventas():
    if not os.path.exists(HISTORIAL_JSON): return []
    with open(HISTORIAL_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)