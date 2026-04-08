import os
from fpdf import FPDF

class TicketPDF(FPDF):
    def header(self):
        # Obtenemos los datos de las variables de entorno
        nombre_clinic = os.getenv('CLINIC_NAME', 'NOMBRE DEL CONSULTORIO')
        direccion = os.getenv('CLINIC_ADDRESS', 'Dirección no configurada')
        whatsapp = os.getenv('CLINIC_WHATSAPP', '000 000 000')

        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 6, nombre_clinic, 0, 1, 'C')
        self.set_font('Helvetica', '', 7)
        self.cell(0, 4, direccion, 0, 1, 'C')
        self.cell(0, 4, f'WhatsApp: {whatsapp}', 0, 1, 'C')
        self.ln(2)
        self.cell(0, 0, '', 'T', 1, 'C') # Línea divisoria
        self.ln(2)

    def total_a_letras(self, numero):
        enteros = int(numero)
        centimos = int(round((numero - enteros) * 100))
        return f"SON: {enteros} CON {centimos:02d}/100 SOLES"

def generar_ticket_pdf(data: dict) -> bytes:
    pdf = TicketPDF(orientation='P', unit='mm', format=(80, 140))
    pdf.set_margins(6, 6, 6)
    pdf.add_page()
    
    # Encabezado de ID y Atencion
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, f"TICKET: {data['id_ticket_global']}", 0, 1)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, f"Operación {data['destino']}: {data['id_ticket_especifico']}", 0, 1)
    pdf.cell(0, 4, f"Fecha: {data['fecha']}", 0, 1)
    pdf.cell(0, 4, f"Cajero: {data.get('atendido_por', 'Admin')}", 0, 1)
    pdf.ln(1)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, f"PACIENTE: {data['paciente']['nombre']}", 0, 1)
    pdf.ln(2)

    # Tabla de Servicios
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(38, 5, 'DESCRIPCION', 'B', 0, 'L')
    pdf.cell(10, 5, 'CANT', 'B', 0, 'C')
    pdf.cell(20, 5, 'TOTAL', 'B', 1, 'R')

    pdf.set_font('Helvetica', '', 7)
    for item in data['items']:
        nombre = item['nombre'][:24]
        pdf.cell(38, 5, nombre, 0, 0, 'L')
        pdf.cell(10, 5, str(item['cantidad']), 0, 0, 'C')
        pdf.cell(20, 5, f"S/. {float(item['subtotal']):.2f}", 0, 1, 'R')

    # Totales y Letras
    pdf.ln(2)
    total = float(data['total_final'])
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 7, f"TOTAL A PAGAR: S/. {total:.2f}", 'T', 1, 'R')
    
    pdf.set_font('Helvetica', 'I', 6)
    pdf.multi_cell(0, 4, pdf.total_a_letras(total), 0, 'R')
    
    pdf.ln(2)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(0, 4, f"Metodo de Pago: {data['metodo_pago']}", 0, 1, 'L')
    
    # Disclaimer Legal
    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 7)
    pdf.multi_cell(0, 4, "Este documento es una nota de venta interna y no tiene validez como factura o boleta electrónica.", 0, 'C')
    
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, "*** Gracias por su confianza ***", 0, 1, 'C')

    return pdf.output()