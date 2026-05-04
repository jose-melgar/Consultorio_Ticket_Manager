import os
import pandas as pd

# 1. Asegurarnos de que la carpeta "data" exista
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')

if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# 2. Datos estándar para Las Marianas (General)
datos_general = {
    'ID_General': ['LM-001', 'LM-002', 'LM-003'],
    'Categoría': ['CONSULTA', 'LABORATORIO', 'PROCEDIMIENTO'],
    'Nombre Específico': ['Consulta Médica General', 'Hemograma Completo', 'Ecografía Pélvica'],
    'Precio Unitario': [30.00, 75.50, 70.00],
    'Costo': [10.00, 12.30, 0.20]
}
df_general = pd.DataFrame(datos_general)
ruta_general = os.path.join(data_dir, 'Lista de Precios-Las Marianas.xlsx')
df_general.to_excel(ruta_general, index=False)

# 3. Datos estándar para Dental
datos_dental = {
    'ID_Dental': ['DENT-001', 'DENT-002', 'DENT-003'],
    'Categoría': ['CONSULTA ODONTOLOGICA', 'PROCEDIMIENTO', 'INSUMO'],
    'Nombre Específico': ['Consulta Odontológica', 'Curación Simple', 'Anestesia Dental'],
    'Precio Unitario': [20.00, 50.00, 10.00],
    'Costo': [11.00, 15.00, 2.00]
}
df_dental = pd.DataFrame(datos_dental)
ruta_dental = os.path.join(data_dir, 'Lista de Precios-Dental.xlsx')
df_dental.to_excel(ruta_dental, index=False)

print("✅ ¡Archivos Excel creados con éxito en la carpeta 'data'!")