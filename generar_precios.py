"""Creates demo catalogs only in a NEW directory; never overwrites customer files."""
import argparse
from pathlib import Path
from openpyxl import Workbook

GENERAL = 'Lista de Precios-Las Marianas.xlsx'
DENTAL = 'Lista de Precios-Dental.xlsx'

def generate(directory):
    target = Path(directory).resolve()
    # Exclusive directory creation prevents accidental overwrite or partial replacement.
    target.mkdir(parents=True, exist_ok=False)
    sheets = {
        GENERAL: [['ID_General', 'Categoría', 'Nombre Específico', 'Precio Unitario', 'Costo Laboratorio', 'Costo Insumos', 'Descuento'],
                  ['LM-001', 'CONSULTA', 'Consulta Médica General', 30, 0, 10, 0],
                  ['LM-002', 'LABORATORIO', 'Hemograma Completo', 75.50, 12.30, 0, 0],
                  ['LM-003', 'PROCEDIMIENTO', 'Ecografía Pélvica', 70, 0, 0.20, 0]],
        DENTAL: [['ID_Dental', 'Categoría', 'Nombre Específico', 'Precio Unitario', 'Costo', 'Descuento'],
                 ['DENT-001', 'CONSULTA ODONTOLOGICA', 'Consulta Odontológica', 20, 11, 0],
                 ['DENT-002', 'PROCEDIMIENTO', 'Curación Simple', 50, 15, 0],
                 ['DENT-003', 'INSUMO', 'Anestesia Dental', 10, 2, 0]],
    }
    for name, rows in sheets.items():
        wb = Workbook()
        for row in rows:
            wb.active.append(row)
        wb.save(target / name)
        wb.close()
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='Directorio nuevo para los catálogos de demostración')
    args = parser.parse_args()
    try:
        print('Catálogos de demostración creados:', generate(args.output))
    except FileExistsError:
        parser.exit(1, 'El directorio ya existe; no se modificó ningún catálogo.\n')
