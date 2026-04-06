import pandas as pd
import os
import json
from datetime import datetime
from typing import List, Dict
from models import Ticket

# --- CONSTANTES DE RUTAS ---
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CATALOGO_GENERAL = os.path.join(DATA_DIR, "Lista de Precios-Las Marianas.xlsx")
CATALOGO_DENTAL = os.path.join(DATA_DIR, "Lista de Precios-Dental.xlsx")
REGISTRO_GENERAL = os.path.join(DATA_DIR, "Ventas-Las Marianas.xlsx")
REGISTRO_DENTAL = os.path.join(DATA_DIR, "Ventas-Dental.xlsx")
HISTORIAL_VENTAS_JSON = os.path.join(DATA_DIR, "ventas.json")

# --- GESTIÓN DE CATÁLOGOS ---
def _crear_catalogo_si_no_existe(path: str, datos_prueba: pd.DataFrame):
    if not os.path.exists(path):
        print(f"Advertencia: Catálogo no encontrado en '{path}'. Creando archivo de prueba.")
        os.makedirs(DATA_DIR, exist_ok=True)
        datos_prueba.to_excel(path, index=False)

def inicializar_catalogos():
    """Verifica y crea catálogos con datos de prueba, incluyendo descuentos."""
    datos_general = pd.DataFrame({
        "ID_General": ["LM-001", "LM-002", "LM-003", "LM-004"],
        "Categoría": ["Consulta", "Insumo", "Insumo", "Procedimiento"],
        "Nombre Específico": ["Consulta General", "Jeringa 5ml", "Venda Elástica", "Curación Simple"],
        "Precio Unitario": [50.0, 2.5, 5.0, 30.0],
        "Descuento": [10.0, 0.0, 0.5, 5.0]  # <-- DESCUENTOS AÑADIDOS
    })
    
    datos_dental = pd.DataFrame({
        "ID_Dental": ["DEN-001", "DEN-002", "DEN-003"],
        "Categoría": ["Consulta", "Procedimiento", "Insumo"],
        "Nombre Específico": ["Consulta Dental", "Limpieza Profunda", "Anestesia Local"],
        "Precio Unitario": [80.0, 120.0, 25.0],
        "Descuento": [15.0, 20.0, 0.0]  # <-- DESCUENTOS AÑADIDOS
    })
    
    _crear_catalogo_si_no_existe(CATALOGO_GENERAL, datos_general)
    _crear_catalogo_si_no_existe(CATALOGO_DENTAL, datos_dental)
    
    # Inicializar el archivo de historial de ventas si no existe
    if not os.path.exists(HISTORIAL_VENTAS_JSON):
        with open(HISTORIAL_VENTAS_JSON, 'w') as f:
            json.dump([], f)
            
    print("Verificación de catálogos y archivos de datos completada.")

def cargar_catalogos() -> dict:
    inicializar_catalogos()
    try:
        df_general = pd.read_excel(CATALOGO_GENERAL)
        df_dental = pd.read_excel(CATALOGO_DENTAL)
        return {"General": df_general, "Dental": df_dental}
    except Exception as e:
        print(f"Error fatal al cargar catálogos: {e}")
        return {}

# --- GESTIÓN DEL HISTORIAL DE VENTAS (JSON) ---
def leer_historial_ventas() -> List[Dict]:
    """Lee todas las ventas del archivo JSON."""
    try:
        with open(HISTORIAL_VENTAS_JSON, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def guardar_nueva_venta(venta_data: Dict):
    """Añade una nueva venta al historial JSON."""
    historial = leer_historial_ventas()
    historial.append(venta_data)
    with open(HISTORIAL_VENTAS_JSON, 'w') as f:
        json.dump(historial, f, indent=4)

ID_COUNTER_FILE = os.path.join(DATA_DIR, "id_counters.json")

def _get_id_counters():
    """Lee los contadores de IDs desde un archivo JSON. Si no existe, los crea."""
    try:
        with open(ID_COUNTER_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Valores iniciales si el archivo no existe o está vacío
        return {"global": 0, "general": 0, "dental": 0}

def _save_id_counters(counters):
    """Guarda los contadores de IDs actualizados en el archivo JSON."""
    with open(ID_COUNTER_FILE, 'w') as f:
        json.dump(counters, f)

def generar_nuevos_ids(destino: str):
    """Genera un nuevo ID global y uno específico, y actualiza los contadores."""
    counters = _get_id_counters()
    
    # Incrementar contadores
    counters["global"] += 1
    if destino.lower() == 'general':
        counters["general"] += 1
        id_especifico = f'LM-{counters["general"]:04d}'
    else: # Dental
        counters["dental"] += 1
        id_especifico = f'DEN-{counters["dental"]:04d}'
        
    id_global = f'TK-{counters["global"]:04d}'
    
    # Guardar los nuevos valores
    _save_id_counters(counters)
    
    return id_global, id_especifico

# --- FUNCIÓN DE REGISTRO EN EXCEL ---
def registrar_venta_excel(ticket: 'Ticket'):
    """
    Registra una venta en el archivo Excel correspondiente y devuelve los IDs generados.
    """
    id_global, id_especifico = generar_nuevos_ids(ticket.destino)
    
    # Determinar el archivo de registro y el nombre de la columna de ID
    if ticket.destino.lower() == 'general':
        archivo_registro = REGISTRO_GENERAL
        id_col_name = 'ID General'
    else:
        archivo_registro = REGISTRO_DENTAL
        id_col_name = 'ID Dental'

    # Preparar los datos para la nueva fila del Excel
    # El ticket puede tener varios items, los concatenamos en una sola celda
    items_str = ", ".join([f"{item.cantidad}x {item.nombre_especifico}" for item in ticket.items])
    
    nueva_fila = {
        'Fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'ID Global': id_global,
        id_col_name: id_especifico,
        'Paciente': ticket.paciente.nombre,
        'DNI': ticket.paciente.dni,
        'Items': items_str,
        'Monto Bruto': ticket.total_bruto,
        'Descuento Total': ticket.descuento_total,
        'Precio Final': ticket.total_final,
        'Método de Pago': ticket.metodo_pago
    }
    
    try:
        # Leer el archivo existente o crear un DataFrame nuevo si no existe
        if os.path.exists(archivo_registro):
            df = pd.read_excel(archivo_registro)
        else:
            df = pd.DataFrame(columns=nueva_fila.keys())

        # Añadir la nueva fila y guardar el archivo
        # `pd.concat` es más seguro para añadir filas a un DataFrame
        nueva_fila_df = pd.DataFrame([nueva_fila])
        df = pd.concat([df, nueva_fila_df], ignore_index=True)
        
        # Guardar el DataFrame actualizado en el archivo Excel
        df.to_excel(archivo_registro, index=False)
        print(f"Venta registrada exitosamente en {archivo_registro}")

    except Exception as e:
        # Manejo de errores, como el archivo estando abierto
        print(f"ERROR: No se pudo escribir en el archivo {archivo_registro}. ¿Está abierto por otro programa? Detalle: {e}")
        # Aquí podrías relanzar la excepción para que el endpoint la capture si prefieres
        raise e

    return id_global, id_especifico