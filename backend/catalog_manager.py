import pandas as pd
import os
import json
from datetime import datetime
from typing import List, Dict
from decimal import Decimal

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CATALOGO_GENERAL = os.path.join(DATA_DIR, "Lista de Precios-Las Marianas.xlsx")
CATALOGO_DENTAL = os.path.join(DATA_DIR, "Lista de Precios-Dental.xlsx")
HISTORIAL_JSON = os.path.join(DATA_DIR, "ventas.json")
ID_COUNTER_FILE = os.path.join(DATA_DIR, "id_counters.json")

# Archivos de registro en CSV para evitar bloqueos de Excel
REGISTRO_CSV_GEN = os.path.join(DATA_DIR, "Ventas-Las Marianas.csv")
REGISTRO_CSV_DEN = os.path.join(DATA_DIR, "Ventas-Dental.csv")

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

def registrar_venta_csv(ticket, id_global, id_especifico):
    archivo = REGISTRO_CSV_GEN if ticket.destino.lower() == 'general' else REGISTRO_CSV_DEN
    
    nueva_fila = {
        'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'ID_Global': id_global,
        'ID_Especifico': id_especifico,
        'Paciente': ticket.paciente.nombre,
        'DNI': ticket.paciente.dni,
        'Monto_Final': float(ticket.total_final),
        'Metodo_Pago': ticket.metodo_pago
    }
    
    df = pd.DataFrame([nueva_fila])
    header = not os.path.exists(archivo)
    df.to_csv(archivo, mode='a', index=False, header=header, encoding='utf-8-sig')

def guardar_historial_json(venta_data):
    # Convertimos Decimals a string para que JSON sea compatible
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