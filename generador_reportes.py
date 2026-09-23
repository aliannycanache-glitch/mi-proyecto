import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Maneja el pie de página institucional con la paginación dinámica 'Página X de Y'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#666666"))
        
        # Obtener el ancho dinámico de la página actual (Carta o Carta Apaisado)
        page_width = self._pagesize[0]
        
        # Línea separadora del pie
        self.setStrokeColor(colors.HexColor("#CCCCCC"))
        self.setLineWidth(0.5)
        self.line(36, 36, page_width - 36, 36)
        
        # Texto de pie de página
        self.drawString(36, 22, "Reporte Oficial de Censo Poblacional - Documento Confidencial")
        page_str = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(page_width - 36, 22, page_str)
        self.restoreState()


def _calcular_edad(fecha_nacimiento):
    """Calcula la edad exacta basada en la fecha de nacimiento."""
    if not fecha_nacimiento:
        return "N/A"
    hoy = datetime.date.today()
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return f"{edad} años"


def _obtener_estilos_base():
    """Retorna los estilos estandarizados para todos los reportes."""
    styles = getSampleStyleSheet()
    return {
        'membrete_pais': ParagraphStyle('MembretePais', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=1, textColor=colors.HexColor('#2D3748')),
        'membrete_comunidad': ParagraphStyle('MembreteComunidad', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=1, textColor=colors.HexColor('#1B4332')),
        'titulo': ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=1, textColor=colors.HexColor('#1B4332')),
        'subtitulo': ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, alignment=1, textColor=colors.HexColor('#666666')),
        'seccion': ParagraphStyle('SectionHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=colors.HexColor('#2D3748')),
        'body_bold': ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10.5),
        'body_normal': ParagraphStyle('BodyNormal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=10.5),
        'th': ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white),
        'td': ParagraphStyle('TableBody', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10),
    }


def generar_pdf_familias(familias, ruta_guardado):
    """Genera el PDF del Censo de Familias."""
    doc = SimpleDocTemplate(ruta_guardado, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []
    e = _obtener_estilos_base()

    total_familias = len(familias)
    total_personas = sum(len(f.miembros) + 1 for f in familias)
    fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # 1. Membrete Institucional
    story.append(Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", e['membrete_pais']))
    story.append(Paragraph("CONSEJO COMUNAL SECTOR \"PUEBLO\"", e['membrete_comunidad']))
    story.append(Paragraph("Monagas, Estado Guárico", e['membrete_pais']))
    story.append(Spacer(1, 10))

    # 2. Título del Reporte
    story.append(Paragraph("REPORTE OFICIAL DE CENSO FAMILIAR", e['titulo']))
    story.append(Paragraph(f"Fecha de emisión: {fecha_str}", e['subtitulo']))
    story.append(Spacer(1, 12))

    # 3. Resumen Ejecutivo
    resumen_data = [[
        Paragraph("<b>TOTAL FAMILIAS:</b>", e['body_normal']),
        Paragraph(str(total_familias), e['body_bold']),
        Paragraph("<b>TOTAL PERSONAS EN CENSO:</b>", e['body_normal']),
        Paragraph(str(total_personas), e['body_bold'])
    ]]
    resumen_table = Table(resumen_data, colWidths=[110, 50, 150, 50])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (3, 0), (3, 0), 'CENTER'),
    ]))
    story.append(resumen_table)
    story.append(Spacer(1, 15))

    # 4. Detalle por Familia
    for i, f in enumerate(familias, start=1):
        nombre_jefe = f"{f.nombres_jefe} {f.apellidos_jefe}"
        cedula_jefe = f"{f.tipo_id}-{f.cedula_jefe}"
        telefono_jefe = f.telefono_jefe or "N/A"
        dir_txt = f"{f.calle.nombre if f.calle else 'N/A'} #{f.casa_num or ''}"
        
        # Cálculo dinámico de la edad del jefe
        edad_jefe = _calcular_edad(getattr(f, 'fecha_nacimiento_jefe', None))

        story.append(Paragraph(f"Familia #{i}: {nombre_jefe}", e['seccion']))
        story.append(Spacer(1, 4))

        # Información del Jefe de Familia
        info_jefe = [
            [
                Paragraph("<b>Cédula Jefe:</b>", e['body_normal']), Paragraph(cedula_jefe, e['body_normal']),
                Paragraph("<b>Edad Jefe:</b>", e['body_normal']), Paragraph(edad_jefe, e['body_normal']),
                Paragraph("<b>Teléfono:</b>", e['body_normal']), Paragraph(telefono_jefe, e['body_normal'])
            ],
            [
                Paragraph("<b>Dirección:</b>", e['body_normal']), Paragraph(dir_txt, e['body_normal']),
                Paragraph("<b>Carga Fam.:</b>", e['body_normal']), Paragraph(f"{len(f.miembros)} pers.", e['body_normal']),
                Paragraph("", e['body_normal']), Paragraph("", e['body_normal'])
            ]
        ]
        info_table = Table(info_jefe, colWidths=[70, 95, 65, 80, 60, 134])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 6))

        # Tabla de Integrantes
        if f.miembros:
            tabla_miembros_data = [[
                Paragraph("Nombre y Apellido", e['th']),
                Paragraph("Cédula", e['th']),
                Paragraph("Parentesco", e['th']),
                Paragraph("Edad", e['th'])
            ]]
            for m in f.miembros:
                cedula_m = f"{m.tipo_id}-{m.cedula}" if m.cedula and m.cedula != "No posee" else "No posee"
                edad_m = _calcular_edad(m.fecha_nacimiento)
                tabla_miembros_data.append([
                    Paragraph(f"{m.nombres} {m.apellidos}", e['td']),
                    Paragraph(cedula_m, e['td']),
                    Paragraph(m.parentesco or "—", e['td']),
                    Paragraph(edad_m, e['td'])
                ])

            miembros_table = Table(tabla_miembros_data, colWidths=[190, 110, 110, 94])
            miembros_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2D3748')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(miembros_table)
        else:
            story.append(Paragraph("<i>Sin carga familiar registrada.</i>", e['body_normal']))

        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=12))

    doc.build(story, canvasmaker=NumberedCanvas)


