from io import BytesIO
from datetime import datetime, date
from decimal import Decimal
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED


def _normalize_formato(formato):
    normalized = (formato or "PDF").strip().upper()
    aliases = {
        "PDF": "PDF",
        "EXCEL": "EXCEL",
        "XLS": "EXCEL",
        "XLSX": "EXCEL",
        "HTML": "HTML",
    }
    return aliases.get(normalized, normalized)


def export_pdf(report):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        raise

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 12)
    y = height - 50
    c.drawString(50, y, report.get("titulo", "Reporte"))
    y -= 20
    cols = report.get("columnas", [])
    # header
    c.setFont("Helvetica-Bold", 10)
    x = 50
    for col in cols:
        c.drawString(x, y, str(col))
        x += 150
    y -= 15
    c.setFont("Helvetica", 9)
    for row in report.get("datos", []):
        x = 50
        for col in cols:
            c.drawString(x, y, str(row.get(col, row.get(col.replace("__", "__"), ""))))
            x += 150
        y -= 12
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer.read(), "application/pdf", f"reporte_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"


def export_excel(report):
    def _sanitize_sheet_title(title):
        invalid = ['\\', '/', '*', '?', ':', '[', ']']
        safe = str(title or "Reporte")
        for ch in invalid:
            safe = safe.replace(ch, "_")
        return safe[:31] or "Reporte"

    def _col_letter(n):
        result = ""
        while n:
            n, rem = divmod(n - 1, 26)
            result = chr(65 + rem) + result
        return result

    def _cell_xml(ref, value):
        if value is None:
            value = ""
        if isinstance(value, bool):
            return f'<c r="{ref}" t="b"><v>{"1" if value else "0"}</v></c>'
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
            return f'<c r="{ref}"><v>{value}</v></c>'
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        text = escape(str(value))
        return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'

    def _build_sheet_xml(report_data):
        cols = report_data.get("columnas", [])
        rows = report_data.get("datos", [])
        xml_rows = []

        header_cells = []
        for idx, col in enumerate(cols, start=1):
            ref = f"{_col_letter(idx)}1"
            header_cells.append(_cell_xml(ref, col))
        xml_rows.append(f'<row r="1">{"".join(header_cells)}</row>')

        for row_idx, row in enumerate(rows, start=2):
            cells = []
            for col_idx, col in enumerate(cols, start=1):
                ref = f"{_col_letter(col_idx)}{row_idx}"
                cells.append(_cell_xml(ref, row.get(col, "")))
            xml_rows.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
           xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetData>
    {''.join(xml_rows)}
  </sheetData>
</worksheet>
"""

    titulo = _sanitize_sheet_title(report.get("titulo", "Reporte"))
    sheet_xml = _build_sheet_xml(report)
    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{escape(titulo)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""
    core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/"
                   xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escape(str(report.get("titulo", "Reporte")))}</dc:title>
  <dc:creator>HomePet</dc:creator>
  <cp:lastModifiedBy>HomePet</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{datetime.utcnow().isoformat()}Z</dcterms:created>
</cp:coreProperties>
"""
    app_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>HomePet</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>1</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="1" baseType="lpstr">
      <vt:lpstr>{escape(titulo)}</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
</Properties>
"""

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("docProps/app.xml", app_xml)

    buffer.seek(0)
    return (
        buffer.read(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"reporte_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx",
    )


def export_html(report):
    cols = report.get("columnas", [])
    rows = report.get("datos", [])
    html = ["<html><head><meta charset='utf-8'><title>", report.get("titulo", "Reporte"), "</title></head><body>"]
    html.append(f"<h1>{report.get('titulo','Reporte')}</h1>")
    html.append("<table border='1' cellpadding='5' cellspacing='0'>")
    # header
    html.append("<tr>")
    for c in cols:
        html.append(f"<th>{c}</th>")
    html.append("</tr>")
    for r in rows:
        html.append("<tr>")
        for c in cols:
            html.append(f"<td>{r.get(c,'')}</td>")
        html.append("</tr>")
    html.append("</table></body></html>")
    content = "".join(html).encode("utf-8")
    return content, "text/html", f"reporte_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"


def export_report(report, formato):
    formato = _normalize_formato(formato)
    if formato == "PDF":
        return export_pdf(report)
    if formato == "EXCEL":
        return export_excel(report)
    if formato == "HTML":
        return export_html(report)
    raise ValueError("Formato no soportado")
