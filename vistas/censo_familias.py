import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import joinedload

# Módulos locales del proyecto
from colores import (
    COLOR_BLANCO,
    COLOR_GRIS,
    COLOR_NEGRO,
    COLOR_ROJO,
    COLOR_VERDE,
)
from exportador import exportar_backup_json, exportar_censo_a_excel
from generador_reportes import generar_pdf_familias
from importador import importar_backup_json, importar_censo_desde_excel
from modelo import Calle, Familia, Miembro, SessionLocal
from utiles import (
    abrir_datepicker_fecha_nacimiento,
    abrir_datepicker_solo_fecha,
    calcular_edad_detallada,
    validar_cedula,
    validar_telefono,
)

# ==========================================
# PALETA DE COLORES PASTELES DE LA INTERFAZ
# ==========================================
PASTEL_BG = "#F7F9FB"
PASTEL_CARD = "#FFFFFF"
PASTEL_BORDER = "#E2E8F0"

PASTEL_AZUL = "#E8F1F5"
PASTEL_AZUL_TEXTO = "#2B4C6F"

PASTEL_VERDE = "#E8F5E9"
PASTEL_VERDE_TEXTO = "#2E5A36"

PASTEL_AMARILLO = "#FFF8E7"
PASTEL_AMARILLO_TEXTO = "#7A5C00"

PASTEL_MORADO = "#F3E5F5"
PASTEL_MORADO_TEXTO = "#5A2E61"

ACCENT_VERDE_DARK = "#4CAF50"
ACCENT_ROJO = "#E57373"


def _edad_en_meses(fecha_nacimiento, hoy=None):
    if not fecha_nacimiento:
        return None
    hoy = hoy or datetime.date.today()
    meses = (hoy.year - fecha_nacimiento.year) * 12 + hoy.month - fecha_nacimiento.month
    if hoy.day < fecha_nacimiento.day:
        meses -= 1
    return max(meses, 0)


def _persona_esta_en_rango(fecha_nacimiento, rango):
    meses = _edad_en_meses(fecha_nacimiento)
    if meses is None:
        return False
    limites = {
        "Bebés (0-23 meses)": (0, 23),
        "Niños (2-11 años)": (24, 143),
        "Adolescentes (12-17 años)": (144, 215),
        "Adultos (18-59 años)": (216, 719),
        "Adultos mayores (60+)": (720, None),
    }.get(rango)
    return limites is None or (meses >= limites[0] and (limites[1] is None or meses <= limites[1]))


