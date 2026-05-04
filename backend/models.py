from dataclasses import dataclass, field
from typing import List
from decimal import Decimal

@dataclass
class Paciente:
    nombre: str
    dni: str

@dataclass
class ServicioItem:
    categoria: str
    nombre_especifico: str
    precio_unitario: Decimal
    costo_unitario: Decimal # Novedad: Ahora guardamos el costo para calcular ganancias
    cantidad: int
    descuento: Decimal = Decimal("0.00")

    @property
    def subtotal(self) -> Decimal:
        return ((self.precio_unitario - self.descuento) * self.cantidad).quantize(Decimal("0.01"))

@dataclass
class Ticket:
    paciente: Paciente
    items: List[ServicioItem] = field(default_factory=list)
    metodo_pago: str = "Efectivo"
    destino: str = "General"
    
    _total_forzado: Decimal = field(init=False, default=None)

    @property
    def total_bruto(self) -> Decimal:
        return sum((item.precio_unitario * item.cantidad) for item in self.items).quantize(Decimal("0.01"))

    @property
    def descuento_total(self) -> Decimal:
        return sum((item.descuento * item.cantidad) for item in self.items).quantize(Decimal("0.01"))

    @property
    def total_final(self) -> Decimal:
        if self._total_forzado is not None:
            return self._total_forzado
        return sum(item.subtotal for item in self.items).quantize(Decimal("0.01"))

    @total_final.setter
    def total_final(self, valor):
        if isinstance(valor, Decimal):
            self._total_forzado = valor.quantize(Decimal("0.01"))
        else:
            self._total_forzado = Decimal(str(valor)).quantize(Decimal("0.01"))