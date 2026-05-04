import os
from fpdf import FPDF

class TicketPDF(FPDF):
    def header(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_path, '..', 'assets', 'Ocupasalud Logo blanco y negro.png')

        if os.path.exists(logo_path):
            self.image(logo_path, x=14, y=5, w=30)
            self.ln(18)
        
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 5, "CONSULTORIO", 0, 1, 'C')
        self.cell(0, 5, "LAS MARIANAS", 0, 1, 'C')
        
        self.set_font('Helvetica', '', 7)
        direccion = os.getenv('CLINIC_ADDRESS', 'Tu Dirección Aquí')[:45]
        whatsapp = os.getenv('CLINIC_WHATSAPP', '921 689 864')
        self.cell(0, 4, direccion, 0, 1, 'C')
        self.cell(0, 4, f'WhatsApp: {whatsapp}', 0, 1, 'C')
        self.ln(1)
        self.line(3, self.get_y(), 55, self.get_y()) 
        self.ln(2)

    def total_a_letras(self, numero):
        enteros = int(numero)
        centimos = int(round((numero - enteros) * 100))
        return f"SON: {enteros} CON {centimos:02d}/100 SOLES"

def generar_ticket_pdf(data: dict) -> bytes:
    palabras_nombre = data['paciente']['nombre'].split()
    lineas_nombre = (len(palabras_nombre) + 1) // 2 
    
    lineas_descuento = 8 if data.get('descuento_especial_activo') else 0
    alto_ajustado = 110 + (lineas_nombre * 5) + (len(data['items']) * 6) + lineas_descuento
    
    pdf = TicketPDF(orientation='P', unit='mm', format=(58, alto_ajustado))
    pdf.set_margins(3, 4, 3) 
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 4, f"TICKET: {data['id_ticket_global']}", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(0, 4, f"Op: {data['id_ticket_especifico']}", 0, 1, 'L')
    pdf.cell(0, 4, f"Fecha: {data['fecha']}", 0, 1, 'L')
    pdf.ln(1)
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, "Paciente:", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 8)
    
    for i in range(0, len(palabras_nombre), 2):
        par_nombres = " ".join(palabras_nombre[i:i+2])
        pdf.cell(0, 4, par_nombres, 0, 1, 'L')
    
    pdf.ln(2)

    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(26, 5, 'DESC.', 'B', 0, 'L')
    pdf.cell(8, 5, 'CT', 'B', 0, 'C')
    pdf.cell(18, 5, 'TOTAL', 'B', 1, 'R')

    pdf.set_font('Helvetica', '', 7)
    for item in data['items']:
        nombre_item = item['nombre'][:18] 
        pdf.cell(26, 5, nombre_item, 0, 0, 'L')
        pdf.cell(8, 5, str(item['cantidad']), 0, 0, 'C')
        pdf.cell(18, 5, f"{float(item['subtotal']):.2f}", 0, 1, 'R')

    pdf.ln(2)
    
    if data.get('descuento_especial_activo'):
        subtotal = float(data.get('subtotal_servicios', 0))
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(34, 4, "Subtotal:", 0, 0, 'R')
        pdf.cell(18, 4, f"S/. {subtotal:.2f}", 0, 1, 'R')

        tipo = "%" if data['descuento_especial_tipo'] == 'percent' else "S/."
        val = float(data['descuento_especial_valor'])
        monto_desc = float(data['descuento_especial_monto_soles'])
        razon = data.get('descuento_especial_razon', '')[:25]
        
        pdf.set_font('Helvetica', 'I', 7)
        pdf.cell(34, 4, f"Dcto {val:g}{tipo}:", 0, 0, 'R')
        pdf.cell(18, 4, f"- S/. {monto_desc:.2f}", 0, 1, 'R')
        pdf.multi_cell(0, 3, f"({razon})", 0, 'R')
        pdf.ln(1)

    total = float(data['total_final'])
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(34, 6, "TOTAL:", 'T', 0, 'R')
    pdf.cell(18, 6, f"S/. {total:.2f}", 'T', 1, 'R')
    
    pdf.set_font('Helvetica', 'I', 6)
    texto_soles = pdf.total_a_letras(total)
    pdf.multi_cell(0, 3, texto_soles, 0, 'R')
    
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(0, 5, "*** GRACIAS ***", 0, 1, 'C')

    return pdf.output()