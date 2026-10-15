"""Windows spool submission; a successful submission is not proof of paper output."""
import logging
import os
from pathlib import Path
from PIL import Image
from receipt import receipt_lines

logger = logging.getLogger(__name__)

def imprimir_ticket_escpos(data, printer_name=None):
    printer = None
    try:
        from escpos.printer import Win32Raw
        printer = Win32Raw(printer_name or os.getenv('PRINTER_NAME', 'MP-POS80'),
                           profile=os.getenv('PRINTER_PROFILE', 'TM-T88V'))
        logo = Path(__file__).resolve().parent.parent / 'assets' / 'Ocupasalud Logo blanco y negro.png'
        if logo.exists():
            with Image.open(logo) as source:
                size = (234, max(1, round(source.height * 234 / source.width)))
                resized = source.convert('RGB').resize(size, Image.Resampling.LANCZOS)
                with Image.new('RGB', (512, size[1]), 'white') as canvas:
                    canvas.paste(resized, ((512 - size[0]) // 2, 0))
                    printer.image(canvas, impl='bitImageColumn')
                resized.close()
        printer.set(align='left', bold=False, normal_textsize=True)
        for line in receipt_lines(data):
            printer.text(line + '\n')
        printer.text('\n\n\n\n')
        printer.cut()
        return True
    except Exception as exc:
        logger.error('Print submission failed (%s)', type(exc).__name__)
        return False
    finally:
        if printer is not None:
            try:
                printer.close()
            except Exception as exc:
                logger.error('Printer cleanup failed (%s)', type(exc).__name__)
