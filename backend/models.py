"""Validación y reglas monetarias independientes del transporte y del hardware."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from zoneinfo import ZoneInfo

CENT = Decimal('0.01')
ZERO = Decimal('0.00')
PAYMENTS = {'Efectivo', 'Yape', 'Plin', 'Tarjeta', 'Transferencia'}

class ValidationError(ValueError):
    pass

def now():
    return datetime.now(ZoneInfo('America/Lima'))

def money(value, label='Importe'):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValidationError(f'{label}: importe inválido.')
    raw = str(value).strip()
    if not re.fullmatch(r'\d+(?:[.,]\d{1,2})?', raw):
        raise ValidationError(f'{label}: use un importe positivo con hasta dos decimales.')
    try:
        result = Decimal(raw.replace(',', '.'))
        if not result.is_finite() or result > Decimal('999999999.99'):
            raise InvalidOperation
        return result.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValidationError(f'{label}: importe fuera de rango.') from None

def text(value, label, limit=200, required=True, multiline=False):
    if not isinstance(value, str):
        raise ValidationError(f'{label}: texto inválido.')
    value = value.strip()
    if (required and not value) or len(value) > limit:
        raise ValidationError(f'{label}: longitud inválida (máximo {limit}).')
    if any(ord(c) < 32 and not (multiline and c in '\n\r\t') for c in value):
        raise ValidationError(f'{label}: contiene caracteres de control.')
    return value

def quantity(value, maximum=999):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValidationError(f'Cantidad: debe ser un entero entre 1 y {maximum}.')
    return value

@dataclass
class Paciente:
    nombre: str
    dni: str
    def __post_init__(self):
        self.nombre = text(self.nombre, 'Nombre').upper()
        if not isinstance(self.dni, str) or not re.fullmatch(r'[0-9]{8}', self.dni):
            raise ValidationError('DNI: debe contener exactamente ocho dígitos.')

@dataclass
class ServicioItem:
    categoria: str
    nombre_especifico: str
    precio_unitario: Decimal
    costo_unitario: Decimal
    cantidad: int
    descuento: Decimal = ZERO
    costo_lab: Decimal = ZERO
    costo_insumo: Decimal = ZERO
    servicio_id: str = 'OTROS'
    def __post_init__(self):
        quantity(self.cantidad)
        self.nombre_especifico = text(self.nombre_especifico, 'Servicio')
        for name in ('precio_unitario', 'costo_unitario', 'descuento', 'costo_lab', 'costo_insumo'):
            setattr(self, name, money(getattr(self, name), name))
        if self.descuento > self.precio_unitario:
            raise ValidationError('El descuento de catálogo supera el precio del servicio.')
    @property
    def subtotal(self):
        return ((self.precio_unitario - self.descuento) * self.cantidad).quantize(CENT)

@dataclass
class Ticket:
    paciente: Paciente
    items: list[ServicioItem] = field(default_factory=list)
    metodo_pago: str = 'Efectivo'
    destino: str = 'General'
    _total_forzado: Decimal | None = field(init=False, default=None)
    @property
    def total_bruto(self):
        return sum((i.precio_unitario * i.cantidad for i in self.items), ZERO)
    @property
    def descuento_total(self):
        return sum((i.descuento * i.cantidad for i in self.items), ZERO)
    @property
    def total_final(self):
        return self._total_forzado if self._total_forzado is not None else sum((i.subtotal for i in self.items), ZERO)
    @total_final.setter
    def total_final(self, value):
        self._total_forzado = money(value)

def build_sale(data, catalogs):
    if not isinstance(data, dict) or not isinstance(data.get('paciente'), dict):
        raise ValidationError('Se requieren los datos del paciente.')
    patient = Paciente(data['paciente'].get('nombre'), data['paciente'].get('dni'))
    destination = data.get('destino')
    if destination not in ('general', 'dental'):
        raise ValidationError('Destino inválido.')
    id_column = 'ID_General' if destination == 'general' else 'ID_Dental'
    by_id = {row[id_column]: row for row in catalogs[destination]}
    raw_items = data.get('items')
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 100:
        raise ValidationError('La venta debe contener entre 1 y 100 servicios.')
    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValidationError('Servicio inválido.')
        count = quantity(raw.get('cantidad'))
        service_id = text(raw.get('id'), 'ID de servicio', 80)
        if service_id == 'OTROS':
            item = ServicioItem('OTROS', raw.get('nombre'), money(raw.get('precio_unitario'), 'Precio'), ZERO, count)
        else:
            row = by_id.get(service_id)
            if row is None:
                raise ValidationError('Un servicio ya no pertenece al catálogo. Actualice la página.')
            lab = money(row.get('Costo Laboratorio', 0)) if destination == 'general' else ZERO
            supply = money(row.get('Costo Insumos', 0)) if destination == 'general' else ZERO
            cost = lab + supply if destination == 'general' else money(row.get('Costo', 0))
            item = ServicioItem(row['Categoría'], row['Nombre Específico'], money(row['Precio Unitario']), cost,
                                count, money(row.get('Descuento', 0)), lab, supply, service_id)
        items.append(item)
    subtotal = sum((i.subtotal for i in items), ZERO)
    active = data.get('descuento_especial_activo', False)
    if not isinstance(active, bool):
        raise ValidationError('Indicador de descuento inválido.')
    kind, value, reason, discount = 'percent', ZERO, '', ZERO
    if active:
        kind = data.get('descuento_especial_tipo')
        value = money(data.get('descuento_especial_valor'), 'Descuento')
        reason = text(data.get('descuento_especial_razon'), 'Motivo del descuento', 300)
        if kind not in ('percent', 'fixed') or (kind == 'percent' and value > 100):
            raise ValidationError('Tipo o porcentaje de descuento inválido.')
        discount = (subtotal * value / 100).quantize(CENT, rounding=ROUND_HALF_UP) if kind == 'percent' else value
        if discount > subtotal:
            raise ValidationError('El descuento supera el subtotal.')
    total = subtotal - discount
    payments = data.get('desglose_pagos', [])
    if not isinstance(payments, list) or len(payments) > len(PAYMENTS):
        raise ValidationError('Desglose de pagos inválido.')
    parsed, methods = [], set()
    for payment in payments:
        if not isinstance(payment, dict) or payment.get('metodo') not in PAYMENTS:
            raise ValidationError('Método de pago inválido.')
        method = payment['metodo']
        amount = money(payment.get('monto'), 'Pago')
        if method in methods or amount <= 0:
            raise ValidationError('Los pagos deben ser positivos y no repetir métodos.')
        methods.add(method)
        parsed.append({'metodo': method, 'monto': str(amount)})
    received = sum((Decimal(p['monto']) for p in parsed), ZERO)
    if received < total:
        raise ValidationError('Los pagos no cubren el total calculado por el servidor.')
    change = received - total
    cash = sum((Decimal(p['monto']) for p in parsed if p['metodo'] == 'Efectivo'), ZERO)
    if change > cash:
        raise ValidationError('El vuelto no puede superar el efectivo recibido.')
    if 'total_esperado' in data and money(data['total_esperado']) != total:
        raise ValidationError('Los precios cambiaron. Actualice el catálogo y revise el total.')
    method_label = ', '.join(f"{p['metodo']}({p['monto']})" for p in parsed) or 'Sin cobro'
    if change:
        method_label += f', Vuelto(-{change})'
    timestamp = now()
    return {
        'fecha': timestamp.strftime('%H:%M:%S %d/%m/%Y'), 'fecha_iso': timestamp.isoformat(),
        'paciente': {'nombre': patient.nombre, 'dni': patient.dni}, 'destino': destination.capitalize(),
        'items': [{'id': i.servicio_id, 'nombre': i.nombre_especifico, 'categoria': i.categoria,
                   'cantidad': i.cantidad, 'precio_unitario': str(i.precio_unitario), 'descuento': str(i.descuento),
                   'subtotal': str(i.subtotal), 'costo_unitario': str(i.costo_unitario),
                   'costo_lab': str(i.costo_lab), 'costo_insumo': str(i.costo_insumo)} for i in items],
        'subtotal_servicios': str(subtotal), 'total_final': str(total),
        'descuento_especial_activo': active, 'descuento_especial_tipo': kind,
        'descuento_especial_valor': str(value), 'descuento_especial_monto_soles': str(discount),
        'descuento_especial_razon': reason, 'observaciones': text(data.get('observaciones', ''), 'Observaciones', 2000, False, True),
        'metodo_pago': method_label, 'desglose_pagos': parsed, 'pago_con': str(received), 'vuelto': str(change),
        'habilitado': True, 'atendido_por': 'Operador local',
    }
