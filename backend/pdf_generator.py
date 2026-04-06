from fpdf import FPDF
from datetime import datetime

class TicketPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'CONSULTORIO LAS MARIANAS', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'Dirección: Av. Ejemplo 123, Lima, Perú', 0, 1, 'C')
        self.cell(0, 5, 'Tel: 987-654-321', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 9)
        self.cell(0, 6, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, data):
        self.set_font('Arial', '', 8)
        for key, value in data.items():
            self.multi_cell(0, 5, f'{key}: {value}')
        self.ln()

    def items_table(self, items):
        self.set_font('Arial', 'B', 7)
        # Anchos de columna para 80mm de papel (aprox 72mm usables)
        col_widths = {'desc': 32, 'cant': 8, 'pu': 12, 'desc_u': 10, 'subt': 10}
        self.cell(col_widths['desc'], 5, 'Descripción', 1)
        self.cell(col_widths['cant'], 5, 'Cant', 1)
        self.cell(col_widths['pu'], 5, 'P.U.', 1)
        self.cell(col_widths['desc_u'], 5, 'Desc.', 1)
        self.cell(col_widths['subt'], 5, 'Subt', 1, 1)

        self.set_font('Arial', '', 7)
        for item in items:
            self.cell(col_widths['desc'], 5, item['nombre'], 1)
            self.cell(col_widths['cant'], 5, str(item['cantidad']), 1, 0, 'C')
            self.cell(col_widths['pu'], 5, f"{item['precioUnitario']:.2f}", 1, 0, 'R')
            self.cell(col_widths['desc_u'], 5, f"{item['descuento']:.2f}", 1, 0, 'R')
            self.cell(col_widths['subt'], 5, f"{item['subtotal']:.2f}", 1, 1, 'R')
        self.ln(5)
    
    def totals(self, total_final):
        self.set_font('Arial', 'B', 9)
        self.cell(0, 6, f'TOTAL A PAGAR: S/. {total_final:.2f}', 0, 1, 'R')

def generar_ticket_pdf(venta_data: dict) -> bytes:
    """Crea el PDF y lo devuelve como un stream de bytes."""
    # Ancho de 80mm para ticketera
    pdf = TicketPDF(orientation='P', unit='mm', format=(80, 200)) # Largo dinámico
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Borde de validación (como se pidió)
    pdf.rect(5, 5, 70, pdf.get_y() + 100) # Ajustar el alto según el contenido

    # --- Contenido del Ticket ---
    pdf.chapter_title('Datos del Paciente')
    pdf.chapter_body({
        "Nombre": venta_data['paciente']['nombre'],
        "DNI": venta_data['paciente']['dni'],
        "Fecha": venta_data['fecha']
    })
    
    pdf.chapter_title('Detalle de Servicios')
    pdf.items_table(venta_data['items'])
    
    pdf.totals(venta_data['total_final'])
    
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 8)
    pdf.cell(0, 5, '¡Gracias por su preferencia!', 0, 1, 'C')

    # Devolver el PDF en memoria
    return pdf.output(dest='S').encode('latin1')
