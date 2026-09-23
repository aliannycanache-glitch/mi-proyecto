import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
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
from sqlalchemy.orm import joinedload
from utiles import (
    abrir_datepicker_fecha_nacimiento,
    validar_cedula,
    validar_telefono,
)


def vista_familia(pagina: ft.Page):
    registros_por_pagina = 5
    pagina_actual = ft.Ref[int]()
    pagina_actual.current = 0

    buscador = ft.Ref[ft.TextField]()
    filtro_calle = ft.Ref[ft.Dropdown]()
    tabla = ft.Ref[ft.DataTable]()
    pie_tabla = ft.Ref[ft.Row]()
    tarjeta_familias = ft.Ref[ft.Container]()
    tarjeta_personas = ft.Ref[ft.Container]()
    resultados_filtrados = []

    # 📊 FilePicker para Exportar a Excel
    def guardar_excel_seleccionado(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path if e.path.endswith(".xlsx") else f"{e.path}.xlsx"
            exito = exportar_censo_a_excel(ruta)

            mensaje = (
                f"Censo exportado con éxito a:\n{ruta}"
                if exito
                else "Ocurrió un error al exportar."
            )
            dlg = ft.AlertDialog(
                title=ft.Text("Exportación Excel"),
                content=ft.Text(mensaje),
                actions=[
                    ft.TextButton(
                        "Aceptar", on_click=lambda ev: e.page.close_dialog()
                    )
                ],
            )
            e.page.dialog = dlg
            dlg.open = True
            e.page.update()

    file_picker_exportar_excel = ft.FilePicker(
        on_result=guardar_excel_seleccionado
    )
    pagina.overlay.append(file_picker_exportar_excel)

    # 🗄️ FilePicker para Exportar Respaldo JSON
    def guardar_json_seleccionado(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path if e.path.endswith(".json") else f"{e.path}.json"
            exito = exportar_backup_json(ruta)

            mensaje = (
                f"Respaldo JSON guardado con éxito en:\n{ruta}"
                if exito
                else "Ocurrió un error al exportar."
            )
            dlg = ft.AlertDialog(
                title=ft.Text("Respaldo JSON"),
                content=ft.Text(mensaje),
                actions=[
                    ft.TextButton(
                        "Aceptar", on_click=lambda ev: e.page.close_dialog()
                    )
                ],
            )
            e.page.dialog = dlg
            dlg.open = True
            e.page.update()

    file_picker_exportar_json = ft.FilePicker(
        on_result=guardar_json_seleccionado
    )
    pagina.overlay.append(file_picker_exportar_json)

    # 📄 FilePicker para Exportar PDF
    file_picker = ft.FilePicker(on_result=lambda e: exportar_pdf(e))
    pagina.overlay.append(file_picker)

    # 📥 FilePicker para Importar Excel
    def procesar_excel_seleccionado(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            ruta_excel = e.files[0].path
            exito = importar_censo_desde_excel(ruta_excel)

            actualizar_tabla()

            mensaje = (
                "El archivo Excel ha sido procesado con éxito en la base de datos."
                if exito
                else "Ocurrió un error al importar el archivo Excel."
            )
            dlg = ft.AlertDialog(
                title=ft.Text("Importación Excel"),
                content=ft.Text(mensaje),
                actions=[
                    ft.TextButton(
                        "Aceptar", on_click=lambda ev: e.page.close_dialog()
                    )
                ],
            )
            e.page.dialog = dlg
            dlg.open = True
            e.page.update()

    file_picker_excel = ft.FilePicker(on_result=procesar_excel_seleccionado)
    pagina.overlay.append(file_picker_excel)

    # 📥 FilePicker para Importar JSON
    def procesar_json_seleccionado(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            ruta_json = e.files[0].path
            exito = importar_backup_json(ruta_json)

            actualizar_tabla()

            mensaje = (
                "El respaldo JSON ha sido procesado con éxito en la base de datos."
                if exito
                else "Ocurrió un error al importar el archivo JSON."
            )
            dlg = ft.AlertDialog(
                title=ft.Text("Importación JSON"),
                content=ft.Text(mensaje),
                actions=[
                    ft.TextButton(
                        "Aceptar", on_click=lambda ev: e.page.close_dialog()
                    )
                ],
            )
            e.page.dialog = dlg
            dlg.open = True
            e.page.update()

    file_picker_importar_json = ft.FilePicker(
        on_result=procesar_json_seleccionado
    )
    pagina.overlay.append(file_picker_importar_json)

    # ✅ Eliminar familia desde BD
    def eliminar_familia(fid, e):
        session = SessionLocal()
        familia = session.query(Familia).filter(Familia.id == fid).first()
        if familia:
            session.delete(familia)
            session.commit()
        session.close()
        actualizar_tabla()
        e.page.update()

    # ✅ Filtrar datos desde BD (Carga explícita de Calle y Miembros)
    def filtrar_datos():
        session = SessionLocal()
        familias = (
            session.query(Familia)
            .options(
                joinedload(Familia.miembros), joinedload(Familia.calle)
            )
            .all()
        )
        session.close()

        texto = (
            buscador.current.value.lower().strip()
            if buscador.current.value
            else ""
        )
        calle_filtro = (
            filtro_calle.current.value.lower().strip()
            if filtro_calle.current.value and filtro_calle.current.value != ""
            else None
        )

        filtradas = []
        for f in familias:
            nombres = f.nombres_jefe.lower() if f.nombres_jefe else ""
            apellidos = f.apellidos_jefe.lower() if f.apellidos_jefe else ""
            cedula = f.cedula_jefe.lower() if f.cedula_jefe else ""

            nombre_calle = f.calle.nombre if f.calle else ""

            if (texto in nombres or texto in apellidos or texto in cedula) and (
                calle_filtro in nombre_calle.lower() if calle_filtro else True
            ):
                filtradas.append(f)
        return filtradas

    def actualizar_tarjetas():
        total_familias = len(resultados_filtrados)
        total_personas = sum(
            len(f.miembros) + 1 for f in resultados_filtrados
        )

        tarjeta_familias.current.content.controls[1].value = str(
            total_familias
        )
        tarjeta_personas.current.content.controls[1].value = str(
            total_personas
        )

        tarjeta_familias.current.update()
        tarjeta_personas.current.update()

    def actualizar_tabla():
        nonlocal resultados_filtrados
        resultados_filtrados = filtrar_datos()
        total_paginas = (
            len(resultados_filtrados) + registros_por_pagina - 1
        ) // registros_por_pagina
        pagina_actual.current = min(
            pagina_actual.current, max(total_paginas - 1, 0)
        )

        inicio = pagina_actual.current * registros_por_pagina
        fin = inicio + registros_por_pagina
        visibles = resultados_filtrados[inicio:fin]

        tabla.current.rows.clear()
        for f in visibles:
            direccion_completa = (
                f"{f.calle.nombre if f.calle else ''} #{f.casa_num or ''}"
            )
            tabla.current.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Container(
                                ft.Text(
                                    f"{f.nombres_jefe} {f.apellidos_jefe}"
                                ),
                                width=200,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                ft.Text(f"{f.tipo_id}-{f.cedula_jefe}"),
                                width=140,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                ft.Text(f.telefono_jefe or ""), width=140
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                ft.Text(direccion_completa), width=280
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                ft.Text(f"{len(f.miembros)} personas"),
                                width=120,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_color=COLOR_ROJO,
                                            tooltip="Eliminar",
                                            on_click=lambda e, fid=f.id: eliminar_familia(
                                                fid, e
                                            ),
                                        ),
                                    ],
                                    spacing=5,
                                ),
                                width=70,
                            )
                        ),
                    ]
                )
            )

        pie_tabla.current.controls = [
            ft.Text(
                f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} resultados",
                color=COLOR_GRIS,
            ),
            ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_LEFT,
                        tooltip="Anterior",
                        icon_color=(
                            COLOR_GRIS
                            if pagina_actual.current == 0
                            else COLOR_NEGRO
                        ),
                        disabled=pagina_actual.current == 0,
                        on_click=lambda e: cambiar_pagina(
                            pagina_actual.current - 1
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
                        tooltip="Siguiente",
                        icon_color=(
                            COLOR_GRIS
                            if pagina_actual.current >= total_paginas - 1
                            else COLOR_NEGRO
                        ),
                        disabled=pagina_actual.current >= total_paginas - 1,
                        on_click=lambda e: cambiar_pagina(
                            pagina_actual.current + 1
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ]

        actualizar_tarjetas()

        if tabla.current.page:
            tabla.current.update()
        if pie_tabla.current.page:
            pie_tabla.current.update()

    def cambiar_pagina(nueva_pagina):
        pagina_actual.current = nueva_pagina
        actualizar_tabla()

    session = SessionLocal()
    calles = session.query(Calle).all()
    session.close()

    filtro_calle.current = ft.Dropdown(
        label="Filtrar por calle",
        width=300,
        options=[ft.dropdown.Option("")]
        + [ft.dropdown.Option(c.nombre) for c in calles],
        on_change=lambda e: cambiar_pagina(0),
    )

    buscador.current = ft.TextField(
        hint_text="Buscar por nombre o cédula",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        on_change=lambda e: cambiar_pagina(0),
    )

    # 🟢 Botón para activar el FilePicker de exportación a Excel
    boton_exportar_excel = ft.IconButton(
        icon=ft.Icons.GRID_ON,
        tooltip="Exportar Censo a Excel",
        icon_color=COLOR_VERDE,
        on_click=lambda e: file_picker_exportar_excel.save_file(
            allowed_extensions=["xlsx"], file_name="Censo_Familias.xlsx"
        ),
    )

    # 🟡 Botón para activar el FilePicker de respaldo JSON
    boton_exportar_json = ft.IconButton(
        icon=ft.Icons.DATA_OBJECT,
        tooltip="Exportar Respaldo JSON",
        icon_color=COLOR_VERDE,
        on_click=lambda e: file_picker_exportar_json.save_file(
            allowed_extensions=["json"], file_name="backup_censo.json"
        ),
    )

    # 🔴 Botón para activar el FilePicker de exportación a PDF
    boton_exportar = ft.IconButton(
        icon=ft.Icons.PICTURE_AS_PDF,
        tooltip="Exportar datos a PDF",
        icon_color=COLOR_VERDE,
        on_click=lambda e: file_picker.save_file(),
    )

    # 📌 Contenedor de filtros con los tres botones de exportación integrados
    tarjeta_filtros = ft.Container(
        content=ft.Row(
            [
                filtro_calle.current,
                buscador.current,
                boton_exportar_excel,
                boton_exportar_json,
                boton_exportar,
            ],
            spacing=15,
        ),
        bgcolor="#ffffff66",
        padding=20,
        border_radius=10,
        width=840,
        alignment=ft.alignment.center_left,
    )

    tarjeta_familias.current = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Familias Registradas",
                    size=14,
                    color=COLOR_GRIS,
                    weight="bold",
                ),
                ft.Text("0", size=22, weight="bold", color=COLOR_NEGRO),
            ]
        ),
        bgcolor=COLOR_BLANCO,
        padding=20,
        border_radius=10,
        width=250,
    )

    tarjeta_personas.current = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Personas en Censo",
                    size=14,
                    color=COLOR_GRIS,
                    weight="bold",
                ),
                ft.Text("0", size=22, weight="bold", color=COLOR_NEGRO),
            ]
        ),
        bgcolor=COLOR_BLANCO,
        padding=20,
        border_radius=10,
        width=250,
    )

    resumen = ft.Row(
        [tarjeta_familias.current, tarjeta_personas.current], spacing=20
    )

    # 📌 ENCABEZADO: Botones principales (Incluye Cargar Censo Excel y Cargar Respaldo JSON)
    encabezado = ft.Row(
        [
            ft.Text(
                "Censo de Familias", size=26, weight="bold", color=COLOR_NEGRO
            ),
            ft.Row(
                [
                    ft.OutlinedButton(
                        "Cargar Excel",
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda _: file_picker_excel.pick_files(
                            allowed_extensions=["xlsx", "xls"],
                            file_type=ft.FilePickerFileType.CUSTOM,
                            dialog_title="Seleccione el archivo de Censo Excel",
                        ),
                    ),
                    ft.OutlinedButton(
                        "Cargar JSON",
                        icon=ft.Icons.FILE_UPLOAD,
                        on_click=lambda _: file_picker_importar_json.pick_files(
                            allowed_extensions=["json"],
                            file_type=ft.FilePickerFileType.CUSTOM,
                            dialog_title="Seleccione el archivo de Respaldo JSON",
                        ),
                    ),
                    ft.ElevatedButton(
                        "+ Agregar Familia",
                        bgcolor=COLOR_VERDE,
                        color=COLOR_BLANCO,
                        on_click=lambda e: e.page.go("/registro_familia"),
                    ),
                ],
                spacing=10,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    tabla.current = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("LÍDER DE FAMILIA")),
            ft.DataColumn(ft.Text("CÉDULA")),
            ft.DataColumn(ft.Text("TELÉFONO")),
            ft.DataColumn(ft.Text("DIRECCIÓN")),
            ft.DataColumn(ft.Text("CARGA FAMILIAR")),
            ft.DataColumn(ft.Text("ACCIONES")),
        ],
        rows=[],
    )

    pie_tabla.current = ft.Row(
        [], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    pie_card = ft.Container(
        content=pie_tabla.current,
        bgcolor=COLOR_BLANCO,
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        border_radius=10,
        border=ft.border.all(1, COLOR_GRIS),
        width=1400,
    )

    columna = ft.Column(
        controls=[
            encabezado,
            resumen,
            tarjeta_filtros,
            ft.Divider(),
            ft.Container(
                content=tabla.current,
                bgcolor="#ffffff66",
                padding=20,
                border_radius=10,
                border=ft.border.all(1, COLOR_GRIS),
                width=1400,
                expand=True,
            ),
            pie_card,
        ],
        spacing=20,
        scroll="auto",
        expand=True,
    )

    def inicializar():
        actualizar_tabla()

    return {"vista": columna, "actualizar": inicializar}


def exportar_pdf(e: ft.FilePickerUploadEvent):
    if not e.path:
        return

    archivo = e.path
    if not archivo.lower().endswith(".pdf"):
        archivo += ".pdf"

    # Consultar BD
    session = SessionLocal()
    familias = (
        session.query(Familia)
        .options(joinedload(Familia.miembros), joinedload(Familia.calle))
        .all()
    )
    session.close()

    # Generar el PDF llamando al módulo independiente
    generar_pdf_familias(familias, archivo)

    # Notificación Flet
    dlg = ft.AlertDialog(
        title=ft.Text("Exportación completada"),
        content=ft.Text(f"El reporte PDF fue guardado en:\n{archivo}"),
        actions=[
            ft.TextButton(
                "Cerrar", on_click=lambda ev: e.page.dialog.close()
            )
        ],
    )
    e.page.dialog = dlg
    dlg.open = True
    e.page.update()


def vista_registro_familia():
    miembros = []

    session = SessionLocal()
    calles = session.query(Calle).all()
    session.close()

    # Mapear objeto Calle a Dropdown usando su ID como key/key_data
    opciones_calles = [
        ft.dropdown.Option(key=str(c.id), text=c.nombre) for c in calles
    ]

    edad_jefe = ft.TextField(label="Edad", width=100, disabled=True)
    fecha_nacimiento_jefe = ft.TextField(
        label="Fecha de Nacimiento", width=280, read_only=True
    )
    beneficiario = ft.Dropdown(
        label="¿Es beneficiario?",
        width=180,
        value="No",
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
        nombre: ft.Checkbox(label=nombre, value=False, on_change=actualizar_beneficiario)
        for nombre in nombres_bonos
    }
    selector_bonos = ft.Container(
        content=ft.Column(
            [
                ft.Text("Bonos o beneficios (puede seleccionar varios)", weight="bold"),
                ft.Column(list(bonos_seleccionados.values()), spacing=0),
            ],
            spacing=4,
        ),
        border=ft.border.all(1, COLOR_GRIS),
        border_radius=8,
        padding=10,
        width=620,
    )

    tipo_cedula_jefe = ft.Dropdown(
        label="Tipo de ID",
        width=120,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula_jefe = ft.TextField(
        label="Cédula de Identidad",
        width=180,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: validar_cedula(e, cedula_jefe),
    )
    telefono_jefe = ft.TextField(
        label="Número de Teléfono",
        width=320,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: validar_telefono(e, telefono_jefe),
    )

    calle_jefe = ft.Dropdown(label="Calle", width=320, options=opciones_calles)
    numero_casa_jefe = ft.TextField(label="N° de Casa", width=200)

    nombres_jefe = ft.TextField(label="Nombres", width=320)
    apellidos_jefe = ft.TextField(label="Apellidos", width=320)

    # Campos del miembro
    edad_miembro = ft.TextField(label="Edad", width=100, disabled=True)
    fecha_nacimiento_miembro = ft.TextField(
        label="F. Nacimiento", width=160, read_only=True
    )

    tipo_cedula_miembro = ft.Ref[ft.Dropdown]()
    parentesco_miembro = ft.Ref[ft.Dropdown]()

    tipo_cedula_miembro.current = ft.Dropdown(
        label="Tipo de ID",
        width=120,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula_miembro = ft.TextField(
        label="Cédula",
        width=170,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: validar_cedula(e, cedula_miembro),
    )
    parentesco_miembro.current = ft.Dropdown(
        label="Parentesco",
        width=160,
        options=[
            ft.dropdown.Option("Seleccione"),
            ft.dropdown.Option("Conyuge"),
            ft.dropdown.Option("Hijo/a"),
            ft.dropdown.Option("Nieto/a"),
            ft.dropdown.Option("Otro"),
        ],
    )

    nombres_miembro = ft.TextField(label="Nombres", width=160)
    apellidos_miembro = ft.TextField(label="Apellidos", width=160)
    beneficiario_miembro = ft.Dropdown(
        label="Beneficiario",
        width=130,
        value="No",
        options=[ft.dropdown.Option("Si"), ft.dropdown.Option("No")],
    )
    bonos_miembro = ft.Dropdown(
        label="Bono del integrante",
        width=240,
        value="Ninguno",
        options=[ft.dropdown.Option("Ninguno")] + [ft.dropdown.Option(nombre) for nombre in nombres_bonos],
    )

    boton_fecha_jefe = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        icon_color=COLOR_VERDE,
        on_click=lambda e: abrir_datepicker_fecha_nacimiento(
            e,
            fecha_nacimiento_jefe,
            edad_jefe,
            formato="%d-%m-%Y",
            fecha_minima=datetime.datetime(1900, 1, 1),
        ),
    )
    boton_fecha_miembro = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        icon_color=COLOR_VERDE,
        on_click=lambda e: abrir_datepicker_fecha_nacimiento(
            e,
            fecha_nacimiento_miembro,
            edad_miembro,
            formato="%d-%m-%Y",
            fecha_minima=datetime.datetime(1900, 1, 1),
        ),
    )

    encabezados_tabla = ft.Row(
        [
            ft.Text("Nombres", width=160, weight="bold"),
            ft.Text("Apellidos", width=160, weight="bold"),
            ft.Text("Tipo de ID", width=120, weight="bold"),
            ft.Text("Cédula", width=170, weight="bold"),
            ft.Text("F. Nacimiento", width=160, weight="bold"),
            ft.Text("Edad", width=100, weight="bold"),
            ft.Text("Parentesco", width=160, weight="bold"),
        ],
        spacing=10,
    )
    tabla_miembros = ft.Column([])

    def añadir_miembro(e: ft.ControlEvent):
        if (
            not nombres_miembro.value.strip()
            or not apellidos_miembro.value.strip()
        ):
            snackbar = ft.SnackBar(
                ft.Text("Por favor completa los campos obligatorios")
            )
            e.page.overlay.append(snackbar)
            snackbar.open = True
            e.page.update()
            return

        cedula_valor = (
            cedula_miembro.value.strip()
            if cedula_miembro.value.strip()
            else "No posee"
        )

        for m in miembros:
            if m["cedula"] == cedula_valor and cedula_valor != "No posee":
                snackbar = ft.SnackBar(
                    ft.Text(
                        f"⚠️ Ya existe un miembro en la carga con la cédula {cedula_valor}"
                    )
                )
                e.page.overlay.append(snackbar)
                snackbar.open = True
                e.page.update()
                return

        session = SessionLocal()
        if cedula_valor != "No posee":
            existente_miembro = (
                session.query(Miembro)
                .filter(Miembro.cedula == cedula_valor)
                .first()
            )
            if existente_miembro:
                snackbar = ft.SnackBar(
                    ft.Text(
                        f"⚠️ Ya existe un miembro registrado en la BD con la cédula {cedula_valor}"
                    )
                )
                e.page.overlay.append(snackbar)
                snackbar.open = True
                e.page.update()
                session.close()
                return
        session.close()

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

        def editar_miembro(ev, miembro):
            nombres_miembro.value = miembro["nombres"]
            apellidos_miembro.value = miembro["apellidos"]
            tipo_cedula_miembro.current.value = miembro["tipo"]
            cedula_miembro.value = (
                "" if miembro["cedula"] == "No posee" else miembro["cedula"]
            )
            fecha_nacimiento_miembro.value = miembro["fecha_nacimiento"]
            edad_miembro.value = miembro["edad"]
            parentesco_miembro.current.value = (
                miembro["parentesco"] if miembro["parentesco"] != "—" else None
            )
            beneficiario_miembro.value = miembro.get("es_beneficiario", "No")
            bonos_miembro.value = miembro.get("bonos", "Ninguno")
            e.page.update()
            miembros.remove(miembro)
            tabla_miembros.controls.remove(fila)
            e.page.update()

        def eliminar_miembro(ev, miembro):
            miembros.remove(miembro)
            tabla_miembros.controls.remove(fila)
            e.page.update()

        fila = ft.Row(
            [
                ft.Text(miembro_data["nombres"], width=160),
                ft.Text(miembro_data["apellidos"], width=160),
                ft.Text(miembro_data["tipo"], width=120),
                ft.Text(miembro_data["cedula"], width=170),
                ft.Text(miembro_data["fecha_nacimiento"], width=160),
                ft.Text(miembro_data["edad"], width=100),
                ft.Text(miembro_data["parentesco"], width=160),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=COLOR_VERDE,
                        tooltip="Editar",
                        on_click=lambda ev, m=miembro_data: editar_miembro(
                            ev, m
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=COLOR_ROJO,
                        tooltip="Eliminar",
                        on_click=lambda ev, m=miembro_data: eliminar_miembro(
                            ev, m
                        ),
                    ),
                ]),
            ],
            spacing=10,
        )

        miembros.append(miembro_data)
        tabla_miembros.controls.append(fila)

        nombres_miembro.value = ""
        apellidos_miembro.value = ""
        cedula_miembro.value = ""
        fecha_nacimiento_miembro.value = ""
        edad_miembro.value = ""

        tipo_cedula_miembro.current.value = None
        tipo_cedula_miembro.current.update()

        parentesco_miembro.current.value = None
        parentesco_miembro.current.update()
        beneficiario_miembro.value = "No"
        bonos_miembro.value = "Ninguno"
        beneficiario_miembro.update()
        bonos_miembro.update()

        e.page.update()

    def guardar_familia(e):
        if (
            not nombres_jefe.value.strip()
            or not apellidos_jefe.value.strip()
            or not cedula_jefe.value.strip()
        ):
            snackbar = ft.SnackBar(
                ft.Text(
                    "Por favor completa los campos obligatorios del jefe de familia"
                )
            )
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

        if not fecha_nacimiento_jefe.value:
            snackbar = ft.SnackBar(ft.Text("Por favor selecciona la fecha de nacimiento del jefe de familia"))
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
        if existente_jefe:
            snackbar = ft.SnackBar(
                ft.Text("⚠️ Ya existe una familia registrada con esa cédula")
            )
            e.page.overlay.append(snackbar)
            snackbar.open = True
            e.page.update()
            session.close()
            return

        fecha_jefe = None
        if fecha_nacimiento_jefe.value:
            try:
                try:
                    fecha_jefe = datetime.datetime.strptime(
                        fecha_nacimiento_jefe.value, "%d-%m-%Y"
                    ).date()
                except ValueError:
                    fecha_jefe = datetime.datetime.strptime(
                        fecha_nacimiento_jefe.value, "%Y-%m-%d"
                    ).date()
            except Exception:
                fecha_jefe = None

        nueva_familia = Familia(
            nombres_jefe=nombres_jefe.value,
            apellidos_jefe=apellidos_jefe.value,
            tipo_id=tipo_cedula_jefe.value or "V",
            cedula_jefe=cedula_jefe.value,
            telefono_jefe=telefono_jefe.value,
            fecha_nacimiento_jefe=fecha_jefe,
            calle_id=int(calle_jefe.value),
            casa_num=numero_casa_jefe.value,
            es_beneficiario=beneficiario.value or "No",
            bono=" | ".join(
                nombre for nombre, control in bonos_seleccionados.items()
                if control.value
            ) or "Ninguno",
        )

        for m in miembros:
            fecha_m = None
            if m["fecha_nacimiento"]:
                try:
                    try:
                        fecha_m = datetime.datetime.strptime(
                            m["fecha_nacimiento"], "%d-%m-%Y"
                        ).date()
                    except ValueError:
                        fecha_m = datetime.datetime.strptime(
                            m["fecha_nacimiento"], "%Y-%m-%d"
                        ).date()
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

        session.add(nueva_familia)
        session.commit()
        session.close()

        snackbar = ft.SnackBar(ft.Text("✅ Familia guardada correctamente"))
        e.page.overlay.append(snackbar)
        snackbar.open = True
        e.page.update()

        e.page.go("/familia")

    boton_añadir = ft.ElevatedButton(
        "Añadir",
        icon=ft.Icons.ADD,
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        on_click=añadir_miembro,
    )
    boton_guardar = ft.ElevatedButton(
        "Guardar Familia",
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        on_click=guardar_familia,
    )
    boton_cancelar = ft.TextButton(
        "Cancelar", on_click=lambda e: e.page.go("/familia")
    )

    return ft.Container(
        content=ft.Column([
            ft.Text(
                "Registro de Nueva Familia",
                size=26,
                weight="bold",
                color=COLOR_NEGRO,
            ),
            ft.Text(
                "Complete los datos para registrar una nueva familia en el sistema.",
                size=14,
                color=COLOR_GRIS,
            ),
            ft.Divider(),
            ft.Text(
                "Datos del Jefe de Familia",
                size=18,
                weight="bold",
                color=COLOR_NEGRO,
            ),
            ft.Row([nombres_jefe, apellidos_jefe], spacing=20),
            ft.Row([tipo_cedula_jefe, cedula_jefe, telefono_jefe], spacing=20),
            ft.Row([calle_jefe, numero_casa_jefe], spacing=20),
            ft.Row(
                [fecha_nacimiento_jefe, boton_fecha_jefe, edad_jefe],
                spacing=10,
            ),
            ft.Row([beneficiario], spacing=20),
            selector_bonos,
            ft.Divider(),
            ft.Text(
                "Carga Familiar (Miembros)",
                size=18,
                weight="bold",
                color=COLOR_NEGRO,
            ),
            ft.Row(
                [
                    nombres_miembro,
                    apellidos_miembro,
                    tipo_cedula_miembro.current,
                    cedula_miembro,
                    fecha_nacimiento_miembro,
                    boton_fecha_miembro,
                    edad_miembro,
                    parentesco_miembro.current,
                    beneficiario_miembro,
                    bonos_miembro,
                    boton_añadir,
                ],
                spacing=10,
            ),
            ft.Container(height=10),
            encabezados_tabla,
            tabla_miembros,
            ft.Container(height=20),
            ft.Row(
                [boton_cancelar, boton_guardar],
                alignment=ft.MainAxisAlignment.END,
                spacing=20,
            ),
        ]),
        bgcolor=COLOR_BLANCO,
        padding=30,
        border_radius=12,
        expand=True,
    )