def generar_pdf_gas(registros_gas, ruta_guardado):
    """Genera el PDF del Censo de Gas Doméstico desglosado por tipos de cilindro."""
    # Usamos orientación apaisada (Landscape) para comodidad en tablas anchas
    doc = SimpleDocTemplate(ruta_guardado, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []
    e = _obtener_estilos_base()

    total_familias = len(registros_gas)
    total_kg10 = sum(r.kg10 or 0 for r in registros_gas)
    total_kg18 = sum(r.kg18 or 0 for r in registros_gas)
    total_kg27 = sum(r.kg27 or 0 for r in registros_gas)
    total_kg43 = sum(r.kg43 or 0 for r in registros_gas)
    total_general = total_kg10 + total_kg18 + total_kg27 + total_kg43

    fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # 1. Membrete
    story.append(Paragraph("REPÚBLICA BOLIVARIANA DE VENEZUELA", e['membrete_pais']))
    story.append(Paragraph("CONSEJO COMUNAL SECTOR \"PUEBLO\"", e['membrete_comunidad']))
    story.append(Paragraph("Monagas, Estado Guárico", e['membrete_pais']))
    story.append(Spacer(1, 8))

    # 2. Título
    story.append(Paragraph("REPORTE OFICIAL CENSO DE GAS DOMÉSTICO", e['titulo']))
    story.append(Paragraph(f"Fecha de emisión: {fecha_str}", e['subtitulo']))
    story.append(Spacer(1, 10))

    # 3. Resumen Ejecutivo
    resumen_data = [
        [
            Paragraph("<b>FAMILIAS ATENDIDAS:</b>", e['body_normal']), Paragraph(str(total_familias), e['body_bold']),
            Paragraph("<b>TOTAL 10KG:</b>", e['body_normal']), Paragraph(str(total_kg10), e['body_bold']),
            Paragraph("<b>TOTAL 18KG:</b>", e['body_normal']), Paragraph(str(total_kg18), e['body_bold']),
            Paragraph("<b>TOTAL 27KG:</b>", e['body_normal']), Paragraph(str(total_kg27), e['body_bold']),
            Paragraph("<b>TOTAL 43KG:</b>", e['body_normal']), Paragraph(str(total_kg43), e['body_bold']),
            Paragraph("<b>TOTAL CILINDROS:</b>", e['body_normal']), Paragraph(str(total_general), e['body_bold'])
        ]
    ]
    resumen_table = Table(resumen_data, colWidths=[95, 35, 65, 35, 65, 35, 65, 35, 65, 35, 90, 40])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(resumen_table)
    story.append(Spacer(1, 12))

    # 4. Tabla de Gas Desglosada
    tabla_gas_data = [[
        Paragraph("#", e['th']),
        Paragraph("Jefe de Familia", e['th']),
        Paragraph("Cédula", e['th']),
        Paragraph("Dirección", e['th']),
        Paragraph("10kg", e['th']),
        Paragraph("18kg", e['th']),
        Paragraph("27kg", e['th']),
        Paragraph("43kg", e['th']),
        Paragraph("Total", e['th'])
    ]]

    for i, r in enumerate(registros_gas, start=1):
        if r.familia:
            jefe = f"{r.familia.nombres_jefe} {r.familia.apellidos_jefe}"
            cedula = f"{r.familia.tipo_id}-{r.familia.cedula_jefe}"
            calle_nom = r.familia.calle.nombre if r.familia.calle else "Sin Calle"
            casa_num = f", Casa {r.familia.casa_num}" if r.familia.casa_num else ""
            direccion = f"{calle_nom}{casa_num}"
        else:
            jefe = "Desconocido"
            cedula = "N/A"
            direccion = "N/A"

        k10, k18, k27, k43 = r.kg10 or 0, r.kg18 or 0, r.kg27 or 0, r.kg43 or 0
        subtotal = k10 + k18 + k27 + k43

        tabla_gas_data.append([
            Paragraph(str(i), e['td']),
            Paragraph(jefe, e['td']),
            Paragraph(cedula, e['td']),
            Paragraph(direccion, e['td']),
            Paragraph(str(k10), e['td']),
            Paragraph(str(k18), e['td']),
            Paragraph(str(k27), e['td']),
            Paragraph(str(k43), e['td']),
            Paragraph(f"<b>{subtotal}</b>", e['td'])
        ])

    # Fila de Totales Generales
    tabla_gas_data.append([
        Paragraph("<b>TOTALES</b>", e['td']),
        Paragraph("", e['td']), Paragraph("", e['td']), Paragraph("", e['td']),
        Paragraph(f"<b>{total_kg10}</b>", e['td']),
        Paragraph(f"<b>{total_kg18}</b>", e['td']),
        Paragraph(f"<b>{total_kg27}</b>", e['td']),
        Paragraph(f"<b>{total_kg43}</b>", e['td']),
        Paragraph(f"<b>{total_general}</b>", e['td'])
    ])

    gas_table = Table(tabla_gas_data, colWidths=[25, 180, 80, 225, 45, 45, 45, 45, 50])
    gas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2D3748')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F7FAFC')]),
        ('SPAN', (0, -1), (3, -1)),  # Unir celdas para la fila de totales
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(gas_table)

    doc.build(story, canvasmaker=NumberedCanvas)


