"""PDF rendering for a quote (fpdf2, pure Python, no system dependencies)."""

from fpdf import FPDF

from .models import Quote


def _money(value: float) -> str:
    return f"${value:,.2f}"


def build_quote_pdf(quote: Quote) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Header
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, f"Construction Quote #{quote.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, f"Client: {quote.client_name or '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Project: {quote.title}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Status: {quote.status}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Items table
    col = (90, 25, 35, 40)  # description, qty, unit price, line total
    pdf.set_font("helvetica", "B", 11)
    for width, label in zip(col, ("Description", "Qty", "Unit price", "Line total")):
        pdf.cell(width, 8, label, border=1)
    pdf.ln()
    pdf.set_font("helvetica", "", 11)
    for item in quote.items:
        pdf.cell(col[0], 8, item.description[:48], border=1)
        pdf.cell(col[1], 8, f"{item.quantity:g}", border=1)
        pdf.cell(col[2], 8, _money(item.unit_price), border=1)
        pdf.cell(col[3], 8, _money(item.line_total), border=1)
        pdf.ln()

    # Totals
    pdf.ln(4)
    pdf.set_font("helvetica", "", 11)
    pdf.cell(150, 7, "Subtotal:", align="R")
    pdf.cell(40, 7, _money(quote.subtotal), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(150, 7, f"Tax ({quote.tax_rate * 100:g}%):", align="R")
    pdf.cell(40, 7, _money(quote.tax_amount), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(150, 8, "Total:", align="R")
    pdf.cell(40, 8, _money(quote.total), new_x="LMARGIN", new_y="NEXT")

    if quote.notes:
        pdf.ln(4)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 5, f"Notes: {quote.notes}")

    return bytes(pdf.output())
