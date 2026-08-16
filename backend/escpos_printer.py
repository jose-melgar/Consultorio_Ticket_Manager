import os
import textwrap
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

        # --- DETALLE DE SERVICIOS (ANCHO COMPLETO SIN CORTES) ---
        p.text("-" * ANCHO_CARACTERES + "\n")
        p.set(bold=True)
        p.text("DETALLE DE SERVICIOS\n")
        p.text("-" * ANCHO_CARACTERES + "\n")
        p.set(bold=False)
        
        for item in data.get('items', []):
            nombre_completo = item.get('nombre', '')
            cant = int(item.get('cantidad', 1))
            
            # Calcular subtotal
            if 'subtotal' in item:
                subt = float(item['subtotal'])
            else:
                subt = float(item.get('precio_unitario', 0)) * cant
            
            # 1. Imprime el nombre completo ocupando todo el ancho (48 caracteres)
            lineas_nombre = textwrap.wrap(nombre_completo, width=ANCHO_CARACTERES)
            p.set(align='left', bold=True)
            for linea in lineas_nombre:
                p.text(f"{linea}\n")
            
            # 2. Imprime la cantidad y el subtotal en la línea inferior
            p.set(bold=False)
            txt_cant = f"  Cant: {cant}"
            txt_subt = f"Total: S/. {subt:.2f}"
            espacios = ANCHO_CARACTERES - len(txt_cant) - len(txt_subt)
            if espacios < 1:
                espacios = 1
            p.text(f"{txt_cant}{' ' * espacios}{txt_subt}\n\n")

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

        p.set(align='right', normal_textsize=True, bold=False, double_height=False)
        p.text(f"Método de Pago: {data.get('metodo_pago', 'Efectivo')}\n")
        
        # --- OBSERVACIONES ADICIONALES ---
        observaciones = data.get('observaciones', '').strip()
        if observaciones:
            p.text("-" * ANCHO_CARACTERES + "\n")
            p.set(align='left', bold=True)
            p.text("Observaciones:\n")
            p.set(bold=False)
            
            lineas_obs = textwrap.wrap(observaciones, width=ANCHO_CARACTERES)
            for linea in lineas_obs:
                p.text(f"{linea}\n")
        
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