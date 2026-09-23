import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from datetime import datetime
import os
from sqlalchemy.orm import joinedload
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO
from utiles import abrir_datepicker_solo_fecha
from modelo import SessionLocal, Usuario, Familia, Miembro

# Importaciones para generación ultra rápida de PDF con ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

def obtener_nombre_mes(mes_str):
    """Convierte un mes numérico (ej. '10' o '1') a su nombre en texto ('octubre')."""
    try:
        idx = int(mes_str) - 1
        if 0 <= idx < 12:
            return MESES[idx]
    except Exception:
        pass
    return mes_str

def formatear_cedula(cedula_str):
    """Asegura el formato estándar con prefijo 'V-'."""
    cedula_str = str(cedula_str).strip()
    if not cedula_str or cedula_str in ["________________", "No posee", "___"]:
        return cedula_str
    if not (cedula_str.startswith("V-") or cedula_str.startswith("E-") or cedula_str.startswith("J-") or cedula_str.startswith("G-")):
        return f"V-{cedula_str}"
    return cedula_str

def generar_pdf_residencia_rapido(nombre, cedula, direccion, tiempo, fecha, encargado_nombre, encargado_cedula, encargado_rol, encargado_telefono, ruta_salida):
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=35
    )
    styles = getSampleStyleSheet()
    
    # Estilos institucionales
    estilo_encabezado = ParagraphStyle(
        'Encabezado',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0f172a")
    )

    estilo_titulo = ParagraphStyle(
        'TituloDoc',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=14,
        leading=18,
        spaceAfter=15,
        textColor=colors.HexColor("#0f172a")
    )
    
    estilo_cuerpo = ParagraphStyle(
        'Cuerpo',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=11,
        leading=18,
        spaceAfter=12
    )

    estilo_firma = ParagraphStyle(
        'Firma',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        leading=14
    )

    estilo_nota = ParagraphStyle(
        'NotaValidez',
        parent=styles['Normal'],
        alignment=TA_JUSTIFY,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    # Procesar fecha (Nombre del mes)
    try:
        partes = fecha.split("/")
        dia = partes[0]
        mes_num = partes[1]
        ano = partes[2]
        mes_nombre = obtener_nombre_mes(mes_num)
    except Exception:
        dia, mes_nombre, ano = "___", "___", "____"

    # Formatear Cédulas
    cedula_formateada = formatear_cedula(cedula)
    encargado_cedula_formateada = formatear_cedula(encargado_cedula)

    story = []

    # 1. Membrete Institucional (Municipio -> Estado)
    header_text = """
    <b>REPÚBLICA BOLIVARIANA DE VENEZUELA</b><br/>
    MUNICIPIO JOSÉ TADEO MONAGAS — ESTADO GUÁRICO<br/>
    PARROQUIA ALTAGRACIA DE ORITUCO<br/>
    <font color="#1e3a8a"><b>CONSEJO COMUNAL "PUEBLO NUEVO"</b></font>
    """
    story.append(Paragraph(header_text, estilo_encabezado))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=15))

    # 2. Título del Documento
    story.append(Paragraph("<u><b>CARTA DE RESIDENCIA</b></u>", estilo_titulo))
    story.append(Spacer(1, 10))

    # 3. Texto Principal (Enfocado Exclusivamente en Residencia)
    texto_p1 = f"""
    Quien suscribe, ciudadano(a) <b>{encargado_nombre}</b>, titular de la cédula de identidad N° <b>{encargado_cedula_formateada}</b>, 
    en su condición de <b>{encargado_rol}</b> del Consejo Comunal del Sector <b>"PUEBLO NUEVO"</b>, ubicado en la parroquia 
    Altagracia de Orituco, Municipio José Tadeo Monagas del Estado Guárico, por medio de la presente hace constar que 
    el/la ciudadano(a): <b>{nombre}</b>, titular de la Cédula de Identidad N° <b>{cedula_formateada}</b>, posee su residencia fijada 
    y habitada permanentemente en la siguiente dirección: <b>{direccion}</b>, dentro del ámbito territorial de nuestra comunidad.
    """
    story.append(Paragraph(texto_p1, estilo_cuerpo))

    texto_p2 = f"""
    Se hace constar que el/la referido(a) ciudadano(a) reside en la dirección antes señalada desde hace 
    aproximadamente <b>{tiempo} años</b>.
    """
    story.append(Paragraph(texto_p2, estilo_cuerpo))

    texto_p3 = f"""
    Constancia que se expide a petición de la parte interesada para los fines legales que considere convenientes, en la ciudad 
    de Altagracia de Orituco, a los <b>{dia}</b> días del mes de <b>{mes_nombre}</b> del año <b>{ano}</b>.
    """
    story.append(Paragraph(texto_p3, estilo_cuerpo))
    story.append(Spacer(1, 40))

    # 4. Firma Única con Teléfono de Contacto
    filas_firma = [
        [Paragraph("__________________________________________", estilo_firma)],
        [Paragraph(f"<b>{encargado_nombre}</b>", estilo_firma)],
        [Paragraph(f"C.I.: {encargado_cedula_formateada}", estilo_firma)],
        [Paragraph(f"<b>{encargado_rol}</b>", estilo_firma)]
    ]
    
    if encargado_telefono and str(encargado_telefono).strip() not in ["", "________________", "Sin teléfono"]:
        filas_firma.append([Paragraph(f"Teléfono de Contacto: {str(encargado_telefono).strip()}", estilo_firma)])
        
    filas_firma.append([Paragraph("Consejo Comunal Pueblo Nuevo", estilo_firma)])

    tabla_firma = Table(filas_firma, colWidths=[350])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))

    story.append(tabla_firma)
    story.append(Spacer(1, 25))

    # 5. Nota de Validez Legal
    texto_nota = """
    <b>NOTA DE VALIDEZ:</b> Este documento posee validez única y exclusivamente si presenta la firma original del vocero autorizado y el sello húmedo correspondiente del Consejo Comunal del Sector Pueblo Nuevo, Altagracia de Orituco, Estado Guárico.
    """
    
    tabla_nota = Table([
        [Paragraph(texto_nota, estilo_nota)]
    ], colWidths=[500])
    tabla_nota.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(tabla_nota)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<font color='#94a3b8'>Documento emitido mediante el Sistema ComuniDatos</font>", estilo_firma))

    doc.build(story)


