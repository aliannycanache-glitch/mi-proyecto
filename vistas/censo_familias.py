import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import joinedload
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
    calcular_edad_detallada,
    validar_cedula,
    validar_telefono,
)

# --- Constantes de Colores Pastel para Consistencia del Sistema ---
PASTEL_BG = "#F4F6F8"
PASTEL_CARD = "#FFFFFF"
PASTEL_VERDE = COLOR_VERDE if "COLOR_VERDE" in globals() else "#4CAF50"
PASTEL_TEXTO_PRI = "#2C3E50"
PASTEL_TEXTO_SEC = "#6C757D"
PASTEL_BORDE = "#E0E0E0"
PASTEL_CAMPO_BG = "#F9FAFB"


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


def vista_familia(pagina: ft.Page = None):
    try:
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

        # --- Manejadores de Exportación / Importación (FilePickers) ---
        file_picker_exportar_excel = ft.FilePicker(
            on_result=lambda e: guardar_excel_seleccionado(e)
        )
        if pagina and file_picker_exportar_excel not in pagina.overlay:
            pagina.overlay.append(file_picker_exportar_excel)

        def guardar_excel_seleccionado(e: ft.FilePickerResultEvent):
            if e.path:
                ruta = e.path if e.path.endswith(".xlsx") else f"{e.path}.xlsx"
                exito = exportar_censo_a_excel(ruta)
                mensaje = f"Censo exportado con éxito a:\n{ruta}" if exito else "Ocurrió un error al exportar."
                dlg = ft.AlertDialog(
                    title=ft.Text("Exportación Excel", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    content=ft.Text(mensaje, color=PASTEL_TEXTO_SEC),
                    actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
                )
                e.page.open(dlg)

        file_picker_exportar_json = ft.FilePicker(
            on_result=lambda e: guardar_json_seleccionado(e)
        )
        if pagina and file_picker_exportar_json not in pagina.overlay:
            pagina.overlay.append(file_picker_exportar_json)

        def guardar_json_seleccionado(e: ft.FilePickerResultEvent):
            if e.path:
                ruta = e.path if e.path.endswith(".json") else f"{e.path}.json"
                exito = exportar_backup_json(ruta)
                mensaje = f"Respaldo JSON guardado con éxito en:\n{ruta}" if exito else "Ocurrió un error al exportar."
                dlg = ft.AlertDialog(
                    title=ft.Text("Respaldo JSON", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    content=ft.Text(mensaje, color=PASTEL_TEXTO_SEC),
                    actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
                )
                e.page.open(dlg)

        file_picker = ft.FilePicker(
            on_result=lambda e: exportar_pdf_handler(e)
        )
        if pagina and file_picker not in pagina.overlay:
            pagina.overlay.append(file_picker)

        def exportar_pdf_handler(e: ft.FilePickerResultEvent):
            if e.path:
                ruta = e.path if e.path.endswith(".pdf") else f"{e.path}.pdf"
                exito = generar_pdf_familias(resultados_filtrados, ruta)
                mensaje = f"PDF generado con éxito en:\n{ruta}" if exito else "Ocurrió un error al generar el PDF."
                dlg = ft.AlertDialog(
                    title=ft.Text("Exportación PDF", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    content=ft.Text(mensaje, color=PASTEL_TEXTO_SEC),
                    actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
                )
                e.page.open(dlg)

        file_picker_excel = ft.FilePicker(
            on_result=lambda e: procesar_excel_seleccionado(e)
        )
        if pagina and file_picker_excel not in pagina.overlay:
            pagina.overlay.append(file_picker_excel)

        def procesar_excel_seleccionado(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                ruta_excel = e.files[0].path
                exito = importar_censo_desde_excel(ruta_excel)
                actualizar_tabla()
                mensaje = "El archivo Excel ha sido procesado con éxito en la base de datos." if exito else "Ocurrió un error al importar el archivo Excel."
                dlg = ft.AlertDialog(
                    title=ft.Text("Importación Excel", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    content=ft.Text(mensaje, color=PASTEL_TEXTO_SEC),
                    actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
                )
                e.page.open(dlg)

        file_picker_importar_json = ft.FilePicker(
            on_result=lambda e: procesar_json_seleccionado(e)
        )
        if pagina and file_picker_importar_json not in pagina.overlay:
            pagina.overlay.append(file_picker_importar_json)

        def procesar_json_seleccionado(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                ruta_json = e.files[0].path
                exito = importar_backup_json(ruta_json)
                actualizar_tabla()
                mensaje = "El respaldo JSON ha sido procesado con éxito en la base de datos." if exito else "Ocurrió un error al importar el archivo JSON."
                dlg = ft.AlertDialog(
                    title=ft.Text("Importación JSON", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    content=ft.Text(mensaje, color=PASTEL_TEXTO_SEC),
                    actions=[ft.TextButton("Aceptar", on_click=lambda ev: e.page.close(dlg))],
                )
                e.page.open(dlg)

        # --- Lógica de Negocio ---
        def eliminar_familia(fid, e):
            try:
                with SessionLocal() as session:
                    familia = session.query(Familia).filter(Familia.id == fid).first()
                    if familia:
                        session.delete(familia)
                        session.commit()
                actualizar_tabla()
            except Exception as ex:
                print(f"Error eliminando familia: {ex}")

        def filtrar_datos():
            with SessionLocal() as session:
                familias = (
                    session.query(Familia)
                    .options(joinedload(Familia.miembros), joinedload(Familia.calle))
                    .execution_options(populate_existing=True)
                    .all()
                )

            texto = buscador.current.value.lower().strip() if buscador.current and buscador.current.value else ""
            calle_filtro = filtro_calle.current.value.lower().strip() if filtro_calle.current and filtro_calle.current.value else None
            edad_filtro = filtro_edad.current.value if filtro_edad.current else None
            campo_busq = tipo_busqueda.current.value if tipo_busqueda.current else "Nombre"

            filtradas = []
            for f in familias:
                nombre_calle = f.calle.nombre if f.calle else ""
                personas = [f.fecha_nacimiento_jefe] + [m.fecha_nacimiento for m in f.miembros]
                nombres = [f"{f.nombres_jefe} {f.apellidos_jefe}".lower()] + [f"{m.nombres} {m.apellidos}".lower() for m in f.miembros]
                cedulas = [f.cedula_jefe] + [m.cedula for m in f.miembros]
                coincide_edad = not edad_filtro or any(_persona_esta_en_rango(fecha, edad_filtro) for fecha in personas)

                if not texto:
                    coincide_busqueda = True
                elif campo_busq == "Nombre":
                    coincide_busqueda = any(texto in nombre for nombre in nombres)
                elif campo_busq == "Cédula":
                    coincide_busqueda = any(texto in (cedula or "").lower() for cedula in cedulas)
                else:
                    coincide_busqueda = any(texto in calcular_edad_detallada(fecha).lower() for fecha in personas)

                if coincide_busqueda and (calle_filtro in nombre_calle.lower() if calle_filtro else True) and coincide_edad:
                    filtradas.append(f)

            return filtradas

        def actualizar_tarjetas():
            total_familias = len(resultados_filtrados)
            total_personas = sum(len(f.miembros) + 1 for f in resultados_filtrados)
            edades = [f.fecha_nacimiento_jefe for f in resultados_filtrados] + [
                miembro.fecha_nacimiento for f in resultados_filtrados for miembro in f.miembros
            ]
            total_menores = sum(1 for fecha in edades if _edad_en_meses(fecha) is not None and _edad_en_meses(fecha) < 216)
            total_mayores = sum(1 for fecha in edades if _edad_en_meses(fecha) is not None and _edad_en_meses(fecha) >= 216)

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
                    color=PASTEL_TEXTO_PRI,
                )
            ]
            if familia.miembros:
                personas.append(ft.Divider(color=PASTEL_BORDE))
                personas.append(ft.Text("Carga familiar", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI))
                personas.extend(
                    ft.Text(
                        f"• {miembro.nombres} {miembro.apellidos} | "
                        f"{miembro.parentesco} | ID: {miembro.tipo_id}-{miembro.cedula} | "
                        f"Edad: {calcular_edad_detallada(miembro.fecha_nacimiento)}",
                        color=PASTEL_TEXTO_SEC,
                    )
                    for miembro in familia.miembros
                )
            else:
                personas.append(ft.Text("No tiene carga familiar registrada.", color=PASTEL_TEXTO_SEC))

            dialogo = ft.AlertDialog(
                title=ft.Text(f"Registro de {familia.nombres_jefe} {familia.apellidos_jefe}", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                content=ft.Column(personas, tight=True, scroll=ft.ScrollMode.AUTO),
                actions=[ft.TextButton("Cerrar", on_click=lambda ev: ev.page.close(dialogo))],
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
                if not visibles:
                    tabla.current.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                                ft.DataCell(ft.Text("No se encontraron registros", color=PASTEL_TEXTO_SEC)),
                                ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                                ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                                ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                                ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                            ]
                        )
                    )
                else:
                    for f in visibles:
                        direccion_completa = f"{f.calle.nombre if f.calle else ''} #{f.casa_num or ''}"
                        tabla.current.rows.append(
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(f"{f.nombres_jefe} {f.apellidos_jefe}", size=14, weight=ft.FontWeight.W_500, color=PASTEL_TEXTO_PRI)),
                                    ft.DataCell(ft.Text(f"{f.tipo_id}-{f.cedula_jefe}", size=13, color=PASTEL_TEXTO_PRI)),
                                    ft.DataCell(ft.Text(f.telefono_jefe or "Sin teléfono", size=13, color=PASTEL_TEXTO_SEC)),
                                    ft.DataCell(ft.Text(direccion_completa, size=13, color=PASTEL_TEXTO_PRI)),
                                    ft.DataCell(
                                        ft.Container(
                                            content=ft.Text(f"{len(f.miembros)} personas", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_VERDE),
                                            bgcolor="#E8F5E9",
                                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                            border_radius=10,
                                        )
                                    ),
                                    ft.DataCell(
                                        ft.Row(
                                            [
                                                ft.IconButton(
                                                    icon=ft.Icons.EDIT_OUTLINED,
                                                    icon_color=PASTEL_VERDE,
                                                    tooltip="Editar familia",
                                                    icon_size=20,
                                                    on_click=lambda e, fid=f.id: e.page.go(f"/registro_familia?edit={fid}"),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.REMOVE_RED_EYE_OUTLINED,
                                                    icon_color="#0288D1",
                                                    tooltip="Ver registro",
                                                    icon_size=20,
                                                    on_click=lambda e, familia=f: mostrar_detalle(familia, e),
                                                ),
                                                ft.IconButton(
                                                    icon=ft.Icons.DELETE_OUTLINED,
                                                    icon_color="#E57373",
                                                    tooltip="Eliminar",
                                                    icon_size=20,
                                                    on_click=lambda e, fid=f.id: eliminar_familia(fid, e),
                                                ),
                                            ],
                                            spacing=2,
                                        )
                                    ),
                                ]
                            )
                        )

            if pie_tabla.current:
                pie_tabla.current.controls = [
                    ft.Text(
                        f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} resultados",
                        size=13,
                        color=PASTEL_TEXTO_SEC,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.KEYBOARD_ARROW_LEFT,
                                tooltip="Anterior",
                                icon_color=PASTEL_TEXTO_SEC if pagina_actual.current == 0 else PASTEL_TEXTO_PRI,
                                disabled=pagina_actual.current == 0,
                                on_click=lambda e: cambiar_pagina(pagina_actual.current - 1),
                            ),
                            ft.Text(f"{pagina_actual.current + 1} / {total_paginas}", size=13, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                            ft.IconButton(
                                icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
                                tooltip="Siguiente",
                                icon_color=PASTEL_TEXTO_SEC if pagina_actual.current >= total_paginas - 1 else PASTEL_TEXTO_PRI,
                                disabled=pagina_actual.current >= total_paginas - 1,
                                on_click=lambda e: cambiar_pagina(pagina_actual.current + 1),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
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

        # --- Controles de Filtros ---
        opt_calles = [ft.dropdown.Option("", "Todas las calles")]
        try:
            with SessionLocal() as session:
                calles_db = session.query(Calle).all()
                for c in calles_db:
                    opt_calles.append(ft.dropdown.Option(c.nombre))
        except Exception as err:
            print(f"Error cargando calles: {err}")

        filtro_calle.current = ft.Dropdown(
            label="Filtrar por calle",
            width=220,
            options=opt_calles,
            border_radius=10,
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            bgcolor=PASTEL_CAMPO_BG,
            on_change=lambda e: cambiar_pagina(0),
        )

        filtro_edad.current = ft.Dropdown(
            label="Filtrar por edad",
            width=200,
            options=[
                ft.dropdown.Option("", "Todos los grupos"),
                ft.dropdown.Option("Bebés (0-23 meses)"),
                ft.dropdown.Option("Niños (2-11 años)"),
                ft.dropdown.Option("Adolescentes (12-17 años)"),
                ft.dropdown.Option("Adultos (18-59 años)"),
                ft.dropdown.Option("Adultos mayores (60+)"),
            ],
            border_radius=10,
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            bgcolor=PASTEL_CAMPO_BG,
            on_change=lambda e: cambiar_pagina(0),
        )

        tipo_busqueda.current = ft.Dropdown(
            label="Buscar por",
            width=140,
            value="Nombre",
            options=[
                ft.dropdown.Option("Nombre"),
                ft.dropdown.Option("Cédula"),
                ft.dropdown.Option("Edad"),
            ],
            border_radius=10,
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            bgcolor=PASTEL_CAMPO_BG,
            on_change=lambda e: actualizar_hint_busqueda(),
        )

        buscador.current = ft.TextField(
            hint_text="Escriba un nombre",
            prefix_icon=ft.Icons.SEARCH,
            width=240,
            height=45,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
            border_radius=10,
            border_color=PASTEL_BORDE,
            focused_border_color=PASTEL_VERDE,
            bgcolor=PASTEL_CAMPO_BG,
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

        boton_exportar_excel = ft.IconButton(
            icon=ft.Icons.GRID_ON_ROUNDED,
            tooltip="Exportar Censo a Excel",
            icon_color=PASTEL_VERDE,
            on_click=lambda e: file_picker_exportar_excel.save_file(
                allowed_extensions=["xlsx"], file_name="Censo_Familias.xlsx"
            ),
        )

        boton_exportar_json = ft.IconButton(
            icon=ft.Icons.DATA_OBJECT_ROUNDED,
            tooltip="Exportar Respaldo JSON",
            icon_color=PASTEL_VERDE,
            on_click=lambda e: file_picker_exportar_json.save_file(
                allowed_extensions=["json"], file_name="backup_censo.json"
            ),
        )

        boton_exportar = ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF_ROUNDED,
            tooltip="Exportar datos a PDF",
            icon_color=PASTEL_VERDE,
            on_click=lambda e: file_picker.save_file(
                allowed_extensions=["pdf"], file_name="Reporte_Familias.pdf"
            ),
        )

        tarjeta_filtros = ft.Container(
            content=ft.Row(
                [
                    filtro_calle.current,
                    filtro_edad.current,
                    tipo_busqueda.current,
                    buscador.current,
                    boton_exportar_excel,
                    boton_exportar_json,
                    boton_exportar,
                ],
                spacing=12,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=PASTEL_CARD,
            padding=15,
            border_radius=12,
            border=ft.border.all(1, PASTEL_BORDE),
            shadow=ft.BoxShadow(blur_radius=8, color="#00000008", offset=ft.Offset(0, 3)),
        )

        def crear_kpi_card(titulo_str, icono, color_icono, ref_texto):
            ref_texto.current = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI)
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icono, size=22, color=color_icono),
                        bgcolor="#FFFFFF",
                        padding=10,
                        border_radius=10
                    ),
                    ft.Column([
                        ft.Text(titulo_str, size=12, weight=ft.FontWeight.W_500, color=PASTEL_TEXTO_SEC),
                        ref_texto.current
                    ], spacing=2)
                ], spacing=12),
                bgcolor=PASTEL_CARD,
                padding=12,
                border_radius=12,
                border=ft.border.all(1, PASTEL_BORDE),
                shadow=ft.BoxShadow(blur_radius=6, color="#00000008", offset=ft.Offset(0, 2)),
                expand=True
            )

        resumen = ft.Row(
            [
                crear_kpi_card("Familias Registradas", ft.Icons.HOME_WORK_ROUNDED, PASTEL_VERDE, txt_total_familias),
                crear_kpi_card("Personas en Censo", ft.Icons.GROUPS_ROUNDED, "#0288D1", txt_total_personas),
                crear_kpi_card("Menores de edad (<18)", ft.Icons.CHILD_CARE_ROUNDED, "#F57C00", txt_total_menores),
                crear_kpi_card("Mayores de edad (18+)", ft.Icons.PERSON_ROUNDED, "#7B1FA2", txt_total_mayores),
            ],
            spacing=15,
            wrap=True,
        )

        titulo_row = ft.Row(
            [
                ft.Row([
                    ft.Icon(ft.Icons.FAMILY_RESTROOM_ROUNDED, size=30, color=PASTEL_VERDE),
                    ft.Text("Censo de Familias", size=24, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI)
                ], spacing=10),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Cargar Excel",
                            icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                            height=40,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                side=ft.BorderSide(1, PASTEL_BORDE)
                            ),
                            on_click=lambda _: file_picker_excel.pick_files(
                                allowed_extensions=["xlsx", "xls"],
                                file_type=ft.FilePickerFileType.CUSTOM,
                                dialog_title="Seleccione el archivo de Censo Excel",
                            ),
                        ),
                        ft.OutlinedButton(
                            "Cargar JSON",
                            icon=ft.Icons.FILE_UPLOAD_ROUNDED,
                            height=40,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                side=ft.BorderSide(1, PASTEL_BORDE)
                            ),
                            on_click=lambda _: file_picker_importar_json.pick_files(
                                allowed_extensions=["json"],
                                file_type=ft.FilePickerFileType.CUSTOM,
                                dialog_title="Seleccione el archivo de Respaldo JSON",
                            ),
                        ),
                        ft.ElevatedButton(
                            "Agregar Familia",
                            icon=ft.Icons.ADD_ROUNDED,
                            bgcolor=PASTEL_VERDE,
                            color=COLOR_BLANCO,
                            height=40,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), elevation=2),
                            on_click=lambda e: e.page.go("/registro_familia"),
                        ),
                    ],
                    spacing=10,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        tabla.current = ft.DataTable(
            heading_row_color="#F8FAFC",
            heading_row_height=45,
            data_row_min_height=50,
            divider_thickness=1,
            horizontal_margin=15,
            column_spacing=25,
            columns=[
                ft.DataColumn(ft.Text("LÍDER DE FAMILIA", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
                ft.DataColumn(ft.Text("CÉDULA", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
                ft.DataColumn(ft.Text("TELÉFONO", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
                ft.DataColumn(ft.Text("DIRECCIÓN", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
                ft.DataColumn(ft.Text("CARGA FAMILIAR", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
                ft.DataColumn(ft.Text("ACCIONES", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
            ],
            rows=[],
        )

        pie_tabla.current = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        pie_card = ft.Container(
            content=pie_tabla.current,
            bgcolor=PASTEL_CARD,
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            border_radius=12,
            border=ft.border.all(1, PASTEL_BORDE),
            shadow=ft.BoxShadow(blur_radius=8, color="#00000008", offset=ft.Offset(0, 3)),
        )

        # Contenedor raíz con altura automática y color de fondo sólido, evitando cualquier gris residual
        columna_principal = ft.Container(
            content=ft.Column(
                [
                    titulo_row,
                    resumen,
                    tarjeta_filtros,
                    ft.Container(
                        content=ft.Column([tabla.current], scroll=ft.ScrollMode.AUTO),
                        bgcolor=PASTEL_CARD,
                        padding=10,
                        border_radius=12,
                        border=ft.border.all(1, PASTEL_BORDE),
                        shadow=ft.BoxShadow(blur_radius=8, color="#00000008", offset=ft.Offset(0, 3)),
                    ),
                    pie_card,
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            bgcolor=PASTEL_BG,
            expand=False,
        )

        actualizar_tabla()

        def inicializar():
            actualizar_tabla()

        return {"vista": columna_principal, "actualizar": inicializar}

    except Exception as ex:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color="red", size=48),
                ft.Text("Error al cargar la vista de Familia:", size=16, weight=ft.FontWeight.BOLD, color="red"),
                ft.Text(str(ex), color="black", selectable=True),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            alignment=ft.alignment.center
        )


# --- VISTA REGISTRO Y EDICIÓN DE FAMILIA ---
def vista_registro_familia(pagina=None, edit_id=None):
    try:
        miembros = []

        with SessionLocal() as session:
            calles = session.query(Calle).all()
            familia_edicion = None
            if edit_id is not None:
                familia_edicion = (
                    session.query(Familia)
                    .options(joinedload(Familia.miembros))
                    .filter(Familia.id == edit_id)
                    .first()
                )
            opciones_calles = [ft.dropdown.Option(key=str(c.id), text=c.nombre) for c in calles]

        edad_jefe = ft.TextField(label="Edad", width=90, disabled=True, border_radius=8, bgcolor="#F5F5F5")
        fecha_nacimiento_jefe = ft.TextField(label="Fecha de Nacimiento", width=220, read_only=True, border_radius=8, bgcolor=PASTEL_CAMPO_BG)
        beneficiario = ft.Dropdown(
            label="¿Es beneficiario?",
            width=180,
            value="No",
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
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
            if beneficiario.page:
                beneficiario.update()

        bonos_seleccionados = {
            nombre: ft.Checkbox(label=nombre, value=False, on_change=actualizar_beneficiario)
            for nombre in nombres_bonos
        }
        selector_bonos = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Bonos o beneficios (puede seleccionar varios)", weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Column(list(bonos_seleccionados.values()), spacing=0),
                ],
                spacing=4,
            ),
            border=ft.border.all(1, PASTEL_BORDE),
            border_radius=8,
            padding=12,
            bgcolor=PASTEL_CAMPO_BG,
            width=620,
        )

        tipo_cedula_jefe = ft.Dropdown(
            label="Tipo ID",
            width=100,
            value="V",
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
        )
        cedula_jefe = ft.TextField(
            label="Cédula de Identidad",
            width=180,
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: validar_cedula(e, cedula_jefe),
        )
        telefono_jefe = ft.TextField(
            label="Número de Teléfono",
            width=250,
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: validar_telefono(e, telefono_jefe),
        )

        calle_jefe = ft.Dropdown(label="Calle", width=280, border_radius=8, bgcolor=PASTEL_CAMPO_BG, options=opciones_calles)
        numero_casa_jefe = ft.TextField(label="N° de Casa", width=160, border_radius=8, bgcolor=PASTEL_CAMPO_BG)

        nombres_jefe = ft.TextField(label="Nombres", width=280, border_radius=8, bgcolor=PASTEL_CAMPO_BG)
        apellidos_jefe = ft.TextField(label="Apellidos", width=280, border_radius=8, bgcolor=PASTEL_CAMPO_BG)

        edad_miembro = ft.TextField(label="Edad", width=80, disabled=True, border_radius=8, bgcolor="#F5F5F5")
        fecha_nacimiento_miembro = ft.TextField(label="F. Nacimiento", width=140, read_only=True, border_radius=8, bgcolor=PASTEL_CAMPO_BG)

        tipo_cedula_miembro = ft.Ref[ft.Dropdown]()
        parentesco_miembro = ft.Ref[ft.Dropdown]()

        tipo_cedula_miembro.current = ft.Dropdown(
            label="Tipo ID",
            width=100,
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
        )
        cedula_miembro = ft.TextField(
            label="Cédula",
            width=150,
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: validar_cedula(e, cedula_miembro),
        )
        parentesco_miembro.current = ft.Dropdown(
            label="Parentesco",
            width=150,
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            options=[
                ft.dropdown.Option("Conyuge"),
                ft.dropdown.Option("Hijo/a"),
                ft.dropdown.Option("Nieto/a"),
                ft.dropdown.Option("Otro"),
            ],
        )

        nombres_miembro = ft.TextField(label="Nombres", width=180, border_radius=8, bgcolor=PASTEL_CAMPO_BG)
        apellidos_miembro = ft.TextField(label="Apellidos", width=180, border_radius=8, bgcolor=PASTEL_CAMPO_BG)
        beneficiario_miembro = ft.Dropdown(
            label="Beneficiario",
            width=130,
            value="No",
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            options=[ft.dropdown.Option("Si"), ft.dropdown.Option("No")],
        )
        bonos_miembro = ft.Dropdown(
            label="Bono integrante",
            width=240,
            value="Ninguno",
            border_radius=8,
            bgcolor=PASTEL_CAMPO_BG,
            options=[ft.dropdown.Option("Ninguno")] + [ft.dropdown.Option(nombre) for nombre in nombres_bonos],
        )

        boton_fecha_jefe = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
            icon_color=PASTEL_VERDE,
            on_click=lambda e: abrir_datepicker_fecha_nacimiento(
                e,
                fecha_nacimiento_jefe,
                edad_jefe,
                formato="%d-%m-%Y",
                fecha_minima=datetime.datetime(1900, 1, 1),
            ),
        )

        boton_fecha_miembro = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
            icon_color=PASTEL_VERDE,
            on_click=lambda e: abrir_datepicker_fecha_nacimiento(
                e,
                fecha_nacimiento_miembro,
                edad_miembro,
                formato="%d-%m-%Y",
                fecha_minima=datetime.datetime(1900, 1, 1),
            ),
        )

        encabezados_tabla = ft.Container(
            content=ft.Row(
                [
                    ft.Text("Nombres", width=160, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("Apellidos", width=160, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("Tipo ID", width=90, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("Cédula", width=140, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("F. Nacimiento", width=130, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("Edad", width=80, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("Parentesco", width=130, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Text("Acciones", width=100, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                ],
                spacing=10,
            ),
            padding=ft.padding.only(left=10, right=10, top=10, bottom=5),
        )

        tabla_miembros = ft.Column([], spacing=5)

        def añadir_miembro(e: ft.ControlEvent):
            if not nombres_miembro.value.strip() or not apellidos_miembro.value.strip():
                e.page.open(ft.SnackBar(ft.Text("Por favor completa los campos obligatorios del miembro")))
                return

            cedula_valor = cedula_miembro.value.strip() if cedula_miembro.value.strip() else "No posee"

            for m in miembros:
                if m["cedula"] == cedula_valor and cedula_valor != "No posee":
                    e.page.open(ft.SnackBar(ft.Text(f"⚠️ Ya existe un miembro en la carga con la cédula {cedula_valor}")))
                    return

            if cedula_valor != "No posee":
                with SessionLocal() as session:
                    consulta = session.query(Miembro).filter(Miembro.cedula == cedula_valor)
                    if edit_id is not None:
                        consulta = consulta.filter(Miembro.familia_id != edit_id)
                    if consulta.first():
                        e.page.open(ft.SnackBar(ft.Text(f"⚠️ Ya existe un miembro registrado en la BD con la cédula {cedula_valor}")))
                        return

            miembro_data = {
                "nombres": nombres_miembro.value,
                "apellidos": apellidos_miembro.value,
                "tipo": tipo_cedula_miembro.current.value or "V",
                "cedula": cedula_valor,
                "fecha_nacimiento": fecha_nacimiento_miembro.value,
                "edad": edad_miembro.value,
                "parentesco": parentesco_miembro.current.value or "—",
                "es_beneficiario": beneficiario_miembro.value or "No",
                "bonos": bonos_miembro.value or "Ninguno",
            }

            def editar_miembro(ev, m_data=miembro_data):
                nombres_miembro.value = m_data["nombres"]
                apellidos_miembro.value = m_data["apellidos"]
                tipo_cedula_miembro.current.value = m_data["tipo"]
                cedula_miembro.value = "" if m_data["cedula"] == "No posee" else m_data["cedula"]
                fecha_nacimiento_miembro.value = m_data["fecha_nacimiento"]
                edad_miembro.value = m_data["edad"]
                parentesco_miembro.current.value = m_data["parentesco"] if m_data["parentesco"] != "—" else None
                beneficiario_miembro.value = m_data.get("es_beneficiario", "No")
                bonos_miembro.value = m_data.get("bonos", "Ninguno")
                miembros.remove(m_data)
                tabla_miembros.controls.remove(fila)
                ev.page.update()

            def eliminar_miembro(ev, m_data=miembro_data):
                miembros.remove(m_data)
                tabla_miembros.controls.remove(fila)
                ev.page.update()

            fila = ft.Container(
                content=ft.Row(
                    [
                        ft.Text(miembro_data["nombres"], width=160, color=PASTEL_TEXTO_PRI),
                        ft.Text(miembro_data["apellidos"], width=160, color=PASTEL_TEXTO_PRI),
                        ft.Text(miembro_data["tipo"], width=90, color=PASTEL_TEXTO_SEC),
                        ft.Text(miembro_data["cedula"], width=140, color=PASTEL_TEXTO_PRI),
                        ft.Text(miembro_data["fecha_nacimiento"], width=130, color=PASTEL_TEXTO_SEC),
                        ft.Text(miembro_data["edad"], width=80, color=PASTEL_TEXTO_PRI),
                        ft.Text(miembro_data["parentesco"], width=130, color=PASTEL_TEXTO_PRI),
                        ft.Row(
                            [
                                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=PASTEL_VERDE, tooltip="Editar", on_click=lambda ev: editar_miembro(ev)),
                                ft.IconButton(icon=ft.Icons.DELETE_OUTLINED, icon_color="#E57373", tooltip="Eliminar", on_click=lambda ev: eliminar_miembro(ev)),
                            ],
                            width=100,
                        ),
                    ],
                    spacing=10,
                ),
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                bgcolor=PASTEL_CARD,
                border_radius=8,
                border=ft.border.all(1, PASTEL_BORDE),
            )

            miembros.append(miembro_data)
            tabla_miembros.controls.append(fila)

            nombres_miembro.value = ""
            apellidos_miembro.value = ""
            cedula_miembro.value = ""
            fecha_nacimiento_miembro.value = ""
            edad_miembro.value = ""
            tipo_cedula_miembro.current.value = None
            if tipo_cedula_miembro.current.page:
                tipo_cedula_miembro.current.update()
            parentesco_miembro.current.value = None
            if parentesco_miembro.current.page:
                parentesco_miembro.current.update()
            beneficiario_miembro.value = "No"
            bonos_miembro.value = "Ninguno"
            if beneficiario_miembro.page:
                beneficiario_miembro.update()
            if bonos_miembro.page:
                bonos_miembro.update()

            e.page.update()

        def guardar_familia(e):
            if not nombres_jefe.value.strip() or not apellidos_jefe.value.strip() or not cedula_jefe.value.strip():
                e.page.open(ft.SnackBar(ft.Text("Por favor completa los campos obligatorios del jefe de familia")))
                return

            if not calle_jefe.value:
                e.page.open(ft.SnackBar(ft.Text("Por favor selecciona una calle")))
                return

            if not fecha_nacimiento_jefe.value:
                e.page.open(ft.SnackBar(ft.Text("Por favor selecciona la fecha de nacimiento del jefe de familia")))
                return

            with SessionLocal() as session:
                existente_jefe = session.query(Familia).filter(Familia.cedula_jefe == cedula_jefe.value.strip()).first()
                if existente_jefe and (edit_id is None or existente_jefe.id != edit_id):
                    e.page.open(ft.SnackBar(ft.Text("⚠️ Ya existe una familia registrada con esa cédula")))
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
                    "nombres_jefe": nombres_jefe.value,
                    "apellidos_jefe": apellidos_jefe.value,
                    "tipo_id": tipo_cedula_jefe.value or "V",
                    "cedula_jefe": cedula_jefe.value,
                    "telefono_jefe": telefono_jefe.value,
                    "fecha_nacimiento_jefe": fecha_jefe,
                    "calle_id": int(calle_jefe.value),
                    "casa_num": numero_casa_jefe.value,
                    "es_beneficiario": beneficiario.value or "No",
                    "bono": " | ".join(nombre for nombre, control in bonos_seleccionados.items() if control.value) or "Ninguno",
                }

                if edit_id is not None:
                    nueva_familia = session.query(Familia).filter(Familia.id == edit_id).first()
                    if not nueva_familia:
                        return
                    for clave, valor in datos_familia.items():
                        setattr(nueva_familia, clave, valor)

                    session.query(Miembro).filter(Miembro.familia_id == edit_id).delete()
                    session.commit()
                    id_familia_final = edit_id
                else:
                    nueva_familia = Familia(**datos_familia)
                    session.add(nueva_familia)
                    session.commit()
                    id_familia_final = nueva_familia.id

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
                        familia_id=id_familia_final,
                        nombres=m["nombres"],
                        apellidos=m["apellidos"],
                        tipo_id=m["tipo"] or "V",
                        cedula=m["cedula"],
                        fecha_nacimiento=fecha_m,
                        parentesco=m["parentesco"],
                        es_beneficiario=m.get("es_beneficiario", "No"),
                        bonos=m.get("bonos", "Ninguno"),
                    )
                    session.add(nuevo_miembro)

                session.commit()

            mensaje = "✅ Familia actualizada correctamente" if edit_id else "✅ Familia guardada correctamente"
            e.page.open(ft.SnackBar(ft.Text(mensaje)))
            e.page.go("/familia")

        if familia_edicion:
            nombres_jefe.value = familia_edicion.nombres_jefe or ""
            apellidos_jefe.value = familia_edicion.apellidos_jefe or ""
            tipo_cedula_jefe.value = familia_edicion.tipo_id or "V"
            cedula_jefe.value = familia_edicion.cedula_jefe or ""
            telefono_jefe.value = familia_edicion.telefono_jefe or ""
            calle_jefe.value = str(familia_edicion.calle_id)
            numero_casa_jefe.value = familia_edicion.casa_num or ""
            fecha_nacimiento_jefe.value = (
                familia_edicion.fecha_nacimiento_jefe.strftime("%d-%m-%Y") if familia_edicion.fecha_nacimiento_jefe else ""
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
                miembros.append(miembro_data)
                fila_ref = [None]

                def editar_existente(ev, data=miembro_data, fila_holder=fila_ref):
                    nombres_miembro.value = data["nombres"]
                    apellidos_miembro.value = data["apellidos"]
                    tipo_cedula_miembro.current.value = data["tipo"]
                    cedula_miembro.value = "" if data["cedula"] == "No posee" else data["cedula"]
                    fecha_nacimiento_miembro.value = data["fecha_nacimiento"]
                    edad_miembro.value = data["edad"]
                    parentesco_miembro.current.value = data["parentesco"]
                    beneficiario_miembro.value = data["es_beneficiario"]
                    bonos_miembro.value = data["bonos"]
                    miembros.remove(data)
                    tabla_miembros.controls.remove(fila_holder[0])
                    ev.page.update()

                def eliminar_existente(ev, data=miembro_data, fila_holder=fila_ref):
                    miembros.remove(data)
                    tabla_miembros.controls.remove(fila_holder[0])
                    ev.page.update()

                fila_ref[0] = ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(miembro_data["nombres"], width=160, color=PASTEL_TEXTO_PRI),
                            ft.Text(miembro_data["apellidos"], width=160, color=PASTEL_TEXTO_PRI),
                            ft.Text(miembro_data["tipo"], width=95, color=PASTEL_TEXTO_SEC),
                            ft.Text(miembro_data["cedula"], width=140, color=PASTEL_TEXTO_PRI),
                            ft.Text(miembro_data["fecha_nacimiento"], width=130, color=PASTEL_TEXTO_SEC),
                            ft.Text(miembro_data["edad"], width=80, color=PASTEL_TEXTO_PRI),
                            ft.Text(miembro_data["parentesco"], width=132, color=PASTEL_TEXTO_PRI),
                            ft.Row(
                                [
                                    ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=PASTEL_VERDE, tooltip="Editar", on_click=editar_existente),
                                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINED, icon_color="#E57373", tooltip="Eliminar", on_click=eliminar_existente),
                                ],
                                width=100,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=ft.padding.symmetric(horizontal=13, vertical=5),
                    bgcolor=PASTEL_CARD,
                    border_radius=8,
                    border=ft.border.all(1, PASTEL_BORDE),
                )
                tabla_miembros.controls.append(fila_ref[0])

        boton_añadir = ft.ElevatedButton(
            "Añadir",
            icon=ft.Icons.ADD_ROUNDED,
            bgcolor=PASTEL_VERDE,
            color=COLOR_BLANCO,
            on_click=añadir_miembro,
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )
        boton_guardar = ft.ElevatedButton(
            "Actualizar Familia" if familia_edicion else "Guardar Familia",
            bgcolor=PASTEL_VERDE,
            color=COLOR_BLANCO,
            on_click=guardar_familia,
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )
        boton_cancelar = ft.OutlinedButton(
            "Cancelar",
            on_click=lambda e: e.page.go("/familia"),
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), side=ft.BorderSide(1, PASTEL_BORDE)),
        )

        tarjeta_jefe = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Datos del Jefe de Familia", size=18, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Divider(height=15, color=PASTEL_BORDE),
                    ft.Row([nombres_jefe, apellidos_jefe], wrap=True, spacing=15),
                    ft.Row([tipo_cedula_jefe, cedula_jefe, telefono_jefe], wrap=True, spacing=15),
                    ft.Row([calle_jefe, numero_casa_jefe], wrap=True, spacing=15),
                    ft.Row([fecha_nacimiento_jefe, boton_fecha_jefe, edad_jefe], wrap=True, spacing=10),
                    ft.Row([beneficiario], wrap=True, spacing=15),
                    selector_bonos,
                ],
                spacing=15,
            ),
            padding=20,
            bgcolor=PASTEL_CARD,
            border_radius=12,
            border=ft.border.all(1, PASTEL_BORDE),
            shadow=ft.BoxShadow(blur_radius=8, color="#00000008", offset=ft.Offset(0, 3)),
        )

        tarjeta_carga = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Carga Familiar (Miembros)", size=18, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_PRI),
                    ft.Divider(height=15, color=PASTEL_BORDE),
                    ft.Row(
                        [
                            nombres_miembro,
                            apellidos_miembro,
                            tipo_cedula_miembro.current,
                            cedula_miembro,
                            fecha_nacimiento_miembro,
                            boton_fecha_miembro,
                            edad_miembro,
                        ],
                        wrap=True,
                        spacing=15,
                    ),
                    ft.Row(
                        [
                            parentesco_miembro.current,
                            beneficiario_miembro,
                            bonos_miembro,
                            boton_añadir,
                        ],
                        wrap=True,
                        spacing=20,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Container(height=10),
                    encabezados_tabla,
                    ft.Container(
                        content=tabla_miembros,
                        padding=10,
                        bgcolor=PASTEL_CAMPO_BG,
                        border_radius=8,
                        border=ft.border.all(1, PASTEL_BORDE),
                    ),
                ],
                spacing=10,
            ),
            padding=20,
            bgcolor=PASTEL_CARD,
            border_radius=12,
            border=ft.border.all(1, PASTEL_BORDE),
            shadow=ft.BoxShadow(blur_radius=8, color="#00000008", offset=ft.Offset(0, 3)),
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Editar Familia" if familia_edicion else "Registro de Nueva Familia",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=PASTEL_TEXTO_PRI,
                    ),
                    ft.Text(
                        "Modifique los datos y la carga familiar."
                        if familia_edicion
                        else "Complete los datos para registrar una nueva familia en el sistema.",
                        size=13,
                        color=PASTEL_TEXTO_SEC,
                    ),
                    ft.Divider(height=15, color=PASTEL_BORDE),
                    tarjeta_jefe,
                    ft.Container(height=10),
                    tarjeta_carga,
                    ft.Container(height=10),
                    ft.Row(
                        [boton_cancelar, boton_guardar],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=15,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=25,
            bgcolor=PASTEL_BG,
            expand=False,
        )

    except Exception as ex:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color="red", size=48),
                ft.Text("Error al cargar la vista de Registro de Familia:", size=16, weight=ft.FontWeight.BOLD, color="red"),
                ft.Text(str(ex), color="black", selectable=True),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30,
            alignment=ft.alignment.center
        )