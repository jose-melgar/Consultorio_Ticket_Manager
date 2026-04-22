import os
from fpdf import FPDF

class TicketPDF(FPDF):
    def header(self):
        # Separación del nombre de la clínica en 2 líneas
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 5, "CONSULTORIO", 0, 1, 'C')
        self.cell(0, 5, "LAS MARIANAS", 0, 1, 'C')
        
        self.set_font('Helvetica', '', 7)
        direccion = os.getenv('CLINIC_ADDRESS', 'Dirección no configurada')[:35]
        whatsapp = os.getenv('CLINIC_WHATSAPP', '000 000 000')
        self.cell(0, 4, direccion, 0, 1, 'C')
        self.cell(0, 4, f'WhatsApp: {whatsapp}', 0, 1, 'C')
        self.ln(1)
        self.line(5, self.get_y(), 43, self.get_y()) 
        self.ln(2)

    def total_a_letras(self, numero):
        enteros = int(numero)
        centimos = int(round((numero - enteros) * 100))
        return f"SON: {enteros} CON {centimos:02d}/100 SOLES"

def generar_ticket_pdf(data: dict) -> bytes:
    # --- CÁLCULO DE ALTO DINÁMICO ---
    # Dividimos el nombre del paciente en palabras para calcular cuántas líneas ocupará
    palabras_nombre = data['paciente']['nombre'].split()
    lineas_nombre = (len(palabras_nombre) + 1) // 2 # 2 nombres por línea
    
    # Base 85mm + lineas de nombre + 6mm por servicio
    alto_ajustado = 90 + (lineas_nombre * 5) + (len(data['items']) * 6)
    
    # Formato 48mm de área de impresión real
    pdf = TicketPDF(orientation='P', unit='mm', format=(48, alto_ajustado))
    pdf.set_margins(6, 4, 6) 
    pdf.add_page()
    
    # Info de venta
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 4, f"TICKET: {data['id_ticket_global']}", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(0, 4, f"Op: {data['id_ticket_especifico']}", 0, 1, 'L')
    pdf.cell(0, 4, f"Fecha: {data['fecha']}", 0, 1, 'L')
    pdf.ln(1)
    
    # --- SECCIÓN PACIENTE (Saltos de línea cada 2 palabras) ---
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, "Paciente:", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 8)
    
    for i in range(0, len(palabras_nombre), 2):
        par_nombres = " ".join(palabras_nombre[i:i+2])
        pdf.cell(0, 4, par_nombres, 0, 1, 'L')
    
    pdf.ln(2)

    # Tabla de servicios
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(18, 5, 'DESC.', 'B', 0, 'L')
    pdf.cell(4, 5, 'CT', 'B', 0, 'C')
    pdf.cell(14, 5, 'TOTAL', 'B', 1, 'R')

    pdf.set_font('Helvetica', '', 7)
    for item in data['items']:
        nombre_item = item['nombre'][:12] 
        pdf.cell(18, 5, nombre_item, 0, 0, 'L')
        pdf.cell(4, 5, str(item['cantidad']), 0, 0, 'C')
        pdf.cell(14, 5, f"{float(item['subtotal']):.2f}", 0, 1, 'R')

    # Totales
    pdf.ln(2)
    total = float(data['total_final'])
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 6, f"TOTAL: S/. {total:.2f}", 'T', 1, 'R')
    
    pdf.set_font('Helvetica', 'I', 6)
    texto_soles = pdf.total_a_letras(total)
    pdf.multi_cell(0, 3, texto_soles, 0, 'R')
    
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, "*** GRACIAS ***", 0, 1, 'C')

    return pdf.output()