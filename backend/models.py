from dataclasses import dataclass, field
from typing import List
from decimal import Decimal

@dataclass
class ServicioItem:
    """Representa un único item con precisión decimal."""
    categoria: str
    nombre_especifico: str
    precio_unitario: Decimal
    cantidad: int
    descuento: Decimal = Decimal("0.00")

    @property
    def subtotal(self) -> Decimal:
        """Calcula el subtotal (precio - descuento) * cantidad."""
        return ((self.precio_unitario - self.descuento) * self.cantidad).quantize(Decimal("0.01"))

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
    
    # Variable oculta que no se exige al crear la clase (init=False)
    _total_forzado: Decimal = field(init=False, default=None)

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
        # Si app.py inyectó un total modificado (Descuento Especial), usamos ese
        if self._total_forzado is not None:
            return self._total_forzado
        
        # Si no, hace la suma normal de los items
        return sum(item.subtotal for item in self.items).quantize(Decimal("0.01"))

    @total_final.setter
    def total_final(self, valor):
        """Setter para inyectar un nuevo total (ej: Descuento global desde app.py)"""
        # Nos aseguramos de mantener la precisión de 2 decimales para la moneda
        if isinstance(valor, Decimal):
            self._total_forzado = valor.quantize(Decimal("0.01"))
        else:
            self._total_forzado = Decimal(str(valor)).quantize(Decimal("0.01"))