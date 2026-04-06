from fpdf import FPDF

class TicketPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 6, 'CONSULTORIO LAS MARIANAS', 0, 1, 'C')
        self.set_font('Helvetica', '', 7)
        self.cell(0, 4, 'RUC: 12345678901', 0, 1, 'C') # Dato opcional pero común
        self.ln(2)

def generar_ticket_pdf(data: dict) -> bytes:
    # Ancho 80mm, altura dinámica (ajustada a 120mm iniciales)
    pdf = TicketPDF(orientation='P', unit='mm', format=(80, 120))
    pdf.set_margins(5, 5, 5)
    pdf.add_page()
    
    # Encabezado de ID y Datos
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, f"TICKET: {data['id_ticket_global']}", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, f"ID Int: {data['id_ticket_especifico']}", 0, 1, 'L')
    pdf.cell(0, 4, f"Fecha: {data['fecha']}", 0, 1, 'L')
    pdf.cell(0, 4, f"Paciente: {data['paciente']['nombre']}", 0, 1, 'L')
    pdf.ln(2)

    # Tabla compacta
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(40, 5, 'Servicio', 'B', 0, 'L')
    pdf.cell(10, 5, 'Cant', 'B', 0, 'C')
    pdf.cell(20, 5, 'Total', 'B', 1, 'R')

    pdf.set_font('Helvetica', '', 7)
    for item in data['items']:
        # Control de texto largo para que no rompa la tabla
        nombre = item['nombre'][:25]
        pdf.cell(40, 5, nombre, 0, 0, 'L')
        pdf.cell(10, 5, str(item['cantidad']), 0, 0, 'C')
        pdf.cell(20, 5, f"S/. {float(item['subtotal']):.2f}", 0, 1, 'R')

    pdf.ln(2)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 7, f"TOTAL A PAGAR: S/. {float(data['total_final']):.2f}", 'T', 1, 'R')
    
    pdf.set_font('Helvetica', 'I', 7)
    pdf.cell(0, 5, f"Metodo de Pago: {data['metodo_pago']}", 0, 1, 'R')
    pdf.ln(4)
    pdf.cell(0, 4, '*** Gracias por su confianza ***', 0, 1, 'C')

    return pdf.output()