import os
from fpdf import FPDF

class TicketPDF(FPDF):
    def header(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_path, '..', 'assets', 'Ocupasalud Logo blanco y negro.png')

        # El papel ahora es de 80mm. Para centrar un logo de 36mm: (80 - 36) / 2 = 22
        if os.path.exists(logo_path):
            self.image(logo_path, x=22, y=5, w=36)
            self.ln(22) # Espacio para el logo más grande
        
        # --- NUEVO TÍTULO Y FUENTES MÁS GRANDES ---
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 6, "CENTRO MEDICO LABORAL", 0, 1, 'C')
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 6, "LAS MARIANAS", 0, 1, 'C')
        
        self.set_font('Helvetica', '', 8)
        direccion = os.getenv('CLINIC_ADDRESS', 'Tu Dirección Aquí')[:50]
        whatsapp = os.getenv('CLINIC_WHATSAPP', '921 689 864')
        self.cell(0, 5, direccion, 0, 1, 'C')
        self.cell(0, 5, f'WhatsApp: {whatsapp}', 0, 1, 'C')
        self.ln(2)
        
        # Línea divisoria adaptada al nuevo ancho (de 4mm a 76mm)
        self.line(4, self.get_y(), 76, self.get_y()) 
        self.ln(3)

    def total_a_letras(self, numero):
        enteros = int(numero)
        centimos = int(round((numero - enteros) * 100))
        return f"SON: {enteros} CON {centimos:02d}/100 SOLES"

def generar_ticket_pdf(data: dict) -> bytes:
    palabras_nombre = data['paciente']['nombre'].split()
    lineas_nombre = (len(palabras_nombre) + 1) // 2 
    
    # Base de altura ampliada porque las letras son más grandes
    lineas_descuento = 10 if data.get('descuento_especial_activo') else 0
    alto_ajustado = 130 + (lineas_nombre * 6) + (len(data['items']) * 7) + lineas_descuento
    
    # --- FORMATO DE 80MM ---
    pdf = TicketPDF(orientation='P', unit='mm', format=(80, alto_ajustado))
    
    # 4mm de márgenes a los lados nos da 72mm de ancho perfecto para escribir
    pdf.set_margins(4, 5, 4) 
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 5, f"TICKET: {data['id_ticket_global']}", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 5, f"Op: {data['id_ticket_especifico']}", 0, 1, 'L')
    pdf.cell(0, 5, f"Fecha: {data['fecha']}", 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, "Paciente:", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 10)
    
    for i in range(0, len(palabras_nombre), 2):
        par_nombres = " ".join(palabras_nombre[i:i+2])
        pdf.cell(0, 5, par_nombres, 0, 1, 'L')
    
    pdf.ln(3)

    # --- TABLA ADAPTADA A 72mm (42 + 10 + 20) ---
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(42, 6, 'DESCRIPCION', 'B', 0, 'L')
    pdf.cell(10, 6, 'CANT', 'B', 0, 'C')
    pdf.cell(20, 6, 'TOTAL', 'B', 1, 'R')

    pdf.set_font('Helvetica', '', 9)
    for item in data['items']:
        # Al tener más ancho (42mm), caben hasta 24 caracteres sin cortarse
        nombre_item = item['nombre'][:24] 
        pdf.cell(42, 6, nombre_item, 0, 0, 'L')
        pdf.cell(10, 6, str(item['cantidad']), 0, 0, 'C')
        pdf.cell(20, 6, f"{float(item['subtotal']):.2f}", 0, 1, 'R')

    pdf.ln(3)
    
    # --- SECCIÓN DE DESGLOSE FINANCIERO ---
    if data.get('descuento_especial_activo'):
        subtotal = float(data.get('subtotal_servicios', 0))
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(42, 5, "Subtotal:", 0, 0, 'R')
        pdf.cell(30, 5, f"S/. {subtotal:.2f}", 0, 1, 'R')

        tipo = "%" if data['descuento_especial_tipo'] == 'percent' else "S/."
        val = float(data['descuento_especial_valor'])
        monto_desc = float(data['descuento_especial_monto_soles'])
        razon = data.get('descuento_especial_razon', '')[:30]
        
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(42, 5, f"Dcto {val:g}{tipo}:", 0, 0, 'R')
        pdf.cell(30, 5, f"- S/. {monto_desc:.2f}", 0, 1, 'R')
        pdf.multi_cell(0, 4, f"({razon})", 0, 'R')
        pdf.ln(2)

    total = float(data['total_final'])
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(42, 8, "TOTAL A PAGAR:", 'T', 0, 'R')
    pdf.cell(30, 8, f"S/. {total:.2f}", 'T', 1, 'R')
    
    pdf.set_font('Helvetica', 'I', 8)
    texto_soles = pdf.total_a_letras(total)
    pdf.multi_cell(0, 4, texto_soles, 0, 'R')
    
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, "*** GRACIAS ***", 0, 1, 'C')

    return pdf.output()