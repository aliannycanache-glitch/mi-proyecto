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

# --- Constantes de Colores Pastel ---
PASTEL_BG = "#F4F6F8"
PASTEL_CARD = "#FFFFFF"
PASTEL_VERDE = COLOR_VERDE if 'COLOR_VERDE' in globals() else "#4CAF50"
PASTEL_TEXTO_PRI = "#2C3E50"
PASTEL_TEXTO_SEC = "#6C757D"
PASTEL_BORDE = "#E0E0E0"
PASTEL_CAMPO_BG = "#F9FAFB"

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

def obtener_nombre_mes(mes_str):
    try:
        idx = int(mes_str) - 1
        if 0 <= idx < 12:
            return MESES[idx]
    except Exception:
        pass
    return mes_str

def formatear_cedula(cedula_str):
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
    
    estilo_encabezado = ParagraphStyle('Encabezado', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, leading=13, textColor=colors.HexColor("#0f172a"))
    estilo_titulo = ParagraphStyle('TituloDoc', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, leading=18, spaceAfter=15, textColor=colors.HexColor("#0f172a"))
    estilo_cuerpo = ParagraphStyle('Cuerpo', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=11, leading=18, spaceAfter=12)
    estilo_firma = ParagraphStyle('Firma', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, leading=14)
    estilo_nota = ParagraphStyle('NotaValidez', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=8, leading=11, textColor=colors.HexColor("#334155"))

    try:
        partes = fecha.split("/")
        dia, mes_num, ano = partes[0], partes[1], partes[2]
        mes_nombre = obtener_nombre_mes(mes_num)
    except Exception:
        dia, mes_nombre, ano = "___", "___", "____"

    cedula_formateada = formatear_cedula(cedula)
    encargado_cedula_formateada = formatear_cedula(encargado_cedula)

    story = []

    header_text = """
    <b>REPÚBLICA BOLIVARIANA DE VENEZUELA</b><br/>
    MUNICIPIO JOSÉ TADEO MONAGAS — ESTADO GUÁRICO<br/>
    PARROQUIA ALTAGRACIA DE ORITUCO<br/>
    <font color="#1e3a8a"><b>CONSEJO COMUNAL "PUEBLO NUEVO"</b></font>
    """
    story.append(Paragraph(header_text, estilo_encabezado))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=15))

    story.append(Paragraph("<u><b>CARTA DE RESIDENCIA</b></u>", estilo_titulo))
    story.append(Spacer(1, 10))

    texto_p1 = f"""
    Quien suscribe, ciudadano(a) <b>{encargado_nombre}</b>, titular de la cédula de identidad N° <b>{encargado_cedula_formateada}</b>, 
    en su condición de <b>{encargado_rol}</b> del Consejo Comunal del Sector <b>"PUEBLO NUEVO"</b>, ubicado en la parroquia 
    Altagracia de Orituco, Municipio José Tadeo Monagas del Estado Guárico, por medio de la presente hace constar que 
    el/la ciudadano(a): <b>{nombre}</b>, titular de la Cédula de Identidad N° <b>{cedula_formateada}</b>, posee su residencia fijada 
    y habitada permanentemente en la siguiente dirección: <b>{direccion}</b>, dentro del ámbito territorial de nuestra comunidad.
    """
    story.append(Paragraph(texto_p1, estilo_cuerpo))

    texto_p2 = f"Se hace constar que el/la referido(a) ciudadano(a) reside en la dirección antes señalada desde hace aproximadamente <b>{tiempo} años</b>."
    story.append(Paragraph(texto_p2, estilo_cuerpo))

    texto_p3 = f"Constancia que se expide a petición de la parte interesada para los fines legales que considere convenientes, en la ciudad de Altagracia de Orituco, a los <b>{dia}</b> días del mes de <b>{mes_nombre}</b> del año <b>{ano}</b>."
    story.append(Paragraph(texto_p3, estilo_cuerpo))
    story.append(Spacer(1, 40))

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
    tabla_firma.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

    story.append(tabla_firma)
    story.append(Spacer(1, 25))

    texto_nota = "<b>NOTA DE VALIDEZ:</b> Este documento posee validez única y exclusivamente si presenta la firma original del vocero autorizado y el sello húmedo correspondiente del Consejo Comunal del Sector Pueblo Nuevo, Altagracia de Orituco, Estado Guárico."
    
    tabla_nota = Table([[Paragraph(texto_nota, estilo_nota)]], colWidths=[500])
    tabla_nota.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(tabla_nota)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<font color='#94a3b8'>Documento emitido mediante el Sistema ComuniDatos</font>", estilo_firma))

    doc.build(story)

