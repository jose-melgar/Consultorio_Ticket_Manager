import os
import textwrap  # Importado para manejar el salto de línea limpio por palabras
from escpos.printer import Win32Raw
from PIL import Image

def imprimir_ticket_escpos(data: dict, printer_name: str = "MP-POS80"):
    try:
        # Conexión directa a la impresora en Windows
        p = Win32Raw(printer_name, profile="TM-T88V")
        
        # --- VARIABLES DE CONFIGURACIÓN ---
        ANCHO_CARACTERES = 48
        AREA_IMPRESION_PX = 512
        
        ANCHO_HOJA_REAL_PX = 704  
        ANCHO_LOGO_TARGET = ANCHO_HOJA_REAL_PX // 3
        
        # --- PROCESAMIENTO DEL LOGO ---
        base_path = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_path, '..', 'assets', 'Ocupasalud Logo blanco y negro.png')
        
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            w_percent = (ANCHO_LOGO_TARGET / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            
            img_resized = img.resize((ANCHO_LOGO_TARGET, h_size), Image.Resampling.LANCZOS)
            canvas = Image.new('RGB', (AREA_IMPRESION_PX, h_size), 'white')
            
            offset_x = (AREA_IMPRESION_PX - ANCHO_LOGO_TARGET) // 2
            canvas.paste(img_resized, (offset_x, 0))
            
            p.image(canvas, impl='bitImageColumn')
            p.text("\n")

        # --- ENCABEZADO ---
        p.set(align='center', bold=True, double_height=True, double_width=True)
        p.text("CENTRO MEDICO LABORAL\n")
        p.text("LAS MARIANAS\n")
        
        p.set(align='center', normal_textsize=True, bold=False, double_height=False, double_width=False)
        direccion = os.getenv('CLINIC_ADDRESS', 'Calle Pisac 113 Mz B2 Lt 46')
        whatsapp = os.getenv('CLINIC_WHATSAPP', '921 689 864')
        p.text(f"{direccion}\n")
        p.text(f"WhatsApp: {whatsapp}\n")
        p.text("-" * ANCHO_CARACTERES + "\n") 
        
        # --- DATOS DEL PACIENTE Y TICKET ---
        p.set(align='left', bold=True)
        p.text(f"TICKET: {data['id_ticket_global']}\n")
        p.set(bold=False)
        p.text(f"Op: {data['id_ticket_especifico']}\n")
        p.text(f"Fecha: {data['fecha']}\n\n")
        
        p.set(bold=True)
        p.text("Paciente:\n")
        p.set(bold=False)
        p.text(f"{data['paciente']['nombre']}\n")
        p.text(f"DNI: {data['paciente']['dni']}\n\n")

        # --- TABLA DE SERVICIOS ---
        p.set(bold=True)
        p.text(f"{'DESCRIPCION'.ljust(26)}{'CANT'.center(8)}{'TOTAL'.rjust(14)}\n")
        p.set(bold=False)
        
        for item in data['items']:
            nombre = item['nombre'][:24].ljust(26)
            cant = str(item['cantidad']).center(8)
            subt = f"{float(item['subtotal']):.2f}".rjust(14)
            p.text(f"{nombre}{cant}{subt}\n")

        p.text("-" * ANCHO_CARACTERES + "\n")
        
        # --- SECCIÓN FINANCIERA ---
        p.set(align='right')
        if data.get('descuento_especial_activo'):
            subtotal = float(data.get('subtotal_servicios', 0))
            p.text(f"{'Subtotal: '.rjust(34)}S/. {subtotal:.2f}\n")

            tipo = "%" if data['descuento_especial_tipo'] == 'percent' else "S/."
            val = float(data['descuento_especial_valor'])
            monto_desc = float(data['descuento_especial_monto_soles'])
            razon = data.get('descuento_especial_razon', '')[:30]
            
            p.text(f"Dcto {val:g}{tipo}: - S/. {monto_desc:.2f}\n")
            p.text(f"({razon})\n")

        total = float(data['total_final'])
        p.set(align='right', bold=True, double_height=True, double_width=False)
        p.text(f"TOTAL A PAGAR:  S/. {total:.2f}\n")

        # Se estructuró mejor el método de pago con su respectivo identificador
        p.set(align='right', normal_textsize=True, bold=False, double_height=False)
        p.text(f"Método de Pago: {data['metodo_pago']}\n")
        
        # ==============================================================================
        # 📝 NUEVA SECCIÓN: OBSERVACIONES ADICIONALES EN EL TICKET FÍSICO
        # ==============================================================================
        observaciones = data.get('observaciones', '').strip()
        if observaciones:
            p.text("-" * ANCHO_CARACTERES + "\n")
            p.set(align='left', bold=True)
            p.text("Observaciones:\n")
            p.set(bold=False)
            
            # textwrap.wrap rompe el texto en un array de líneas sin cortar palabras
            lineas_obs = textwrap.wrap(observaciones, width=ANCHO_CARACTERES)
            for linea in lineas_obs:
                p.text(f"{linea}\n")
        
        # Retornamos la alineación para el mensaje de cierre
        p.set(align='center', normal_textsize=True, bold=False, double_height=False)
        p.text("\n*** GRACIAS ***\n")
        
        # Avance de papel y Corte
        p.text("\n\n\n\n\n")
        p.cut()
        p.close()
        
        return True
    except Exception as e:
        print(f"Error de ESC/POS: {e}")
        return False