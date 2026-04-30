import os
from fpdf import FPDF

class TicketPDF(FPDF):
    def header(self):
        # Separación del nombre de la clínica en 2 líneas
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 5, "CONSULTORIO", 0, 1, 'C')
        self.cell(0, 5, "LAS MARIANAS", 0, 1, 'C')
        
        self.set_font('Helvetica', '', 7)
        # Al tener más espacio, permitimos direcciones más largas
        direccion = os.getenv('CLINIC_ADDRESS', 'Dirección no configurada')[:45]
        whatsapp = os.getenv('CLINIC_WHATSAPP', '000 000 000')
        self.cell(0, 4, direccion, 0, 1, 'C')
        self.cell(0, 4, f'WhatsApp: {whatsapp}', 0, 1, 'C')
        self.ln(1)
        
        # Línea divisoria extendida de borde a borde (de 3 a 55)
        self.line(3, self.get_y(), 55, self.get_y()) 
        self.ln(2)

    def total_a_letras(self, numero):
        enteros = int(numero)
        centimos = int(round((numero - enteros) * 100))
        return f"SON: {enteros} CON {centimos:02d}/100 SOLES"

def generar_ticket_pdf(data: dict) -> bytes:
    # --- CÁLCULO DE ALTO DINÁMICO ---
    palabras_nombre = data['paciente']['nombre'].split()
    lineas_nombre = (len(palabras_nombre) + 1) // 2 
    
    alto_ajustado = 90 + (lineas_nombre * 5) + (len(data['items']) * 6)
    
    # --- FORMATO FULL ANCHO (58MM) ---
    pdf = TicketPDF(orientation='P', unit='mm', format=(58, alto_ajustado))
    
    # Márgenes de 3mm izquierda y derecha (nos da 52mm de espacio útil para escribir)
    pdf.set_margins(3, 4, 3) 
    pdf.add_page()
    
    # Info de venta
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 4, f"TICKET: {data['id_ticket_global']}", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(0, 4, f"Op: {data['id_ticket_especifico']}", 0, 1, 'L')
    pdf.cell(0, 4, f"Fecha: {data['fecha']}", 0, 1, 'L')
    pdf.ln(1)
    
    # --- SECCIÓN PACIENTE (Se mantiene tu lógica de 2 nombres por línea) ---
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, "Paciente:", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 8)
    
    for i in range(0, len(palabras_nombre), 2):
        par_nombres = " ".join(palabras_nombre[i:i+2])
        pdf.cell(0, 4, par_nombres, 0, 1, 'L')
    
    pdf.ln(2)

    # --- NUEVA TABLA ANCHA (26mm + 8mm + 18mm = 52mm totales) ---
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(26, 5, 'DESC.', 'B', 0, 'L')
    pdf.cell(8, 5, 'CT', 'B', 0, 'C')
    pdf.cell(18, 5, 'TOTAL', 'B', 1, 'R')

    pdf.set_font('Helvetica', '', 7)
    for item in data['items']:
        # Ahora caben hasta 18 caracteres en la descripción sin cortarse
        nombre_item = item['nombre'][:18] 
        pdf.cell(26, 5, nombre_item, 0, 0, 'L')
        pdf.cell(8, 5, str(item['cantidad']), 0, 0, 'C')
        pdf.cell(18, 5, f"{float(item['subtotal']):.2f}", 0, 1, 'R')

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