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
    abrir_datepicker_solo_fecha,
    calcular_edad_detallada,
    validar_cedula,
    validar_telefono,
)


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


def vista_familia(pagina: ft.Page):
    registros_por_pagina = 5
    pagina_actual = ft.Ref[int]()
    pagina_actual.current = 0

    buscador = ft.Ref[ft.TextField]()
    filtro_calle = ft.Ref[ft.Dropdown]()
    tipo_busqueda = ft.Ref[ft.Dropdown]()
    tabla = ft.Ref[ft.DataTable]()
    pie_tabla = ft.Ref[ft.Row]()
    tarjeta_familias = ft.Ref[ft.Container]()
    tarjeta_personas = ft.Ref[ft.Container]()
    tarjeta_menores = ft.Ref[ft.Container]()
    tarjeta_mayores = ft.Ref[ft.Container]()
    resultados_filtrados = []

    # FilePicker para Exportar a Excel
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

    # FilePicker para Exportar Respaldo JSON
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

    # FilePicker para Exportar PDF
# FilePicker para Exportar PDF
    def exportar_pdf(e: ft.FilePickerResultEvent):
        if e.path:
            ruta = e.path if e.path.endswith(".pdf") else f"{e.path}.pdf"
            exito = generar_pdf_familias(resultados_filtrados, ruta)

            mensaje = (
                f"PDF generado con éxito en:\n{ruta}"
                if exito
                else "Ocurrió un error al generar el PDF."
            )
            dlg = ft.AlertDialog(
                title=ft.Text("Exportación PDF"),
                content=ft.Text(mensaje),
                actions=[
                    ft.TextButton(
                        "Aceptar", on_click=lambda ev: ev.page.close(dlg)
                    )
                ],
            )
            e.page.open(dlg)
        
    file_picker = ft.FilePicker(on_result=lambda e: exportar_pdf(e))
    pagina.overlay.append(file_picker)

    # FilePicker para Importar Excel
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

    # FilePicker para Importar JSON
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

    #  Eliminar familia desde BD
    def eliminar_familia(fid, e):
        session = SessionLocal()
        familia = session.query(Familia).filter(Familia.id == fid).first()
        if familia:
            session.delete(familia)
            session.commit()
        session.close()
        actualizar_tabla()
        e.page.update()

    #  Filtrar datos desde BD (Carga explícita de Calle y Miembros)
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
        edad_filtro = filtro_edad.current.value if filtro_edad.current else None
        campo_busqueda = tipo_busqueda.current.value or "Nombre"

        filtradas = []
        for f in familias:
            nombre_calle = f.calle.nombre if f.calle else ""
            personas = [f.fecha_nacimiento_jefe] + [m.fecha_nacimiento for m in f.miembros]
            nombres = [
                f"{f.nombres_jefe} {f.apellidos_jefe}".lower()
            ] + [f"{m.nombres} {m.apellidos}".lower() for m in f.miembros]
            cedulas = [f.cedula_jefe] + [m.cedula for m in f.miembros]
            coincide_edad = (
                not edad_filtro
                or any(_persona_esta_en_rango(fecha, edad_filtro) for fecha in personas)
            )
            if not texto:
                coincide_busqueda = True
            elif campo_busqueda == "Nombre":
                coincide_busqueda = any(texto in nombre for nombre in nombres)
            elif campo_busqueda == "Cédula":
                coincide_busqueda = any(texto in (cedula or "").lower() for cedula in cedulas)
            else:
                coincide_busqueda = any(
                    texto in calcular_edad_detallada(fecha).lower()
                    for fecha in personas
                )

            if coincide_busqueda and (
                calle_filtro in nombre_calle.lower() if calle_filtro else True
            ) and coincide_edad:
                filtradas.append(f)
        return filtradas

    def actualizar_tarjetas():
        total_familias = len(resultados_filtrados)
        total_personas = sum(
            len(f.miembros) + 1 for f in resultados_filtrados
        )
        edades = [
            f.fecha_nacimiento_jefe
            for f in resultados_filtrados
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

        tarjeta_familias.current.content.controls[1].value = str(
            total_familias
        )
        tarjeta_personas.current.content.controls[1].value = str(
            total_personas
        )
        tarjeta_menores.current.content.controls[1].value = str(total_menores)
        tarjeta_mayores.current.content.controls[1].value = str(total_mayores)

        tarjeta_familias.current.update()
        tarjeta_personas.current.update()
        tarjeta_menores.current.update()
        tarjeta_mayores.current.update()

    def mostrar_detalle(familia, e):
        personas = [
            ft.Text(
                f"Jefe: {familia.nombres_jefe} {familia.apellidos_jefe} | "
                f"ID: {familia.tipo_id}-{familia.cedula_jefe} | "
                f"Edad: {calcular_edad_detallada(familia.fecha_nacimiento_jefe)}",
                weight="bold",
            )
        ]
        if familia.miembros:
            personas.append(ft.Divider())
            personas.append(ft.Text("Carga familiar", weight="bold"))
            personas.extend(
                ft.Text(
                    f"{miembro.nombres} {miembro.apellidos} | "
                    f"{miembro.parentesco} | ID: {miembro.tipo_id}-{miembro.cedula} | "
                    f"Edad: {calcular_edad_detallada(miembro.fecha_nacimiento)}"
                )
                for miembro in familia.miembros
            )
        else:
            personas.append(ft.Text("No tiene carga familiar registrada."))

        dialogo = ft.AlertDialog(
            title=ft.Text(f"Registro de {familia.nombres_jefe} {familia.apellidos_jefe}"),
            content=ft.Column(personas, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Cerrar", on_click=lambda ev: e.page.close(dialogo))],
        )
        e.page.dialog = dialogo
        dialogo.open = True
        e.page.update()

    def editar_carga_familiar(familia, e):
        e.page.snack_bar = ft.SnackBar(ft.Text("Abriendo editor de carga familiar..."))
        e.page.snack_bar.open = True
        e.page.update()
        session = SessionLocal()
        familia = (
            session.query(Familia)
            .options(joinedload(Familia.miembros))
            .filter(Familia.id == familia.id)
            .first()
        )
        session.close()
        if not familia:
            e.page.snack_bar = ft.SnackBar(ft.Text("No se encontró la familia seleccionada"))
            e.page.snack_bar.open = True
            e.page.update()
            return

        nombre = ft.TextField(label="Nombres", width=220)
        apellido = ft.TextField(label="Apellidos", width=220)
        tipo_id = ft.Dropdown(
            label="Tipo de ID",
            width=120,
            value="V",
            options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
        )
        cedula = ft.TextField(label="Cédula", width=180)
        parentesco = ft.TextField(label="Parentesco", width=180)
        fecha_nacimiento = ft.TextField(
            label="Fecha de nacimiento", width=190, read_only=True
        )
        miembro_actual = [None]
        lista_miembros = ft.Column([], scroll=ft.ScrollMode.AUTO, height=220)

        def limpiar_formulario():
            miembro_actual[0] = None
            nombre.value = ""
            apellido.value = ""
            tipo_id.value = "V"
            cedula.value = ""
            parentesco.value = ""
            fecha_nacimiento.value = ""

        def cargar_miembro(miembro):
            miembro_actual[0] = miembro
            nombre.value = miembro.nombres
            apellido.value = miembro.apellidos
            tipo_id.value = miembro.tipo_id or "V"
            cedula.value = miembro.cedula if miembro.cedula != "No posee" else ""
            parentesco.value = miembro.parentesco
            fecha_nacimiento.value = (
                miembro.fecha_nacimiento.strftime("%d-%m-%Y")
                if miembro.fecha_nacimiento
                else ""
            )
            e.page.update()

        def eliminar_miembro(miembro, ev):
            def confirmar_eliminacion(confirmacion_ev):
                session = SessionLocal()
                miembro_bd = session.query(Miembro).filter(
                    Miembro.id == miembro.id,
                    Miembro.familia_id == familia.id,
                ).first()
                if miembro_bd:
                    session.delete(miembro_bd)
                    session.commit()
                session.close()
                
                ev.page.close(dialogo_confirmacion)
                limpiar_formulario()
                refrescar_lista()
                
                # REFRESCAR A TABELA DA TELA PRINCIPAL
                actualizar_tabla()
                ev.page.update()

            dialogo_confirmacion = ft.AlertDialog(
                title=ft.Text("Eliminar integrante"),
                content=ft.Text(
                    f"¿Deseas eliminar a {miembro.nombres} {miembro.apellidos} "
                    "de esta carga familiar?"
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda confirmacion_ev: ev.page.close(
                            dialogo_confirmacion
                        ),
                    ),
                    ft.ElevatedButton(
                        "Eliminar",
                        bgcolor=COLOR_ROJO,
                        color=COLOR_BLANCO,
                        on_click=confirmar_eliminacion,
                    ),
                ],
            )
            ev.page.open(dialogo_confirmacion)

        def refrescar_lista():
            session = SessionLocal()
            miembros_actualizados = (
                session.query(Miembro)
                .filter(Miembro.familia_id == familia.id)
                .order_by(Miembro.id)
                .all()
            )
            session.close()
            lista_miembros.controls = [
                ft.Row(
                    [
                        ft.Text(
                            f"{miembro.nombres} {miembro.apellidos} - {miembro.parentesco}",
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            tooltip="Editar integrante",
                            icon_color=COLOR_VERDE,
                            on_click=lambda ev, m=miembro: cargar_miembro(m),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="Eliminar integrante",
                            icon_color=COLOR_ROJO,
                            on_click=lambda ev, m=miembro: eliminar_miembro(m, ev),
                        ),
                    ]
                )
                for miembro in miembros_actualizados
            ]
        def guardar_miembro(ev):
            if not nombre.value.strip() or not apellido.value.strip() or not fecha_nacimiento.value:
                ev.page.snack_bar = ft.SnackBar(
                    ft.Text("Completa nombres, apellidos y fecha de nacimiento")
                )
                ev.page.snack_bar.open = True
                ev.page.update()
                return

            try:
                try:
                    fecha = datetime.datetime.strptime(
                        fecha_nacimiento.value, "%d-%m-%Y"
                    ).date()
                except ValueError:
                    fecha = datetime.datetime.strptime(
                        fecha_nacimiento.value, "%Y-%m-%d"
                    ).date()
            except ValueError:
                ev.page.snack_bar = ft.SnackBar(
                    ft.Text("La fecha debe tener el formato DD-MM-AAAA")
                )
                ev.page.snack_bar.open = True
                ev.page.update()
                return

            cedula_valor = cedula.value.strip() or "No posee"
            session = SessionLocal()
            consulta = session.query(Miembro).filter(Miembro.cedula == cedula_valor)
            if miembro_actual[0] is not None:
                consulta = consulta.filter(Miembro.id != miembro_actual[0].id)
            if cedula_valor != "No posee" and consulta.first():
                session.close()
                ev.page.snack_bar = ft.SnackBar(
                    ft.Text("Ya existe un integrante con esa cédula")
                )
                ev.page.snack_bar.open = True
                ev.page.update()
                return

            familia_bd = session.query(Familia).filter(Familia.id == familia.id).first()
            if miembro_actual[0] is None:
                miembro_bd = Miembro(
                    familia_id=familia.id,
                    es_beneficiario="No",
                    bonos="Ninguno",
                )
                session.add(miembro_bd)
            else:
                miembro_bd = session.query(Miembro).filter(
                    Miembro.id == miembro_actual[0].id
                ).first()

            if not familia_bd or not miembro_bd:
                session.close()
                return

            miembro_bd.nombres = nombre.value.strip()
            miembro_bd.apellidos = apellido.value.strip()
            miembro_bd.tipo_id = tipo_id.value or "V"
            miembro_bd.cedula = cedula_valor
            miembro_bd.fecha_nacimiento = fecha
            miembro_bd.parentesco = parentesco.value.strip() or "Otro"

            try:
                session.commit()
                session.close()

                limpiar_formulario()
                refrescar_lista()
                
                # REFRESCAR A TELA E A TABELA PRINCIPAL
                actualizar_tabla()
                ev.page.update()

            except Exception as error:
                session.rollback()
                session.close()
                ev.page.snack_bar = ft.SnackBar(
                    ft.Text(f"No se pudo guardar el integrante: {error}")
                )
                ev.page.snack_bar.open = True
                ev.page.update()
                return
        boton_fecha = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            icon_color=COLOR_VERDE,
            tooltip="Seleccionar fecha",
            on_click=lambda ev: abrir_datepicker_solo_fecha(
                ev, fecha_nacimiento, formato="%d-%m-%Y"
            ),
        )
        formulario = ft.Column(
            [
                ft.Text("Agregar o editar integrante", weight="bold"),
                ft.Row([nombre, apellido, tipo_id, cedula], wrap=True),
                ft.Row([parentesco, fecha_nacimiento, boton_fecha], wrap=True),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Guardar integrante",
                            icon=ft.Icons.SAVE,
                            bgcolor=COLOR_VERDE,
                            color=COLOR_BLANCO,
                            on_click=guardar_miembro,
                        ),
                        ft.TextButton("Limpiar", on_click=lambda ev: (limpiar_formulario(), ev.page.update())),
                    ]
                ),
                ft.Divider(),
                ft.Text("Integrantes registrados", weight="bold"),
                lista_miembros,
            ],
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        )
        dialogo = ft.AlertDialog(
            title=ft.Text(
                f"Editar carga familiar de {familia.nombres_jefe} {familia.apellidos_jefe}"
            ),
            content=formulario,
            actions=[
                ft.TextButton("Cerrar", on_click=lambda ev: ev.page.close(dialogo))
            ],
        )
        refrescar_lista()
        e.page.dialog = dialogo
        dialogo.open = True
        e.page.update()

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
                                        ft.Container(
                                            content=ft.Row(
                                                [
                                                    ft.Icon(ft.Icons.EDIT, color=COLOR_VERDE),
                                                    ft.Text("Editar carga", color=COLOR_VERDE),
                                                ],
                                                spacing=4,
                                            ),
                                            tooltip="Editar o agregar carga familiar",
                                            padding=ft.padding.symmetric(horizontal=6, vertical=4),
                                            on_click=lambda e, fid=f.id: e.page.go(
                                                f"/registro_familia?edit={fid}"
                                            ),
                                        ),
                                        ft.Container(
                                            content=ft.Icon(ft.Icons.VISIBILITY, color=COLOR_VERDE),
                                            tooltip="Ver registro y carga familiar",
                                            padding=8,
                                            on_click=lambda e, familia=f: mostrar_detalle(familia, e),
                                        ),
                                        ft.Container(
                                            content=ft.Icon(ft.Icons.DELETE, color=COLOR_ROJO),
                                            tooltip="Eliminar",
                                            padding=8,
                                            on_click=lambda e, fid=f.id: eliminar_familia(fid, e),
                                        ),
                                    ],
                                    spacing=5,
                                ),
                                width=120,
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

    filtro_edad = ft.Ref[ft.Dropdown]()
    filtro_edad.current = ft.Dropdown(
        label="Filtrar por edad",
        width=260,
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
        width=180,
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
        width=300,
        on_change=lambda e: cambiar_pagina(0),
    )

    def actualizar_hint_busqueda():
        ayudas = {
            "Nombre": "Escriba un nombre",
            "Cédula": "Escriba una cédula",
            "Edad": "Escriba una edad, meses o RN",
        }
        buscador.current.hint_text = ayudas.get(
            tipo_busqueda.current.value, "Buscar"
        )
        buscador.current.value = ""
        buscador.current.update()
        cambiar_pagina(0)

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
                filtro_edad.current,
                tipo_busqueda.current,
                buscador.current,
                boton_exportar_excel,
                boton_exportar_json,
                boton_exportar,
            ],
            spacing=15,
            wrap=True,
        ),
        bgcolor="#ffffff66",
        padding=20,
        border_radius=10,
        width=1400,
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

    tarjeta_menores.current = ft.Container(
        content=ft.Column([
            ft.Text("Menores de edad (<18)", size=14, color=COLOR_GRIS, weight="bold"),
            ft.Text("0", size=22, weight="bold", color=COLOR_NEGRO),
        ]),
        bgcolor=COLOR_BLANCO,
        padding=20,
        border_radius=10,
        width=250,
    )

    tarjeta_mayores.current = ft.Container(
        content=ft.Column([
            ft.Text("Mayores de edad (18+)", size=14, color=COLOR_GRIS, weight="bold"),
            ft.Text("0", size=22, weight="bold", color=COLOR_NEGRO),
        ]),
        bgcolor=COLOR_BLANCO,
        padding=20,
        border_radius=10,
        width=250,
    )

    resumen = ft.Row(
        [
            tarjeta_familias.current,
            tarjeta_personas.current,
            tarjeta_menores.current,
            tarjeta_mayores.current,
        ],
        spacing=20,
        wrap=True,
    )

    # ENCABEZADO: Botones principales (Incluye Cargar Censo Excel y Cargar Respaldo JSON)
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
            consulta_miembro = session.query(Miembro).filter(
                Miembro.cedula == cedula_valor
            )
            if familia_edicion is not None:
                consulta_miembro = consulta_miembro.filter(
                    Miembro.familia_id != edit_id
                )
            existente_miembro = consulta_miembro.first()
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
        if existente_jefe and (familia_edicion is None or existente_jefe.id != edit_id):
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

        session.commit()
        session.close()

        mensaje = "✅ Familia actualizada correctamente" if familia_edicion else "✅ Familia guardada correctamente"
        snackbar = ft.SnackBar(ft.Text(mensaje))
        e.page.overlay.append(snackbar)
        snackbar.open = True
        e.page.update()

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

            fila_ref[0] = ft.Row([
                ft.Text(miembro_data["nombres"], width=160),
                ft.Text(miembro_data["apellidos"], width=160),
                ft.Text(miembro_data["tipo"], width=120),
                ft.Text(miembro_data["cedula"], width=170),
                ft.Text(miembro_data["fecha_nacimiento"], width=160),
                ft.Text(miembro_data["edad"], width=100),
                ft.Text(miembro_data["parentesco"], width=160),
                ft.IconButton(icon=ft.Icons.EDIT, icon_color=COLOR_VERDE, tooltip="Editar", on_click=editar_existente),
                ft.IconButton(icon=ft.Icons.DELETE, icon_color=COLOR_ROJO, tooltip="Eliminar", on_click=eliminar_existente),
            ], spacing=10)
            tabla_miembros.controls.append(fila_ref[0])

    boton_añadir = ft.ElevatedButton(
        "Añadir",
        icon=ft.Icons.ADD,
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        on_click=añadir_miembro,
    )
    boton_guardar = ft.ElevatedButton(
        "Actualizar Familia" if familia_edicion else "Guardar Familia",
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
                "Editar Familia" if familia_edicion else "Registro de Nueva Familia",
                size=26,
                weight="bold",
                color=COLOR_NEGRO,
            ),
            ft.Text(
                "Modifique los datos y la carga familiar."
                if familia_edicion
                else "Complete los datos para registrar una nueva familia en el sistema.",
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