def vista_residencia(pagina: ft.Page):
    campo_busqueda = ft.Ref[ft.TextField]()
    lista_resultados = ft.Ref[ft.Column]()
    campo_nombre = ft.Ref[ft.Text]()
    campo_cedula = ft.Ref[ft.Text]()
    campo_direccion = ft.Ref[ft.Text]()
    campo_fecha = ft.Ref[ft.TextField]()
    campo_tiempo = ft.Ref[ft.Dropdown]()

    # Cargar datos desde BD
    session = SessionLocal()
    familias = session.query(Familia).options(joinedload(Familia.calle)).all()
    todos = []
    
    for f in familias:
        calle_nom = f.calle.nombre if f.calle else "Sin calle"
        casa_num = f", Casa #{f.casa_num}" if f.casa_num else ""
        direccion_txt = f"{calle_nom}{casa_num}"

        todos.append({
            "nombre": f"{f.nombres_jefe} {f.apellidos_jefe}",
            "cedula": f"{f.tipo_id}-{f.cedula_jefe}",
            "direccion": direccion_txt
        })
        
        for m in f.miembros:
            cedula_m = f"{m.tipo_id}-{m.cedula}" if m.cedula and m.cedula != "No posee" else "No posee"
            todos.append({
                "nombre": f"{m.nombres} {m.apellidos}",
                "cedula": cedula_m,
                "direccion": direccion_txt
            })
    session.close()

    def seleccionar(miembro):
        campo_nombre.current.value = f'Nombre: {miembro["nombre"]}'
        campo_cedula.current.value = f'Cédula: {miembro["cedula"]}'
        campo_direccion.current.value = f'Dirección: {miembro["direccion"]}'
        campo_nombre.current.update()
        campo_cedula.current.update()
        campo_direccion.current.update()
        lista_resultados.current.controls = []
        lista_resultados.current.update()

    def buscar(e):
        texto = campo_busqueda.current.value.lower().strip()
        if not texto:
            lista_resultados.current.controls = []
            lista_resultados.current.update()
            return

        coincidencias = [m for m in todos if texto in m["nombre"].lower() or texto in m["cedula"].lower()]
        lista_resultados.current.controls = []
        for m in coincidencias[:10]:
            boton = ft.TextButton(text=f'{m["nombre"]} — {m["cedula"]}', on_click=lambda ev, mm=m: seleccionar(mm))
            lista_resultados.current.controls.append(boton)
        lista_resultados.current.update()

    def abrir_fecha(e):
        abrir_datepicker_solo_fecha(e, campo_fecha.current, formato="%d/%m/%Y")

    def exportar_pdf(e: ft.FilePickerUploadEvent):
        if not e.path:
            return

        destino = e.path
        if not destino.lower().endswith(".pdf"):
            destino += ".pdf"

        nombre = campo_nombre.current.value.replace("Nombre: ", "").strip()
        cedula = campo_cedula.current.value.replace("Cédula: ", "").strip()
        direccion = campo_direccion.current.value.replace("Dirección: ", "").strip()
        fecha = campo_fecha.current.value.strip()
        tiempo = campo_tiempo.current.value.replace(" años", "") if campo_tiempo.current.value else "___"

        # Cargar datos del Líder / Encargado desde la sesión activa
        encargado_nombre = "________________"
        encargado_cedula = "________________"
        encargado_rol = "Líder Político"
        encargado_telefono = ""

        if hasattr(pagina, "session_usuario_id"):
            session = SessionLocal()
            usuario = session.query(Usuario).filter(Usuario.id == pagina.session_usuario_id).first()
            session.close()
            if usuario:
                encargado_nombre = f"{usuario.nombre} {usuario.apellido}"
                encargado_cedula = usuario.cedula
                encargado_rol = usuario.rol if usuario.rol else "Líder Político"
                encargado_telefono = getattr(usuario, "telefono", "") or getattr(usuario, "tlf", "") or ""

        # Generar PDF
        generar_pdf_residencia_rapido(
            nombre, cedula, direccion, tiempo, fecha,
            encargado_nombre, encargado_cedula, encargado_rol, encargado_telefono, destino
        )

        dlg = ft.AlertDialog(
            title=ft.Text("Carta Generada"),
            content=ft.Text(f"La carta de residencia fue guardada en:\n{destino}"),
            actions=[ft.TextButton("Cerrar", on_click=lambda ev: e.page.close_dialog())]
        )
        e.page.dialog = dlg
        dlg.open = True
        e.page.update()

    file_picker = ft.FilePicker(on_result=exportar_pdf)
    pagina.overlay.append(file_picker)

    def generar_carta(e):
        cedula = campo_cedula.current.value.replace("Cédula: ", "").strip() or "documento"
        file_picker.save_file(dialog_title="Guardar carta de residencia...", file_name=f"Carta_Residencia_{cedula}.pdf")

    def mostrar_vista_previa(e):
        nombre = campo_nombre.current.value.replace("Nombre: ", "").strip()
        cedula = campo_cedula.current.value.replace("Cédula: ", "").strip()
        direccion = campo_direccion.current.value.replace("Dirección: ", "").strip()
        fecha = campo_fecha.current.value.strip()
        tiempo = campo_tiempo.current.value or "Sin especificar"

        if not nombre or not cedula or not direccion:
            pagina.snack_bar = ft.SnackBar(
                ft.Text("Selecciona primero un miembro para ver la carta.")
            )
            pagina.snack_bar.open = True
            pagina.update()
            return

        with SessionLocal() as session:
            usuario = session.query(Usuario).filter(
                Usuario.id == getattr(pagina, "session_usuario_id", None)
            ).first()

        encargado_nombre = f"{usuario.nombre} {usuario.apellido}" if usuario else "________________"
        encargado_cedula = usuario.cedula if usuario else "________________"
        encargado_rol = usuario.rol if usuario and usuario.rol else "Líder Político"

        documento = ft.Container(
            content=ft.Column(
                [
                    ft.Text("REPÚBLICA BOLIVARIANA DE VENEZUELA", size=11, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text("MUNICIPIO JOSÉ TADEO MONAGAS - ESTADO GUÁRICO", size=10, text_align=ft.TextAlign.CENTER),
                    ft.Text('CONSEJO COMUNAL "PUEBLO NUEVO"', size=11, weight=ft.FontWeight.BOLD, color=COLOR_VERDE, text_align=ft.TextAlign.CENTER),
                    ft.Divider(color=COLOR_NEGRO),
                    ft.Text("CARTA DE RESIDENCIA", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=8),
                    ft.Text(
                        f'Quien suscribe, {encargado_nombre}, titular de la cédula N° {encargado_cedula}, '
                        f'en su condición de {encargado_rol}, hace constar que {nombre}, titular de la cédula '
                        f'N° {cedula}, reside permanentemente en {direccion}.',
                        size=12,
                        text_align=ft.TextAlign.JUSTIFY,
                    ),
                    ft.Text(
                        f"Se hace constar que reside en la dirección indicada desde hace aproximadamente {tiempo}.",
                        size=12,
                        text_align=ft.TextAlign.JUSTIFY,
                    ),
                    ft.Text(
                        f"Constancia que se expide en Altagracia de Orituco, a los {fecha}.",
                        size=12,
                        text_align=ft.TextAlign.JUSTIFY,
                    ),
                    ft.Container(height=18),
                    ft.Text("________________________________", text_align=ft.TextAlign.CENTER),
                    ft.Text(encargado_nombre, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"C.I.: {encargado_cedula}", text_align=ft.TextAlign.CENTER),
                    ft.Text(encargado_rol, text_align=ft.TextAlign.CENTER),
                    ft.Text("Vista previa - documento aún no generado", size=10, color=COLOR_GRIS, italic=True, text_align=ft.TextAlign.CENTER),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            border=ft.border.all(1, COLOR_GRIS),
            border_radius=8,
            padding=28,
            width=680,
        )

        def cerrar_vista_previa(ev):
            pagina.close(dialogo)

        def generar_desde_vista_previa(ev):
            pagina.close(dialogo)
            generar_carta(ev)

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Vista previa de la carta de residencia"),
            content=documento,
            actions=[
                ft.TextButton("Cerrar", on_click=cerrar_vista_previa),
                ft.ElevatedButton("Generar PDF", icon=ft.Icons.PICTURE_AS_PDF, bgcolor=COLOR_VERDE, color=COLOR_BLANCO, on_click=generar_desde_vista_previa),
            ],
        )
        pagina.open(dialogo)

    # UI principal
    titulo = ft.Text("Carta de Residencia", size=26, weight="bold", color=COLOR_NEGRO)

    campo_busqueda.current = ft.TextField(
        hint_text="Buscar miembro por nombre, apellido o cédula",
        prefix_icon=ft.Icons.SEARCH,
        bgcolor=COLOR_BLANCO,
        border_radius=8,
        width=500,
        on_change=buscar
    )

    lista_resultados.current = ft.Column([], scroll=ft.ScrollMode.AUTO)

    campo_nombre.current = ft.Text("Nombre: ", size=16)
    campo_cedula.current = ft.Text("Cédula: ", size=16)
    campo_direccion.current = ft.Text("Dirección: ", size=16)

    campo_fecha.current = ft.TextField(
        label="Fecha de Emisión",
        hint_text="dd/mm/aaaa",
        bgcolor=COLOR_BLANCO,
        border_radius=8,
        width=180,
        read_only=True,
        value=datetime.now().strftime("%d/%m/%Y")
    )

    boton_fecha = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Seleccionar fecha",
        icon_color=COLOR_VERDE,
        on_click=abrir_fecha
    )

    campo_tiempo.current = ft.Dropdown(
        label="Tiempo de vivienda",
        width=180,
        value="1 años",
        options=[ft.dropdown.Option(f"{a} años") for a in range(1, 31)]
    )

    boton_generar = ft.ElevatedButton(
        text="Generar Carta en PDF",
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.DESCRIPTION,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=generar_carta
    )

    return ft.Container(
        content=ft.Column([
            titulo,
            ft.Text("Paso 1: Buscar Miembro", size=18, weight="bold"),
            campo_busqueda.current,
            ft.Container(content=lista_resultados.current, height=140, bgcolor="#ffffff66", padding=10, border_radius=8, border=ft.border.all(1, COLOR_GRIS)),
            ft.Divider(),
            ft.Text("Paso 2: Confirmar Datos y Generar", size=18, weight="bold"),
            campo_nombre.current,
            campo_cedula.current,
            campo_direccion.current,
            ft.Row([campo_fecha.current, boton_fecha, campo_tiempo.current], spacing=20),
            ft.Row([
                ft.OutlinedButton("Vista previa", icon=ft.Icons.PREVIEW, on_click=mostrar_vista_previa),
                boton_generar,
            ], alignment=ft.MainAxisAlignment.END, spacing=12)
        ], spacing=20),
        padding=20,
        bgcolor=COLOR_BLANCO,
        border_radius=10,
        expand=True
    )