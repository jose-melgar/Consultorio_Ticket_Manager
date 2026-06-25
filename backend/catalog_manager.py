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
    Registra la venta e inyecta la fórmula de Excel para arrastrar saldos automáticos.
    """
    columnas = [
        "Fecha", "nota de venta", "Pago", "Nombre", "Descripción", "A cuenta", 
        "ingresos", "Egresos - gastos", "LABORATORIO", "Insumos de lab", 
        "Ganancia", "Saldos", "observaciones"
    ]
    
    fecha = datetime.now().strftime("%d.%m.%y")
    num_nota = f"{id_global} | {id_especifico}"
    pago = ticket.metodo_pago.capitalize()
    nombre_paciente = ticket.paciente.nombre.upper()

    descripcion_items = ", ".join([
        f"{item.nombre_especifico} {item.cantidad}" if item.cantidad >= 2 else item.nombre_especifico 
        for item in ticket.items
    ])
    
    ingresos = float(ticket.total_final)
    egresos_servicios = 0.0
    egresos_insumos = 0.0
    
    if ticket.destino.lower() == 'dental':
        for item in ticket.items:
            if "insumo" in item.categoria.lower() or "medicamento" in item.categoria.lower():
                egresos_insumos += float(item.costo_unitario) * item.cantidad
            else:
                egresos_servicios += float(item.costo_unitario) * item.cantidad
    else:
        for item in ticket.items:
            egresos_servicios += float(getattr(item, 'costo_lab', 0)) * item.cantidad
            egresos_insumos += float(getattr(item, 'costo_insumo', 0)) * item.cantidad

    ganancia = ingresos - (egresos_servicios + egresos_insumos)

    obs = venta_final.get('observaciones', '')
    if venta_final.get('descuento_especial_activo'):
        obs += f" | Desc: {venta_final['descuento_especial_razon']}"

    nueva_fila = {
        "Fecha": fecha,
        "nota de venta": num_nota,
        "Pago": pago,
        "Nombre": nombre_paciente,
        "Descripción": descripcion_items,
        "A cuenta": 0,
        "ingresos": ingresos,
        "Egresos - gastos": 0,
        "LABORATORIO": egresos_servicios,
        "Insumos de lab": egresos_insumos,
        "Ganancia": ganancia,
        "Saldos": "", 
        "observaciones": obs
    }

    if not os.path.exists(LIBRO_CONTABLE):
        df = pd.DataFrame([nueva_fila], columns=columnas)
        df.loc[0, "Saldos"] = "=K2"
        df.to_excel(LIBRO_CONTABLE, index=False)
    else:
        wb = load_workbook(LIBRO_CONTABLE)
        ws = wb.active
        start_row = ws.max_row + 1
        wb.close()
        
        formula_saldo = f"=L{start_row-1}+K{start_row}"

        with pd.ExcelWriter(LIBRO_CONTABLE, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            df_nuevo = pd.DataFrame([nueva_fila], columns=columnas)
            df_nuevo.loc[0, "Saldos"] = formula_saldo
            df_nuevo.to_excel(writer, index=False, header=False, startrow=start_row-1)

# --- FUNCIÓN REINCORPORADA: GUARDA CADA COMPRA EN EL HISTORIAL DIGITAL ---
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

# --- FUNCIONES DE ANULACIÓN Y ELIMINACIÓN ---
def eliminar_ticket_json(id_global: str) -> bool:
    if not os.path.exists(HISTORIAL_JSON): return False
    with open(HISTORIAL_JSON, 'r', encoding='utf-8') as f:
        historial = json.load(f)
    
    nuevo_historial = [t for t in historial if t["id_ticket_global"] != id_global]
    if len(historial) != len(nuevo_historial):
        with open(HISTORIAL_JSON, 'w', encoding='utf-8') as f:
            json.dump(nuevo_historial, f, indent=4, ensure_ascii=False)
        return True
    return False

def eliminar_ticket_excel(id_global: str) -> bool:
    if not os.path.exists(LIBRO_CONTABLE): return False
    wb = load_workbook(LIBRO_CONTABLE)
    ws = wb.active
    
    fila_a_eliminar = None
    for r in range(2, ws.max_row + 1):
        if id_global in str(ws.cell(row=r, column=2).value or ""):
            fila_a_eliminar = r
            break
            
    if fila_a_eliminar:
        ws.delete_rows(fila_a_eliminar)
        
        # Reestructuramos fórmulas para arrastrar saldos automáticos
        for r in range(fila_a_eliminar, ws.max_row + 1):
            if r == 2:
                ws.cell(row=r, column=12, value="=K2")
            else:
                ws.cell(row=r, column=12, value=f"=L{r-1}+K{r}")
                
        wb.save(LIBRO_CONTABLE)
        wb.close()
        return True
        
    wb.close()
    return False

def leer_historial_ventas():
    if not os.path.exists(HISTORIAL_JSON): return []
    with open(HISTORIAL_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)