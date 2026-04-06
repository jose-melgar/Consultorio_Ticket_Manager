from dataclasses import dataclass, field
from typing import List

@dataclass
class ServicioItem:
    """Representa un único item dentro de un ticket de servicio."""
    categoria: str
    nombre_especifico: str
    precio_unitario: float
    cantidad: int = 1
    descuento: float = 0.0

    @property
    def subtotal(self) -> float:
        """Calcula el subtotal para este item."""
        precio_efectivo = self.precio_unitario - self.descuento
        return precio_efectivo * self.cantidad

@dataclass
class Paciente:
    """Representa los datos del paciente."""
    nombre: str
    dni: str

@dataclass
class Ticket:
    """Representa un ticket completo con todos sus servicios y datos."""
    paciente: Paciente
    items: List[ServicioItem] = field(default_factory=list)
    metodo_pago: str = "Efectivo"
    destino: str = "General" # Puede ser "General" o "Dental"

    @property
    def total_bruto(self) -> float:
        """Suma de todos los subtotales sin descuento general."""
        return sum(item.subtotal for item in self.items)

    @property
    def descuento_total(self) -> float:
        """Suma de todos los descuentos aplicados."""
        return sum(item.descuento * item.cantidad for item in self.items)

    @property
    def total_final(self) -> float:
        """Total final a pagar."""
        return self.total_bruto