# --- VISTA PRINCIPAL ---
def vista_residencia(page: ft.Page = None):
    try:
        campo_busqueda = ft.Ref[ft.TextField]()
        lista_resultados = ft.Ref[ft.Column]()
        contenedor_busqueda = ft.Ref[ft.Container]()
        
        txt_nombre = ft.Ref[ft.Text]()
        txt_cedula = ft.Ref[ft.Text]()
        txt_direccion = ft.Ref[ft.Text]()
        
        campo_fecha = ft.Ref[ft.TextField]()
        campo_tiempo = ft.Ref[ft.Dropdown]()

        # Cargar datos BD
        todos = []
        try:
            session = SessionLocal()
            familias = session.query(Familia).options(joinedload(Familia.calle)).all()
            for f in familias:
                calle_nom = f.calle.nombre if getattr(f, "calle", None) else "Sin calle"
                casa_num = f", Casa #{f.casa_num}" if getattr(f, "casa_num", None) else ""
                direccion_txt = f"{calle_nom}{casa_num}"

                todos.append({
                    "nombre": f"{f.nombres_jefe} {f.apellidos_jefe}",
                    "cedula": f"{f.tipo_id}-{f.cedula_jefe}",
                    "direccion": direccion_txt
                })
                
                for m in getattr(f, "miembros", []):
                    cedula_m = f"{m.tipo_id}-{m.cedula}" if getattr(m, "cedula", None) and m.cedula != "No posee" else "No posee"
                    todos.append({
                        "nombre": f"{m.nombres} {m.apellidos}",
                        "cedula": cedula_m,
                        "direccion": direccion_txt
                    })
            session.close()
        except Exception as err:
            print(f"Error cargando base de datos en vista_residencia: {err}")

        def seleccionar(miembro):
            txt_nombre.current.value = miembro["nombre"]
            txt_cedula.current.value = miembro["cedula"]
            txt_direccion.current.value = miembro["direccion"]
            
            txt_nombre.current.color = PASTEL_TEXTO_PRI
            txt_cedula.current.color = PASTEL_TEXTO_PRI
            txt_direccion.current.color = PASTEL_TEXTO_PRI
            
            txt_nombre.current.update()
            txt_cedula.current.update()
            txt_direccion.current.update()
            
            lista_resultados.current.controls = []
            contenedor_busqueda.current.visible = False
            contenedor_busqueda.current.update()

        def buscar(e):
            texto = campo_busqueda.current.value.lower().strip()
            if not texto:
                lista_resultados.current.controls = []
                contenedor_busqueda.current.visible = False
                contenedor_busqueda.current.update()
                return

            coincidencias = [m for m in todos if texto in m["nombre"].lower() or texto in m["cedula"].lower()]
            lista_resultados.current.controls = []
            
            if not coincidencias:
                lista_resultados.current.controls.append(
                    ft.Container(content=ft.Text("No se encontraron miembros coincidentes", color=PASTEL_TEXTO_SEC, size=13), padding=10)
                )
            else:
                for m in coincidencias[:8]:
                    boton = ft.TextButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.PERSON_OUTLINED, size=18, color=PASTEL_VERDE),
                            ft.Text(f'{m["nombre"]}', weight=ft.FontWeight.W_500, color=PASTEL_TEXTO_PRI),
                            ft.Text(f'— C.I: {m["cedula"]}', color=PASTEL_TEXTO_SEC, size=12)
                        ], spacing=8),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                        on_click=lambda ev, mm=m: seleccionar(mm)
                    )
                    lista_resultados.current.controls.append(boton)

            contenedor_busqueda.current.visible = True
            contenedor_busqueda.current.update()

        def abrir_fecha(e):
            abrir_datepicker_solo_fecha(e, campo_fecha.current, formato="%d/%m/%Y")

        def exportar_pdf(e: ft.FilePickerUploadEvent):
            if not e.path:
                return

            destino = e.path
            if not destino.lower().endswith(".pdf"):
                destino += ".pdf"

            nombre = txt_nombre.current.value
            cedula = txt_cedula.current.value
            direccion = txt_direccion.current.value
            
            if nombre == "Sin seleccionar":
                return

            fecha = campo_fecha.current.value.strip()
            tiempo = campo_tiempo.current.value.replace(" años", "") if campo_tiempo.current.value else "___"

            encargado_nombre = "________________"
            encargado_cedula = "________________"
            encargado_rol = "Líder Político"
            encargado_telefono = ""

            p_actual = e.page
            if hasattr(p_actual, "session_usuario_id") and p_actual.session_usuario_id:
                try:
                    session = SessionLocal()
                    usuario = session.query(Usuario).filter(Usuario.id == p_actual.session_usuario_id).first()
                    session.close()
                    if usuario:
                        encargado_nombre = f"{usuario.nombre} {usuario.apellido}"
                        encargado_cedula = usuario.cedula
                        encargado_rol = usuario.rol if usuario.rol else "Líder Político"
                        encargado_telefono = getattr(usuario, "telefono", "") or getattr(usuario, "tlf", "") or ""
                except Exception as ex_u:
                    print(f"Error consultando usuario: {ex_u}")

            generar_pdf_residencia_rapido(
                nombre, cedula, direccion, tiempo, fecha,
                encargado_nombre, encargado_cedula, encargado_rol, encargado_telefono, destino
            )

            dlg = ft.AlertDialog(
                title=ft.Text("Carta Generada Exitosamente", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                content=ft.Text(f"La carta de residencia fue guardada en:\n{destino}", color=PASTEL_TEXTO_SEC),
                actions=[ft.TextButton("Aceptar", on_click=lambda ev: ev.page.close_dialog())]
            )
            e.page.dialog = dlg
            dlg.open = True
            e.page.update()

        file_picker = ft.FilePicker(on_result=exportar_pdf)

        def generar_carta(e):
            cedula = txt_cedula.current.value
            if cedula == "Sin seleccionar" or not txt_nombre.current.value:
                e.page.snack_bar = ft.SnackBar(ft.Text("Debe seleccionar un miembro primero."))
                e.page.snack_bar.open = True
                e.page.update()
                return

            if file_picker not in e.page.overlay:
                e.page.overlay.append(file_picker)
                e.page.update()

            file_picker.save_file(dialog_title="Guardar carta de residencia...", file_name=f"Carta_Residencia_{cedula}.pdf")

        def mostrar_vista_previa(e):
            nombre = txt_nombre.current.value
            cedula = txt_cedula.current.value
            direccion = txt_direccion.current.value
            fecha = campo_fecha.current.value.strip()
            tiempo = campo_tiempo.current.value or "Sin especificar"

            if nombre == "Sin seleccionar" or not nombre:
                e.page.snack_bar = ft.SnackBar(ft.Text("Selecciona primero un miembro para ver la carta."))
                e.page.snack_bar.open = True
                e.page.update()
                return

            encargado_nombre = "________________"
            encargado_cedula = "________________"
            encargado_rol = "Líder Político"

            user_id = getattr(e.page, "session_usuario_id", None)
            if user_id:
                try:
                    with SessionLocal() as session:
                        usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
                        if usuario:
                            encargado_nombre = f"{usuario.nombre} {usuario.apellido}"
                            encargado_cedula = usuario.cedula
                            encargado_rol = usuario.rol if usuario.rol else "Líder Político"
                except Exception as ex_p:
                    print(f"Error consultando usuario en previa: {ex_p}")

            documento = ft.Container(
                content=ft.Column(
                    [
                        ft.Text("REPÚBLICA BOLIVARIANA DE VENEZUELA", size=11, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="#1E293B"),
                        ft.Text("MUNICIPIO JOSÉ TADEO MONAGAS - ESTADO GUÁRICO", size=10, text_align=ft.TextAlign.CENTER, color="#475569"),
                        ft.Text('CONSEJO COMUNAL "PUEBLO NUEVO"', size=11, weight=ft.FontWeight.BOLD, color=PASTEL_VERDE, text_align=ft.TextAlign.CENTER),
                        ft.Divider(color=PASTEL_BORDE),
                        ft.Text("CARTA DE RESIDENCIA", size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="#0F172A"),
                        ft.Container(height=8),
                        ft.Text(f'Quien suscribe, {encargado_nombre}, titular de la cédula N° {encargado_cedula}, en su condición de {encargado_rol}, hace constar que {nombre}, titular de la cédula N° {cedula}, reside permanentemente en {direccion}.', size=12, text_align=ft.TextAlign.JUSTIFY, color="#334155"),
                        ft.Text(f"Se hace constar que reside en la dirección indicada desde hace aproximadamente {tiempo}.", size=12, text_align=ft.TextAlign.JUSTIFY, color="#334155"),
                        ft.Text(f"Constancia que se expide en Altagracia de Orituco, a los {fecha}.", size=12, text_align=ft.TextAlign.JUSTIFY, color="#334155"),
                        ft.Container(height=20),
                        ft.Text("________________________________", text_align=ft.TextAlign.CENTER, color="#64748B"),
                        ft.Text(encargado_nombre, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, color="#0F172A"),
                        ft.Text(f"C.I.: {encargado_cedula}", text_align=ft.TextAlign.CENTER, color="#475569"),
                        ft.Text(encargado_rol, text_align=ft.TextAlign.CENTER, color="#475569"),
                        ft.Container(height=10),
                        ft.Text("Vista previa - documento aún no generado", size=10, color=PASTEL_TEXTO_SEC, italic=True, text_align=ft.TextAlign.CENTER),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                bgcolor=COLOR_BLANCO,
                border=ft.border.all(1, PASTEL_BORDE),
                border_radius=10,
                padding=30,
                width=580,
            )

            def cerrar_vista_previa(ev):
                ev.page.close(dialogo)

            def generar_desde_vista_previa(ev):
                ev.page.close(dialogo)
                generar_carta(ev)

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Vista previa de la Carta de Residencia", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                content=documento,
                actions=[
                    ft.TextButton("Cerrar", on_click=cerrar_vista_previa),
                    ft.ElevatedButton("Generar PDF", icon=ft.Icons.PICTURE_AS_PDF, bgcolor=PASTEL_VERDE, color=COLOR_BLANCO, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=generar_desde_vista_previa),
                ],
            )
            e.page.open(dialogo)

        # UI Principal
        titulo = ft.Row([
            ft.Icon(ft.Icons.ASSIGNMENT_IND_ROUNDED, size=28, color=PASTEL_VERDE),
            ft.Text("Emisión de Carta de Residencia", size=24, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI)
        ], spacing=10)

        campo_busqueda.current = ft.TextField(
            hint_text="Buscar miembro por nombre, apellido o cédula...",
            prefix_icon=ft.Icons.SEARCH,
            bgcolor=PASTEL_CAMPO_BG,
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            border_radius=10,
            width=520,
            height=45,
            content_padding=ft.padding.symmetric(horizontal=15, vertical=0),
            on_change=buscar
        )

        lista_resultados.current = ft.Column([], spacing=2)

        contenedor_busqueda.current = ft.Container(
            content=ft.Column([lista_resultados.current], scroll=ft.ScrollMode.AUTO, height=180),
            bgcolor=PASTEL_CARD,
            padding=10,
            border_radius=10,
            border=ft.border.all(1, PASTEL_BORDE),
            width=520,
            shadow=ft.BoxShadow(blur_radius=8, color="#0000000A", offset=ft.Offset(0, 3)),
            visible=False
        )

        txt_nombre.current = ft.Text("Sin seleccionar", size=14, weight=ft.FontWeight.W_500, color=PASTEL_TEXTO_SEC)
        txt_cedula.current = ft.Text("Sin seleccionar", size=14, weight=ft.FontWeight.W_500, color=PASTEL_TEXTO_SEC)
        txt_direccion.current = ft.Text("Sin seleccionar", size=14, weight=ft.FontWeight.W_500, color=PASTEL_TEXTO_SEC)

        tarjeta_miembro = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.BADGE_OUTLINED, color=PASTEL_VERDE, size=20),
                    ft.Text("Datos del Solicitante Seleccionado", size=14, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI)
                ], spacing=8),
                ft.Divider(color=PASTEL_BORDE, height=10),
                ft.Row([ft.Text("Nombre completo:", size=13, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC, width=130), txt_nombre.current]),
                ft.Row([ft.Text("Cédula de Identidad:", size=13, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC, width=130), txt_cedula.current]),
                ft.Row([ft.Text("Dirección de Residencia:", size=13, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC, width=130), txt_direccion.current]),
            ], spacing=8),
            bgcolor=PASTEL_CAMPO_BG,
            border=ft.border.all(1, PASTEL_BORDE),
            border_radius=10,
            padding=15
        )

        campo_fecha.current = ft.TextField(
            label="Fecha de Emisión",
            hint_text="dd/mm/aaaa",
            bgcolor=PASTEL_CAMPO_BG,
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            border_radius=10,
            width=170,
            height=45,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
            read_only=True,
            value=datetime.now().strftime("%d/%m/%Y")
        )

        boton_fecha = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            tooltip="Seleccionar fecha",
            icon_color=PASTEL_VERDE,
            on_click=abrir_fecha
        )

        # --- CORRECCIÓN AQUÍ: Se eliminó el parámetro height=45 ---
        campo_tiempo.current = ft.Dropdown(
            label="Tiempo habitando",
            width=180,
            value="1 años",
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            border_radius=10,
            options=[ft.dropdown.Option(f"{a} años") for a in range(1, 31)]
        )

        boton_generar = ft.ElevatedButton(
            text="Generar PDF",
            bgcolor=PASTEL_VERDE,
            color=COLOR_BLANCO,
            icon=ft.Icons.PICTURE_AS_PDF,
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=2),
            on_click=generar_carta
        )

        boton_preview = ft.OutlinedButton(
            "Vista Previa",
            icon=ft.Icons.PREVIEW,
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, PASTEL_BORDE)),
            on_click=mostrar_vista_previa
        )

        return ft.Container(
            content=ft.Column([
                titulo,
                ft.Text("Generación rápida de documentos de residencia comunitarios.", size=13, color=PASTEL_TEXTO_SEC),
                ft.Divider(color=PASTEL_BORDE, height=15),
                
                ft.Text("Paso 1: Buscar Miembro de la Comunidad", size=15, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                ft.Column([campo_busqueda.current, contenedor_busqueda.current], spacing=5),
                
                ft.Container(height=5),
                
                ft.Text("Paso 2: Confirmar Parámetros y Generar", size=15, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                tarjeta_miembro,
                
                ft.Row([
                    ft.Row([campo_fecha.current, boton_fecha], spacing=5),
                    campo_tiempo.current
                ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Container(height=10),
                
                ft.Row([boton_preview, boton_generar], alignment=ft.MainAxisAlignment.END, spacing=15)
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            bgcolor=PASTEL_CARD,
            padding=25,
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=10, color="#0000000D", offset=ft.Offset(0, 4)),
            margin=15,
            expand=True
        )

    except Exception as ex:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE, color="red", size=48),
                ft.Text("Error al cargar la vista de Residencia:", size=16, weight=ft.FontWeight.BOLD, color="red"),
                ft.Text(str(ex), color="black", selectable=True),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            alignment=ft.alignment.center
        )