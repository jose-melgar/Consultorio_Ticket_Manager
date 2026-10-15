"""Receipts with full descriptions, observations and measured thermal page height."""
import os
from pathlib import Path
from fpdf import FPDF
from PIL import Image
from receipt import receipt_lines

LOGO = Path(__file__).resolve().parent.parent / 'assets' / 'Ocupasalud Logo blanco y negro.png'

def generar_ticket_pdf(data):
    font = Path(os.getenv('PDF_FONT', str(Path(os.getenv('WINDIR', 'C:/Windows')) / 'Fonts' / 'arial.ttf')))
    lines = receipt_lines(data)
    def render(height):
        pdf = FPDF(unit='mm', format=(80, height))
        pdf.set_margins(4, 4, 4)
        pdf.set_auto_page_break(False)
        pdf.add_page()
        if font.is_file():
            pdf.add_font('Receipt', fname=str(font))
            pdf.set_font('Receipt', size=9)
        else:
            pdf.set_font('Helvetica', size=9)
        if LOGO.exists():
            pdf.image(str(LOGO), x=24, y=4, w=32)
            with Image.open(LOGO) as image:
                pdf.set_y(4 + 32 * image.height / image.width + 3)
        for line in lines:
            if not font.is_file():
                line = line.encode('latin-1', errors='replace').decode('latin-1')
            pdf.set_x(4)
            pdf.multi_cell(72, 4.5, line)
        return pdf
    measured = render(10000)
    height = max(80, measured.get_y() + 6)
    # Serialization closes the measurement pass's font resources as well.
    measured.output()
    final = render(height)
    return bytes(final.output())
