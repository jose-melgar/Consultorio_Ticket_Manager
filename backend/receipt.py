"""Canonical receipt content shared by PDF and the thermal printer."""
from decimal import Decimal
import os
import textwrap

def clinic():
    return {'nombre': os.getenv('CLINIC_NAME', 'CENTRO MEDICO LABORAL LAS MARIANAS'),
            'direccion': os.getenv('CLINIC_ADDRESS', 'Calle Pisac 113 Mz B2 Lt 46'),
            'whatsapp': os.getenv('CLINIC_WHATSAPP', '921 689 864')}

def clean(value):
    return ''.join(c if ord(c) >= 32 or c in '\n\t' else ' ' for c in str(value))

def receipt_lines(data, width=48):
    details = clinic()
    lines = [details['nombre'], details['direccion'], 'WhatsApp: ' + details['whatsapp'], '-' * width,
             'TICKET: ' + data['id_ticket_global'], 'Op: ' + data['id_ticket_especifico'], 'Fecha: ' + data['fecha'],
             'Paciente: ' + data['paciente']['nombre'], 'DNI: ' + data['paciente']['dni'], '-' * width,
             'DETALLE DE SERVICIOS']
    if data.get('habilitado') is False:
        lines.insert(0, '*** TICKET ANULADO ***')
    for item in data.get('items', []):
        lines.extend([item['nombre'], f"Cant: {item['cantidad']}   Total: S/. {Decimal(str(item['subtotal'])):.2f}"])
    lines.append('-' * width)
    if data.get('descuento_especial_activo'):
        lines.extend([f"Subtotal: S/. {Decimal(str(data['subtotal_servicios'])):.2f}",
                      f"Descuento: S/. {Decimal(str(data['descuento_especial_monto_soles'])):.2f}",
                      'Motivo: ' + data.get('descuento_especial_razon', '')])
    lines.extend([f"TOTAL A PAGAR: S/. {Decimal(str(data['total_final'])):.2f}",
                  'Método de Pago: ' + data.get('metodo_pago', 'Sin cobro')])
    if 'pago_con' in data:
        lines.append(f"Recibido: S/. {Decimal(str(data['pago_con'])):.2f}")
    if 'vuelto' in data:
        lines.append(f"Vuelto: S/. {Decimal(str(data['vuelto'])):.2f}")
    if data.get('observaciones'):
        lines.extend(['Observaciones:', data['observaciones']])
    if data.get('motivo_eliminacion'):
        lines.extend(['Motivo de anulación:', data['motivo_eliminacion']])
    lines.append('*** GRACIAS ***')
    return [wrapped for line in lines for paragraph in clean(line).splitlines()
            for wrapped in (textwrap.wrap(paragraph, width=width) or [''])]