def generar_pdf_adultos_mayores(registros, ruta_guardado):
    """Genera el padrón de atención y beneficios del adulto mayor."""
    doc = SimpleDocTemplate(ruta_guardado, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=48)
    estilos = _obtener_estilos_base()
    story = [
        Paragraph("REPORTE DE ATENCIÓN DEL ADULTO MAYOR", estilos['titulo']),
        Paragraph(f"Fecha de emisión: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos['subtitulo']),
        Spacer(1, 12),
    ]
    datos = [[
        Paragraph("Cédula", estilos['th']), Paragraph("Nombre", estilos['th']),
        Paragraph("Edad", estilos['th']), Paragraph("Categoría", estilos['th']),
        Paragraph("Beneficio", estilos['th']), Paragraph("Dirección", estilos['th']),
    ]]
    for registro in registros:
        datos.append([
            Paragraph(f"{registro.tipo_id}-{registro.cedula}", estilos['td']),
            Paragraph(f"{registro.nombres} {registro.apellidos}", estilos['td']),
            Paragraph(str(registro.edad or "-"), estilos['td']),
            Paragraph(registro.categoria or "No aplica", estilos['td']),
            Paragraph("Sí" if registro.aplica_bolsa == "Si" else "No", estilos['td']),
            Paragraph(registro.direccion or "-", estilos['td']),
        ])
    tabla = Table(datos, colWidths=[75, 170, 45, 140, 70, 270], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2D3748')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(tabla)
    doc.build(story, canvasmaker=NumberedCanvas)


def generar_pdf_proteccion_integral(casos, ruta_guardado):
    """Genera el reporte de casos registrados en protección integral."""
    doc = SimpleDocTemplate(ruta_guardado, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=48)
    estilos = _obtener_estilos_base()
    story = [
        Paragraph("REPORTE DE GESTIÓN DE PROTECCIÓN INTEGRAL", estilos['titulo']),
        Paragraph(f"Fecha de emisión: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos['subtitulo']),
        Spacer(1, 12),
    ]
    datos = [[
        Paragraph("Cédula", estilos['th']), Paragraph("Nombre", estilos['th']),
        Paragraph("Tipo de caso", estilos['th']), Paragraph("Estado", estilos['th']),
        Paragraph("Fecha", estilos['th']), Paragraph("Descripción", estilos['th']),
    ]]
    for caso in casos:
        datos.append([
            Paragraph(f"{caso.tipo_id}-{caso.cedula}", estilos['td']),
            Paragraph(f"{caso.nombres} {caso.apellidos}", estilos['td']),
            Paragraph(caso.tipo_caso or "-", estilos['td']),
            Paragraph(caso.estado or "-", estilos['td']),
            Paragraph(caso.fecha_registro.strftime('%d/%m/%Y') if caso.fecha_registro else "-", estilos['td']),
            Paragraph(caso.descripcion or "-", estilos['td']),
        ])
    tabla = Table(datos, colWidths=[75, 160, 130, 85, 75, 270], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2D3748')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(tabla)
    doc.build(story, canvasmaker=NumberedCanvas)