# ==========================================
# 1. VISTA PRINCIPAL CENSO DE FAMILIAS
# ==========================================
def vista_familia(pagina: ft.Page):
    registros_por_pagina = 5
    pagina_actual = ft.Ref[int]()
    pagina_actual.current = 0

    buscador = ft.Ref[ft.TextField]()
    filtro_calle = ft.Ref[ft.Dropdown]()
    filtro_edad = ft.Ref[ft.Dropdown]()
    tipo_busqueda = ft.Ref[ft.Dropdown]()
    tabla = ft.Ref[ft.DataTable]()
    pie_tabla = ft.Ref[ft.Row]()

    txt_total_familias = ft.Ref[ft.Text]()
    txt_total_personas = ft.Ref[ft.Text]()
    txt_total_menores = ft.Ref[ft.Text]()
    txt_total_mayores = ft.Ref[ft.Text]()

    resultados_filtrados = []

    # --- FilePickers ---
    def guardar_excel_seleccionado(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path if e.path.endswith(".xlsx") else f"{e.path}.xlsx"
            exito = exportar_censo_a_excel(ruta)
            mensaje = f"Censo exportado con éxito a:\n{ruta}" if exito else "Ocurrió un error al exportar."
            dlg = ft.AlertDialog(
                title=ft.Text("Exportación Excel"),
                content=ft.Text(mensaje),
                actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
            )
            e.page.open(dlg)

    file_picker_exportar_excel = ft.FilePicker(on_result=guardar_excel_seleccionado)
    pagina.overlay.append(file_picker_exportar_excel)

    def guardar_json_seleccionado(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path if e.path.endswith(".json") else f"{e.path}.json"
            exito = exportar_backup_json(ruta)
            mensaje = f"Respaldo JSON guardado con éxito en:\n{ruta}" if exito else "Ocurrió un error al exportar."
            dlg = ft.AlertDialog(
                title=ft.Text("Respaldo JSON"),
                content=ft.Text(mensaje),
                actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
            )
            e.page.open(dlg)

    file_picker_exportar_json = ft.FilePicker(on_result=guardar_json_seleccionado)
    pagina.overlay.append(file_picker_exportar_json)

    def exportar_pdf(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path if e.path.endswith(".pdf") else f"{e.path}.pdf"
            exito = generar_pdf_familias(resultados_filtrados, ruta)
            mensaje = f"PDF generado con éxito en:\n{ruta}" if exito else "Ocurrió un error al generar el PDF."
            dlg = ft.AlertDialog(
                title=ft.Text("Exportación PDF"),
                content=ft.Text(mensaje),
                actions=[ft.TextButton("Aceptar", on_click=lambda ev: ev.page.close(dlg))],
            )
            e.page.open(dlg)

    file_picker = ft.FilePicker(on_result=lambda e: exportar_pdf(e))
    pagina.overlay.append(file_picker)

    def procesar_excel_seleccionado(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            ruta_excel = e.files[0].path
            exito = importar_censo_desde_excel(ruta_excel)
            actualizar_tabla()
            mensaje = "El archivo Excel ha sido procesado con éxito en la base de datos." if exito else "Ocurrió un error al importar el archivo Excel."
            dlg = ft.AlertDialog(
                title=ft.Text("Importación Excel"),
                content=ft.Text(mensaje),
                actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
            )
            e.page.open(dlg)

    file_picker_excel = ft.FilePicker(on_result=procesar_excel_seleccionado)
    pagina.overlay.append(file_picker_excel)

    def procesar_json_seleccionado(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            ruta_json = e.files[0].path
            exito = importar_backup_json(ruta_json)
            actualizar_tabla()
            mensaje = "El respaldo JSON ha sido procesado con éxito en la base de datos." if exito else "Ocurrió un error al importar el archivo JSON."
            dlg = ft.AlertDialog(
                title=ft.Text("Importación JSON"),
                content=ft.Text(mensaje),
                actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
            )
            e.page.open(dlg)

    file_picker_importar_json = ft.FilePicker(on_result=procesar_json_seleccionado)
    pagina.overlay.append(file_picker_importar_json)

    def eliminar_familia(fid, e):
        session = SessionLocal()
        familia = session.query(Familia).filter(Familia.id == fid).first()
        if familia:
            session.delete(familia)
            session.commit()
        session.close()
        actualizar_tabla()

    def filtrar_datos():
        session = SessionLocal()
        familias = (
            session.query(Familia)
            .options(joinedload(Familia.miembros), joinedload(Familia.calle))
            .all()
        )
        session.close()

        texto = (
            buscador.current.value.lower().strip()
            if buscador.current and buscador.current.value
            else ""
        )
        calle_filtro = (
            filtro_calle.current.value.lower().strip()
            if filtro_calle.current and filtro_calle.current.value
            else None
        )
        edad_filtro = filtro_edad.current.value if filtro_edad.current and filtro_edad.current.value else None
        campo_busqueda = (tipo_busqueda.current.value if tipo_busqueda.current else None) or "Nombre"

        filtradas = []
        for f in familias:
            nombre_calle = (f.calle.nombre if f.calle else "").lower()
            personas = [f.fecha_nacimiento_jefe] + [m.fecha_nacimiento for m in f.miembros]
            nombres = [
                f"{f.nombres_jefe or ''} {f.apellidos_jefe or ''}".lower()
            ] + [f"{m.nombres or ''} {m.apellidos or ''}".lower() for m in f.miembros]
            cedulas = [str(f.cedula_jefe or "")] + [str(m.cedula or "") for m in f.miembros]

            coincide_edad = (
                not edad_filtro
                or any(_persona_esta_en_rango(fecha, edad_filtro) for fecha in personas)
            )

            if not texto:
                coincide_busqueda = True
            elif campo_busqueda == "Nombre":
                coincide_busqueda = any(texto in nombre for nombre in nombres)
            elif campo_busqueda == "Cédula":
                coincide_busqueda = any(texto in cedula.lower() for cedula in cedulas)
            else:
                coincide_busqueda = any(
                    texto in calcular_edad_detallada(fecha).lower()
                    for fecha in personas
                )

            coincide_calle = True
            if calle_filtro:
                coincide_calle = calle_filtro in nombre_calle

            if coincide_busqueda and coincide_calle and coincide_edad:
                filtradas.append(f)

        return filtradas

    def actualizar_tarjetas():
        total_familias = len(resultados_filtrados)
        total_personas = sum(len(f.miembros) + 1 for f in resultados_filtrados)
        edades = [
            f.fecha_nacimiento_jefe for f in resultados_filtrados
        ] + [
            miembro.fecha_nacimiento
            for f in resultados_filtrados
            for miembro in f.miembros
        ]

        total_menores = sum(
            1 for fecha in edades
            if _edad_en_meses(fecha) is not None and _edad_en_meses(fecha) < 216
        )
        total_mayores = sum(
            1 for fecha in edades
            if _edad_en_meses(fecha) is not None and _edad_en_meses(fecha) >= 216
        )

        if txt_total_familias.current:
            txt_total_familias.current.value = str(total_familias)
            if txt_total_familias.current.page:
                txt_total_familias.current.update()

        if txt_total_personas.current:
            txt_total_personas.current.value = str(total_personas)
            if txt_total_personas.current.page:
                txt_total_personas.current.update()

        if txt_total_menores.current:
            txt_total_menores.current.value = str(total_menores)
            if txt_total_menores.current.page:
                txt_total_menores.current.update()

        if txt_total_mayores.current:
            txt_total_mayores.current.value = str(total_mayores)
            if txt_total_mayores.current.page:
                txt_total_mayores.current.update()

    def mostrar_detalle(familia, e):
        personas = [
            ft.Text(
                f"Jefe: {familia.nombres_jefe} {familia.apellidos_jefe} | "
                f"ID: {familia.tipo_id}-{familia.cedula_jefe} | "
                f"Edad: {calcular_edad_detallada(familia.fecha_nacimiento_jefe)}",
                weight=ft.FontWeight.BOLD,
                color="#2C3E50"
            )
        ]
        if familia.miembros:
            personas.append(ft.Divider(color=PASTEL_BORDER))
            personas.append(ft.Text("Carga familiar", weight=ft.FontWeight.BOLD, color="#2C3E50"))
            personas.extend(
                ft.Text(
                    f"• {miembro.nombres} {miembro.apellidos} | "
                    f"{miembro.parentesco} | ID: {miembro.tipo_id}-{miembro.cedula} | "
                    f"Edad: {calcular_edad_detallada(miembro.fecha_nacimiento)}",
                    color="#4A5568"
                )
                for miembro in familia.miembros
            )
        else:
            personas.append(ft.Text("No tiene carga familiar registrada.", color="#718096"))

        dialogo = ft.AlertDialog(
            title=ft.Text(
                f"Registro de {familia.nombres_jefe} {familia.apellidos_jefe}",
                weight=ft.FontWeight.BOLD,
            ),
            content=ft.Column(personas, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    style=ft.ButtonStyle(color="#4A5568"),
                    on_click=lambda ev: ev.page.close(dialogo),
                )
            ],
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        e.page.open(dialogo)

    def actualizar_tabla():
        nonlocal resultados_filtrados
        resultados_filtrados = filtrar_datos()
        total_paginas = max(1, (len(resultados_filtrados) + registros_por_pagina - 1) // registros_por_pagina)

        pagina_actual.current = min(pagina_actual.current, max(total_paginas - 1, 0))
        inicio = pagina_actual.current * registros_por_pagina
        fin = inicio + registros_por_pagina
        visibles = resultados_filtrados[inicio:fin]

        if tabla.current:
            tabla.current.rows.clear()
            for f in visibles:
                direccion_completa = f"{f.calle.nombre if f.calle else ''} #{f.casa_num or ''}"
                tabla.current.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                ft.Container(
                                    ft.Text(
                                        f"{f.nombres_jefe} {f.apellidos_jefe}",
                                        weight=ft.FontWeight.W_500,
                                        color="#2D3748",
                                    ),
                                    width=200,
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    ft.Text(f"{f.tipo_id}-{f.cedula_jefe}", color="#4A5568"),
                                    width=140,
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    ft.Text(f.telefono_jefe or "", color="#4A5568"), width=140
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    ft.Text(direccion_completa, color="#4A5568"), width=280
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    ft.Container(
                                        content=ft.Text(
                                            f"{len(f.miembros)} personas",
                                            size=12,
                                            color=PASTEL_AZUL_TEXTO,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        bgcolor=PASTEL_AZUL,
                                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                        border_radius=12,
                                    ),
                                    width=120,
                                )
                            ),
                            ft.DataCell(
                                ft.Container(
                                    ft.Row(
                                        [
                                            ft.Container(
                                                content=ft.Row(
                                                    [
                                                        ft.Icon(ft.Icons.EDIT, color=ACCENT_VERDE_DARK, size=18),
                                                        ft.Text("Carga", color=ACCENT_VERDE_DARK, size=13, weight="bold"),
                                                    ],
                                                    spacing=4,
                                                ),
                                                tooltip="Editar o agregar carga familiar",
                                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                                bgcolor=PASTEL_VERDE,
                                                border_radius=6,
                                                on_click=lambda e, fid=f.id: e.page.go(
                                                    f"/registro_familia?edit={fid}"
                                                ),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.VISIBILITY_OUTLINED,
                                                icon_color="#4A5568",
                                                icon_size=20,
                                                tooltip="Ver registro y carga familiar",
                                                on_click=lambda ev, fam=f: mostrar_detalle(fam, ev),
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.DELETE_OUTLINED,
                                                icon_color=ACCENT_ROJO,
                                                icon_size=20,
                                                tooltip="Eliminar",
                                                on_click=lambda e, fid=f.id: eliminar_familia(fid, e),
                                            ),
                                        ],
                                        spacing=2,
                                    ),
                                    width=150,
                                )
                            ),
                        ]
                    )
                )

        if pie_tabla.current:
            pie_tabla.current.controls = [
                ft.Text(
                    f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} resultados",
                    color="#718096",
                    size=13,
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.KEYBOARD_ARROW_LEFT,
                            tooltip="Anterior",
                            icon_color="#A0AEC0" if pagina_actual.current == 0 else "#2D3748",
                            disabled=pagina_actual.current == 0,
                            on_click=lambda e: cambiar_pagina(pagina_actual.current - 1),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
                            tooltip="Siguiente",
                            icon_color="#A0AEC0" if pagina_actual.current >= total_paginas - 1 else "#2D3748",
                            disabled=pagina_actual.current >= total_paginas - 1,
                            on_click=lambda e: cambiar_pagina(pagina_actual.current + 1),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ]

        actualizar_tarjetas()
        if tabla.current and tabla.current.page:
            tabla.current.update()
        if pie_tabla.current and pie_tabla.current.page:
            pie_tabla.current.update()

    def cambiar_pagina(nueva_pagina):
        pagina_actual.current = max(0, nueva_pagina)
        actualizar_tabla()

    session = SessionLocal()
    calles = session.query(Calle).all()
    session.close()

    filtro_calle.current = ft.Dropdown(
        label="Filtrar por calle",
        width=250,
        border_radius=8,
        options=[ft.dropdown.Option("")] + [ft.dropdown.Option(c.nombre) for c in calles],
        on_change=lambda e: cambiar_pagina(0),
    )

    filtro_edad.current = ft.Dropdown(
        label="Filtrar por edad",
        width=220,
        border_radius=8,
        options=[
            ft.dropdown.Option(""),
            ft.dropdown.Option("Bebés (0-23 meses)"),
            ft.dropdown.Option("Niños (2-11 años)"),
            ft.dropdown.Option("Adolescentes (12-17 años)"),
            ft.dropdown.Option("Adultos (18-59 años)"),
            ft.dropdown.Option("Adultos mayores (60+)")
        ],
        on_change=lambda e: cambiar_pagina(0),
    )

    tipo_busqueda.current = ft.Dropdown(
        label="Buscar por",
        width=150,
        border_radius=8,
        value="Nombre",
        options=[
            ft.dropdown.Option("Nombre"),
            ft.dropdown.Option("Cédula"),
            ft.dropdown.Option("Edad"),
        ],
        on_change=lambda e: actualizar_hint_busqueda(),
    )

    buscador.current = ft.TextField(
        hint_text="Escriba un nombre",
        prefix_icon=ft.Icons.SEARCH,
        width=260,
        border_radius=8,
        on_change=lambda e: cambiar_pagina(0),
    )

    def actualizar_hint_busqueda():
        ayudas = {
            "Nombre": "Escriba un nombre",
            "Cédula": "Escriba una cédula",
            "Edad": "Escriba una edad, meses o RN",
        }
        buscador.current.hint_text = ayudas.get(tipo_busqueda.current.value, "Buscar")
        buscador.current.value = ""
        if buscador.current.page:
            buscador.current.update()
        cambiar_pagina(0)

    # Botones de exportación
    boton_exportar_excel = ft.IconButton(
        icon=ft.Icons.GRID_ON_ROUNDED,
        tooltip="Exportar Censo a Excel",
        icon_color=ACCENT_VERDE_DARK,
        bgcolor=PASTEL_VERDE,
        on_click=lambda e: file_picker_exportar_excel.save_file(
            allowed_extensions=["xlsx"], file_name="Censo_Familias.xlsx"
        ),
    )

    boton_exportar_json = ft.IconButton(
        icon=ft.Icons.DATA_OBJECT_ROUNDED,
        tooltip="Exportar Respaldo JSON",
        icon_color="#3182CE",
        bgcolor=PASTEL_AZUL,
        on_click=lambda e: file_picker_exportar_json.save_file(
            allowed_extensions=["json"], file_name="backup_censo.json"
        ),
    )

    boton_exportar = ft.IconButton(
        icon=ft.Icons.PICTURE_AS_PDF_ROUNDED,
        tooltip="Exportar datos a PDF",
        icon_color="#E53E3E",
        bgcolor="#FFF5F5",
        on_click=lambda e: file_picker.save_file(),
    )

    tarjeta_filtros = ft.Container(
        content=ft.Row(
            [
                filtro_calle.current,
                filtro_edad.current,
                tipo_busqueda.current,
                buscador.current,
                ft.Row([boton_exportar_excel, boton_exportar_json, boton_exportar], spacing=6),
            ],
            spacing=12,
            wrap=True,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        bgcolor=PASTEL_CARD,
        padding=16,
        border_radius=12,
        border=ft.border.all(1, PASTEL_BORDER),
    )

    def crear_tarjeta_resumen(titulo, icono, bg_color, text_color, ref_texto):
        ref_texto.current = ft.Text("0", size=22, weight=ft.FontWeight.BOLD, color=text_color)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icono, color=text_color, size=24),
                        padding=12,
                        bgcolor=PASTEL_CARD,
                        border_radius=10,
                    ),
                    ft.Column(
                        [
                            ft.Text(titulo, size=13, color=text_color, weight=ft.FontWeight.W_600),
                            ref_texto.current,
                        ],
                        spacing=2,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=bg_color,
            padding=16,
            border_radius=12,
            expand=True,
        )

    tarjeta_familias_cnt = crear_tarjeta_resumen("Familias Registradas", ft.Icons.HOLIDAY_VILLAGE_ROUNDED, PASTEL_AZUL, PASTEL_AZUL_TEXTO, txt_total_familias)
    tarjeta_personas_cnt = crear_tarjeta_resumen("Personas en Censo", ft.Icons.PEOPLE_ALT_ROUNDED, PASTEL_VERDE, PASTEL_VERDE_TEXTO, txt_total_personas)
    tarjeta_menores_cnt = crear_tarjeta_resumen("Menores de edad (<18)", ft.Icons.CHILD_CARE_ROUNDED, PASTEL_AMARILLO, PASTEL_AMARILLO_TEXTO, txt_total_menores)
    tarjeta_mayores_cnt = crear_tarjeta_resumen("Mayores de edad (18+)", ft.Icons.SUPERVISED_USER_CIRCLE_ROUNDED, PASTEL_MORADO, PASTEL_MORADO_TEXTO, txt_total_mayores)

    resumen = ft.Row(
        [
            tarjeta_familias_cnt,
            tarjeta_personas_cnt,
            tarjeta_menores_cnt,
            tarjeta_mayores_cnt,
        ],
        spacing=16,
    )

    encabezado = ft.Row(
        [
            ft.Text("Censo de Familias", size=28, weight=ft.FontWeight.BOLD, color="#1A202C"),
            ft.Row(
                [
                    ft.OutlinedButton(
                        "Cargar Excel",
                        icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), color="#4A5568"),
                        on_click=lambda _: file_picker_excel.pick_files(
                            allowed_extensions=["xlsx", "xls"],
                            file_type=ft.FilePickerFileType.CUSTOM,
                            dialog_title="Seleccione el archivo de Censo Excel",
                        ),
                    ),
                    ft.OutlinedButton(
                        "Cargar JSON",
                        icon=ft.Icons.FILE_UPLOAD_ROUNDED,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), color="#4A5568"),
                        on_click=lambda _: file_picker_importar_json.pick_files(
                            allowed_extensions=["json"],
                            file_type=ft.FilePickerFileType.CUSTOM,
                            dialog_title="Seleccione el archivo de Respaldo JSON",
                        ),
                    ),
                    ft.ElevatedButton(
                        "+ Agregar Familia",
                        bgcolor=ACCENT_VERDE_DARK,
                        color=COLOR_BLANCO,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=lambda e: e.page.go("/registro_familia"),
                    ),
                ],
                spacing=10,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    tabla.current = ft.DataTable(
        heading_row_color=PASTEL_BG,
        heading_row_height=48,
        data_row_min_height=52,
        divider_thickness=0.5,
        columns=[
            ft.DataColumn(ft.Text("LÍDER DE FAMILIA", weight=ft.FontWeight.BOLD, color="#718096")),
            ft.DataColumn(ft.Text("CÉDULA", weight=ft.FontWeight.BOLD, color="#718096")),
            ft.DataColumn(ft.Text("TELÉFONO", weight=ft.FontWeight.BOLD, color="#718096")),
            ft.DataColumn(ft.Text("DIRECCIÓN", weight=ft.FontWeight.BOLD, color="#718096")),
            ft.DataColumn(ft.Text("CARGA FAMILIAR", weight=ft.FontWeight.BOLD, color="#718096")),
            ft.DataColumn(ft.Text("ACCIONES", weight=ft.FontWeight.BOLD, color="#718096")),
        ],
        rows=[],
    )

    pie_tabla.current = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    pie_card = ft.Container(
        content=pie_tabla.current,
        bgcolor=PASTEL_CARD,
        padding=ft.padding.symmetric(horizontal=20, vertical=8),
        border_radius=12,
        border=ft.border.all(1, PASTEL_BORDER),
    )

    columna = ft.Column(
        controls=[
            encabezado,
            resumen,
            tarjeta_filtros,
            ft.Container(
                content=tabla.current,
                bgcolor=PASTEL_CARD,
                padding=12,
                border_radius=12,
                border=ft.border.all(1, PASTEL_BORDER),
                expand=True,
            ),
            pie_card,
        ],
        spacing=16,
        scroll="auto",
        expand=True,
    )

    actualizar_tabla()

    def inicializar():
        actualizar_tabla()

    return {"vista": columna, "actualizar": inicializar}

def vista_registro_familia(pagina=None, edit_id=None):
    miembros = []
    session = SessionLocal()
    calles = session.query(Calle).all()
    familia_edicion = None
    if edit_id is not None:
        familia_edicion = (
            session.query(Familia)
            .options(joinedload(Familia.miembros))
            .filter(Familia.id == edit_id)
            .first()
        )
    session.close()

    opciones_calles = [
        ft.dropdown.Option(key=str(c.id), text=c.nombre) for c in calles
    ]

    # --- ESTILOS REUTILIZABLES ---
    BG_CAMPO = "#FDFDFD"
    
    # --- CAMPOS DEL JEFE DE FAMILIA ---
    nombres_jefe = ft.TextField(label="Nombres", expand=True, border_radius=10, bgcolor=BG_CAMPO, focused_border_color=ACCENT_VERDE_DARK)
    apellidos_jefe = ft.TextField(label="Apellidos", expand=True, border_radius=10, bgcolor=BG_CAMPO, focused_border_color=ACCENT_VERDE_DARK)

    tipo_cedula_jefe = ft.Dropdown(
        label="Tipo ID",
        width=110,
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula_jefe = ft.TextField(
        label="Cédula de Identidad",
        expand=True,
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: validar_cedula(e, cedula_jefe),
    )
    telefono_jefe = ft.TextField(
        label="Número de Teléfono",
        expand=True,
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: validar_telefono(e, telefono_jefe),
    )

    calle_jefe = ft.Dropdown(label="Calle", expand=True, border_radius=10, bgcolor=BG_CAMPO, focused_border_color=ACCENT_VERDE_DARK, options=opciones_calles)
    numero_casa_jefe = ft.TextField(label="N° de Casa", width=160, border_radius=10, bgcolor=BG_CAMPO, focused_border_color=ACCENT_VERDE_DARK)

    fecha_nacimiento_jefe = ft.TextField(
        label="Fecha de Nacimiento", width=180, read_only=True, border_radius=10, bgcolor=BG_CAMPO
    )
    edad_jefe = ft.TextField(label="Edad", width=100, disabled=True, border_radius=10, bgcolor="#F4F6F6")

    beneficiario = ft.Dropdown(
        label="¿Es beneficiario?",
        width=170,
        value="No",
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        options=[ft.dropdown.Option("Si"), ft.dropdown.Option("No")],
    )

    nombres_bonos = [
        "Ingreso integral trabajadores activos",
        "Ingreso integral jubilados",
        "Ingreso integral pensionados",
        "Bono unico familiar",
        "Corresponsabilidad y formacion",
        "Responsabilidad profesional",
        "Becas universitaria/enseñanza media",
        "Somos Venezuela",
    ]

    def actualizar_beneficiario(e):
        beneficiario.value = "Si" if any(control.value for control in bonos_seleccionados.values()) else "No"
        beneficiario.update()

    bonos_seleccionados = {
        nombre: ft.Checkbox(label=nombre, value=False, active_color=ACCENT_VERDE_DARK, on_change=actualizar_beneficiario)
        for nombre in nombres_bonos
    }

    selector_bonos = ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.CARD_GIFTCARD_ROUNDED, color=ACCENT_VERDE_DARK, size=20),
                    ft.Text("Bonos o beneficios (puede seleccionar varios)", weight=ft.FontWeight.BOLD, color="#2C3E50"),
                ], spacing=8),
                ft.ResponsiveRow(
                    [ft.Container(control, col={"sm": 12, "md": 6}) for control in bonos_seleccionados.values()],
                    spacing=0,
                ),
            ],
            spacing=10,
        ),
        bgcolor=PASTEL_CARD,
        border=ft.border.all(1, PASTEL_BORDER),
        border_radius=12,
        padding=16,
        shadow=ft.BoxShadow(blur_radius=6, color="#00000005", offset=ft.Offset(0, 2)),
    )

    boton_fecha_jefe = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
        icon_color=ACCENT_VERDE_DARK,
        tooltip="Seleccionar fecha",
        on_click=lambda e: abrir_datepicker_fecha_nacimiento(
            e,
            fecha_nacimiento_jefe,
            edad_jefe,
            formato="%d-%m-%Y",
            fecha_minima=datetime.datetime(1900, 1, 1),
        ),
    )

    # --- CAMPOS DE MIEMBROS DE LA CARGA FAMILIAR ---
    nombres_miembro = ft.TextField(label="Nombres", width=180, border_radius=10, bgcolor=BG_CAMPO, focused_border_color=ACCENT_VERDE_DARK)
    apellidos_miembro = ft.TextField(label="Apellidos", width=180, border_radius=10, bgcolor=BG_CAMPO, focused_border_color=ACCENT_VERDE_DARK)

    tipo_cedula_miembro = ft.Ref[ft.Dropdown]()
    tipo_cedula_miembro.current = ft.Dropdown(
        label="Tipo ID",
        width=110,
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula_miembro = ft.TextField(
        label="Cédula",
        width=150,
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: validar_cedula(e, cedula_miembro),
    )

    fecha_nacimiento_miembro = ft.TextField(
        label="F. Nacimiento", width=150, read_only=True, border_radius=10, bgcolor=BG_CAMPO
    )
    edad_miembro = ft.TextField(label="Edad", width=90, disabled=True, border_radius=10, bgcolor="#F4F6F6")

    parentesco_miembro = ft.Ref[ft.Dropdown]()
    parentesco_miembro.current = ft.Dropdown(
        label="Parentesco",
        width=160,
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        options=[
            ft.dropdown.Option("Seleccione"),
            ft.dropdown.Option("Conyuge"),
            ft.dropdown.Option("Hijo/a"),
            ft.dropdown.Option("Nieto/a"),
            ft.dropdown.Option("Otro"),
        ],
    )

    beneficiario_miembro = ft.Dropdown(
        label="Beneficiario",
        width=130,
        value="No",
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        options=[ft.dropdown.Option("Si"), ft.dropdown.Option("No")],
    )

    bonos_miembro = ft.Dropdown(
        label="Bono del integrante",
        width=240,
        value="Ninguno",
        border_radius=10,
        bgcolor=BG_CAMPO,
        focused_border_color=ACCENT_VERDE_DARK,
        options=[ft.dropdown.Option("Ninguno")] + [ft.dropdown.Option(nombre) for nombre in nombres_bonos],
    )

    boton_fecha_miembro = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
        icon_color=ACCENT_VERDE_DARK,
        tooltip="Seleccionar fecha",
        on_click=lambda e: abrir_datepicker_fecha_nacimiento(
            e,
            fecha_nacimiento_miembro,
            edad_miembro,
            formato="%d-%m-%Y",
            fecha_minima=datetime.datetime(1900, 1, 1),
        ),
    )

    tabla_miembros = ft.Column([], spacing=8)

    def añadir_miembro(e: ft.ControlEvent):
        if not nombres_miembro.value.strip() or not apellidos_miembro.value.strip():
            snackbar = ft.SnackBar(ft.Text("Por favor completa los nombres y apellidos del integrante"))
            e.page.overlay.append(snackbar)
            snackbar.open = True
            e.page.update()
            return

        cedula_valor = cedula_miembro.value.strip() if cedula_miembro.value.strip() else "No posee"

        for m in miembros:
            if m["cedula"] == cedula_valor and cedula_valor != "No posee":
                snackbar = ft.SnackBar(ft.Text(f"⚠️ Ya existe un miembro en la lista con la cédula {cedula_valor}"))
                e.page.overlay.append(snackbar)
                snackbar.open = True
                e.page.update()
                return

        session = SessionLocal()
        if cedula_valor != "No posee":
            consulta_miembro = session.query(Miembro).filter(Miembro.cedula == cedula_valor)
            if familia_edicion is not None:
                consulta_miembro = consulta_miembro.filter(Miembro.familia_id != edit_id)
            if consulta_miembro.first():
                snackbar = ft.SnackBar(ft.Text(f"⚠️ Ya existe un integrante en la BD con la cédula {cedula_valor}"))
                e.page.overlay.append(snackbar)
                snackbar.open = True
                e.page.update()
                session.close()
                return
        session.close()

        miembro_data = {
            "nombres": nombres_miembro.value.strip(),
            "apellidos": apellidos_miembro.value.strip(),
            "tipo": tipo_cedula_miembro.current.value or "V",
            "cedula": cedula_valor,
            "fecha_nacimiento": fecha_nacimiento_miembro.value,
            "edad": edad_miembro.value,
            "parentesco": parentesco_miembro.current.value or "Otro",
            "es_beneficiario": beneficiario_miembro.value or "No",
            "bonos": bonos_miembro.value or "Ninguno",
        }

        def eliminar_miembro(ev, m_item, fila_ref):
            miembros.remove(m_item)
            tabla_miembros.controls.remove(fila_ref)
            ev.page.update()

        fila = ft.Container(
            content=ft.Row(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.PERSON_ROUNDED, color=PASTEL_AZUL_TEXTO, size=18),
                        ft.Text(f"{miembro_data['nombres']} {miembro_data['apellidos']}", weight=ft.FontWeight.BOLD, color="#2C3E50"),
                    ], expand=True),
                    ft.Text(f"ID: {miembro_data['tipo']}-{miembro_data['cedula']}", width=150, color="#7F8C8D"),
                    ft.Container(
                        content=ft.Text(miembro_data['parentesco'], size=12, color="#2E7D32", weight=ft.FontWeight.BOLD),
                        bgcolor="#E8F5E9",
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=8,
                    ),
                    ft.Text(f"Edad: {miembro_data['edad']}", width=100, color="#7F8C8D"),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_ROUNDED,
                        icon_color=ACCENT_ROJO,
                        tooltip="Eliminar miembro",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor=PASTEL_BG,
            border_radius=10,
            border=ft.border.all(1, PASTEL_BORDER),
        )

        fila.content.controls[4].on_click = lambda ev, m=miembro_data, f_ctrl=fila: eliminar_miembro(ev, m, f_ctrl)

        miembros.append(miembro_data)
        tabla_miembros.controls.append(fila)

        # Limpiar formulario
        nombres_miembro.value = ""
        apellidos_miembro.value = ""
        cedula_miembro.value = ""
        fecha_nacimiento_miembro.value = ""
        edad_miembro.value = ""
        tipo_cedula_miembro.current.value = "V"
        parentesco_miembro.current.value = None
        beneficiario_miembro.value = "No"
        bonos_miembro.value = "Ninguno"

        e.page.update()

    def guardar_familia(e):
        if not nombres_jefe.value.strip() or not apellidos_jefe.value.strip() or not cedula_jefe.value.strip():
            snackbar = ft.SnackBar(ft.Text("Por favor completa los campos obligatorios del jefe de familia"))
            e.page.overlay.append(snackbar)
            snackbar.open = True
            e.page.update()
            return
        if not calle_jefe.value:
            snackbar = ft.SnackBar(ft.Text("Por favor selecciona una calle"))
            e.page.overlay.append(snackbar)
            snackbar.open = True
            e.page.update()
            return

        session = SessionLocal()
        existente_jefe = (
            session.query(Familia)
            .filter(Familia.cedula_jefe == cedula_jefe.value.strip())
            .first()
        )
        if existente_jefe and (familia_edicion is None or existente_jefe.id != edit_id):
            snackbar = ft.SnackBar(ft.Text("⚠️ Ya existe una familia registrada con esa cédula"))
            e.page.overlay.append(snackbar)
            snackbar.open = True
            e.page.update()
            session.close()
            return

        fecha_jefe = None
        if fecha_nacimiento_jefe.value:
            try:
                try:
                    fecha_jefe = datetime.datetime.strptime(fecha_nacimiento_jefe.value, "%d-%m-%Y").date()
                except ValueError:
                    fecha_jefe = datetime.datetime.strptime(fecha_nacimiento_jefe.value, "%Y-%m-%d").date()
            except Exception:
                fecha_jefe = None

        datos_familia = {
            "nombres_jefe": nombres_jefe.value.strip(),
            "apellidos_jefe": apellidos_jefe.value.strip(),
            "tipo_id": tipo_cedula_jefe.value or "V",
            "cedula_jefe": cedula_jefe.value.strip(),
            "telefono_jefe": telefono_jefe.value.strip(),
            "fecha_nacimiento_jefe": fecha_jefe,
            "calle_id": int(calle_jefe.value),
            "casa_num": numero_casa_jefe.value.strip(),
            "es_beneficiario": beneficiario.value or "No",
            "bono": " | ".join(
                nombre for nombre, control in bonos_seleccionados.items()
                if control.value
            ) or "Ninguno",
        }

        if familia_edicion is not None:
            nueva_familia = session.query(Familia).filter(Familia.id == edit_id).first()
            if not nueva_familia:
                session.close()
                return
            for clave, valor in datos_familia.items():
                setattr(nueva_familia, clave, valor)
            nueva_familia.miembros.clear()
        else:
            nueva_familia = Familia(**datos_familia)

        for m in miembros:
            fecha_m = None
            if m["fecha_nacimiento"]:
                try:
                    try:
                        fecha_m = datetime.datetime.strptime(m["fecha_nacimiento"], "%d-%m-%Y").date()
                    except ValueError:
                        fecha_m = datetime.datetime.strptime(m["fecha_nacimiento"], "%Y-%m-%d").date()
                except Exception:
                    fecha_m = None

            nuevo_miembro = Miembro(
                nombres=m["nombres"],
                apellidos=m["apellidos"],
                tipo_id=m["tipo"] or "V",
                cedula=m["cedula"],
                fecha_nacimiento=fecha_m,
                parentesco=m["parentesco"],
                es_beneficiario=m.get("es_beneficiario", "No"),
                bonos=m.get("bonos", "Ninguno"),
            )
            nueva_familia.miembros.append(nuevo_miembro)

        session.commit()
        session.close()

        mensaje = "✅ Familia actualizada correctamente" if familia_edicion else "✅ Familia guardada correctamente"
        snackbar = ft.SnackBar(ft.Text(mensaje))
        e.page.overlay.append(snackbar)
        snackbar.open = True
        e.page.update()
        e.page.go("/familia")

    # CARGA PREVIA EN CASO DE EDICIÓN
    if familia_edicion:
        nombres_jefe.value = familia_edicion.nombres_jefe or ""
        apellidos_jefe.value = familia_edicion.apellidos_jefe or ""
        tipo_cedula_jefe.value = familia_edicion.tipo_id or "V"
        cedula_jefe.value = familia_edicion.cedula_jefe or ""
        telefono_jefe.value = familia_edicion.telefono_jefe or ""
        calle_jefe.value = str(familia_edicion.calle_id) if familia_edicion.calle_id else None
        numero_casa_jefe.value = familia_edicion.casa_num or ""
        fecha_nacimiento_jefe.value = (
            familia_edicion.fecha_nacimiento_jefe.strftime("%d-%m-%Y")
            if familia_edicion.fecha_nacimiento_jefe else ""
        )
        edad_jefe.value = calcular_edad_detallada(familia_edicion.fecha_nacimiento_jefe)
        beneficiario.value = familia_edicion.es_beneficiario or "No"

        bonos_guardados = (familia_edicion.bono or "").split(" | ")
        for nombre_bono, control in bonos_seleccionados.items():
            control.value = nombre_bono in bonos_guardados

        for miembro in familia_edicion.miembros:
            miembro_data = {
                "nombres": miembro.nombres,
                "apellidos": miembro.apellidos,
                "tipo": miembro.tipo_id or "V",
                "cedula": miembro.cedula,
                "fecha_nacimiento": miembro.fecha_nacimiento.strftime("%d-%m-%Y") if miembro.fecha_nacimiento else "",
                "edad": calcular_edad_detallada(miembro.fecha_nacimiento),
                "parentesco": miembro.parentesco or "Otro",
                "es_beneficiario": miembro.es_beneficiario or "No",
                "bonos": miembro.bonos or "Ninguno",
            }

            def eliminar_existente(ev, m_item, f_cnt):
                miembros.remove(m_item)
                tabla_miembros.controls.remove(f_cnt)
                ev.page.update()

            fila_exist = ft.Container(
                content=ft.Row(
                    [
                        ft.Row([
                            ft.Icon(ft.Icons.PERSON_ROUNDED, color=PASTEL_AZUL_TEXTO, size=18),
                            ft.Text(f"{miembro_data['nombres']} {miembro_data['apellidos']}", weight=ft.FontWeight.BOLD, color="#2C3E50"),
                        ], expand=True),
                        ft.Text(f"ID: {miembro_data['tipo']}-{miembro_data['cedula']}", width=150, color="#7F8C8D"),
                        ft.Container(
                            content=ft.Text(miembro_data['parentesco'], size=12, color="#2E7D32", weight=ft.FontWeight.BOLD),
                            bgcolor="#E8F5E9",
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=8,
                        ),
                        ft.Text(f"Edad: {miembro_data['edad']}", width=100, color="#7F8C8D"),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_ROUNDED,
                            icon_color=ACCENT_ROJO,
                            tooltip="Eliminar integrante",
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                bgcolor=PASTEL_BG,
                border_radius=10,
                border=ft.border.all(1, PASTEL_BORDER),
            )
            fila_exist.content.controls[4].on_click = lambda ev, m=miembro_data, f_ctrl=fila_exist: eliminar_existente(ev, m, f_ctrl)

            miembros.append(miembro_data)
            tabla_miembros.controls.append(fila_exist)

    boton_añadir = ft.ElevatedButton(
        "Añadir",
        icon=ft.Icons.ADD_ROUNDED,
        bgcolor=ACCENT_VERDE_DARK,
        color=COLOR_BLANCO,
        height=45,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=añadir_miembro,
    )

    boton_guardar = ft.ElevatedButton(
        "Actualizar Familia" if familia_edicion else "Guardar Familia",
        icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
        bgcolor=ACCENT_VERDE_DARK,
        color=COLOR_BLANCO,
        height=45,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=guardar_familia,
    )

    boton_cancelar = ft.OutlinedButton(
        "Cancelar",
        height=45,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), color="#7F8C8D"),
        on_click=lambda e: e.page.go("/familia"),
    )

    # --- CONTENEDORES ESTILIZADOS SECTORIZADOS ---
    tarjeta_jefe = ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.BADGE_ROUNDED, color=ACCENT_VERDE_DARK, size=22),
                    ft.Text("Datos del Jefe de Familia", size=18, weight=ft.FontWeight.BOLD, color="#2C3E50"),
                ], spacing=8),
                ft.Row([nombres_jefe, apellidos_jefe], spacing=12),
                ft.Row([tipo_cedula_jefe, cedula_jefe, telefono_jefe], spacing=12),
                ft.Row([calle_jefe, numero_casa_jefe], spacing=12),
                ft.Row([fecha_nacimiento_jefe, boton_fecha_jefe, edad_jefe, beneficiario], spacing=10),
            ],
            spacing=14,
        ),
        bgcolor=PASTEL_CARD,
        border=ft.border.all(1, PASTEL_BORDER),
        border_radius=12,
        padding=18,
        shadow=ft.BoxShadow(blur_radius=6, color="#00000005", offset=ft.Offset(0, 2)),
    )

    tarjeta_carga = ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.FAMILY_RESTROOM_ROUNDED, color=ACCENT_VERDE_DARK, size=22),
                    ft.Text("Carga Familiar (Miembros)", size=18, weight=ft.FontWeight.BOLD, color="#2C3E50"),
                ], spacing=8),
                
                # Fila 1: Nombres, Apellidos, Tipo ID, Cédula
                ft.Row([nombres_miembro, apellidos_miembro, tipo_cedula_miembro.current, cedula_miembro], spacing=10, wrap=True),
                
                # Fila 2: Fecha Nacimiento, Edad, Parentesco, Beneficiario, Bono y Botón Añadir
                ft.Row(
                    [
                        fecha_nacimiento_miembro,
                        boton_fecha_miembro,
                        edad_miembro,
                        parentesco_miembro.current,
                        beneficiario_miembro,
                        bonos_miembro,
                        boton_añadir,
                    ],
                    spacing=10,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=5),
                tabla_miembros,
            ],
            spacing=14,
        ),
        bgcolor=PASTEL_CARD,
        border=ft.border.all(1, PASTEL_BORDER),
        border_radius=12,
        padding=18,
        shadow=ft.BoxShadow(blur_radius=6, color="#00000005", offset=ft.Offset(0, 2)),
    )

    # --- ESTRUCTURA GENERAL DE LA PÁGINA ---
    return ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_ROUNDED,
                        icon_color="#2C3E50",
                        tooltip="Volver",
                        on_click=lambda e: e.page.go("/familia"),
                    ),
                    ft.Text(
                        "Editar Familia" if familia_edicion else "Registro de Nueva Familia",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color="#1A202C",
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                tarjeta_jefe,
                selector_bonos,
                tarjeta_carga,
                
                ft.Row(
                    [boton_cancelar, boton_guardar],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=12,
                ),
            ],
            spacing=18,
            scroll="auto",
        ),
        bgcolor=PASTEL_BG,
        padding=20,
        expand=True,
    )