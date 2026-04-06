from dataclasses import dataclass, field
from typing import List
from decimal import Decimal

@dataclass
class ServicioItem:
    """Representa un único item con precisión decimal."""
    categoria: str
    nombre_especifico: str
    precio_unitario: Decimal
    cantidad: int = 1
    descuento: Decimal = Decimal("0.00")

    @property
    def subtotal(self) -> Decimal:
        """Calcula el subtotal (precio - descuento) * cantidad."""
        precio_efectivo = self.precio_unitario - self.descuento
        return (precio_efectivo * self.cantidad).quantize(Decimal("0.01"))

@dataclass
class Paciente:
    nombre: str
    dni: str

@dataclass
class Ticket:
    paciente: Paciente
    items: List[ServicioItem] = field(default_factory=list)
    metodo_pago: str = "Efectivo"
    destino: str = "General"

    @property
    def total_bruto(self) -> Decimal:
        """Suma de precios unitarios por cantidad."""
        return sum((item.precio_unitario * item.cantidad) for item in self.items).quantize(Decimal("0.01"))

    @property
    def descuento_total(self) -> Decimal:
        """Suma de todos los descuentos aplicados."""
        return sum((item.descuento * item.cantidad) for item in self.items).quantize(Decimal("0.01"))

    @property
    def total_final(self) -> Decimal:
        """Monto final a pagar después de descuentos."""
        return sum(item.subtotal for item in self.items).quantize(Decimal("0.01"))