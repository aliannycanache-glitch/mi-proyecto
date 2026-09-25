import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO
from modelo import SessionLocal, RegistroGas, Familia, Calle
from sqlalchemy.orm import joinedload
from generador_reportes import generar_pdf_gas

def vista_gas(pagina: ft.Page):
    registros_por_pagina = 5
    pagina_actual = ft.Ref[int]()
    pagina_actual.current = 0
    tabla_gas = ft.Ref[ft.DataTable]()
    pie_tabla = ft.Ref[ft.Row]()
    resultados_filtrados = []

    # FilePicker para guardar el reporte PDF
    def guardar_archivo(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        exportar_pdf(e.path, pagina)

    file_picker = ft.FilePicker(on_result=guardar_archivo)
    if file_picker not in pagina.overlay:
        pagina.overlay.append(file_picker)

    def eliminar_registro(registro_id, e):
        with SessionLocal() as session:
            registro = session.query(RegistroGas).filter(RegistroGas.id == registro_id).first()
            if registro:
                session.delete(registro)
                session.commit()
        actualizar_tabla()
        if e.page:
            e.page.update()

    def actualizar_tabla():
        nonlocal resultados_filtrados
        with SessionLocal() as session:
            resultados_filtrados = (
                session.query(RegistroGas)
                .options(joinedload(RegistroGas.familia).joinedload(Familia.calle))
                .all()
            )

        total_paginas = (len(resultados_filtrados) + registros_por_pagina - 1) // registros_por_pagina
        pagina_actual.current = min(pagina_actual.current, max(total_paginas - 1, 0))

        inicio = pagina_actual.current * registros_por_pagina
        fin = inicio + registros_por_pagina
        visibles = resultados_filtrados[inicio:fin]

        if tabla_gas.current:
            tabla_gas.current.rows.clear()
            for r in visibles:
                if r.familia:
                    nombre_jefe = f"{r.familia.nombres_jefe} {r.familia.apellidos_jefe}"
                    calle_nom = r.familia.calle.nombre if r.familia.calle else "Sin Calle"
                    casa_num = f", Casa {r.familia.casa_num}" if r.familia.casa_num else ""
                    direccion_jefe = f"{calle_nom}{casa_num}"
                else:
                    nombre_jefe = "Desconocido"
                    direccion_jefe = "N/A"

                tabla_gas.current.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Container(ft.Text(nombre_jefe, weight=ft.FontWeight.W_500), width=220)),
                    ft.DataCell(ft.Container(ft.Text(direccion_jefe, color=COLOR_NEGRO), width=280)),
                    ft.DataCell(ft.Container(ft.Text(str(r.kg10 or 0), weight=ft.FontWeight.BOLD), width=50)),
                    ft.DataCell(ft.Container(ft.Text(str(r.kg18 or 0), weight=ft.FontWeight.BOLD), width=50)),
                    ft.DataCell(ft.Container(ft.Text(str(r.kg27 or 0), weight=ft.FontWeight.BOLD), width=50)),
                    ft.DataCell(ft.Container(ft.Text(str(r.kg43 or 0), weight=ft.FontWeight.BOLD), width=50)),
                    ft.DataCell(ft.Container(ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.DELETE_ROUNDED,
                            icon_color=COLOR_ROJO,
                            tooltip="Eliminar",
                            on_click=lambda e, rid=r.id: eliminar_registro(rid, e)
                        )
                    ], spacing=5), width=70))
                ]))

        if pie_tabla.current:
            pie_tabla.current.controls = [
                ft.Text(
                    f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} registros",
                    color=COLOR_GRIS,
                    size=13
                ),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED,
                        tooltip="Anterior",
                        icon_color=COLOR_VERDE if pagina_actual.current > 0 else COLOR_GRIS,
                        disabled=pagina_actual.current == 0,
                        on_click=lambda e: cambiar_pagina(pagina_actual.current - 1)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED,
                        tooltip="Siguiente",
                        icon_color=COLOR_VERDE if pagina_actual.current < total_paginas - 1 else COLOR_GRIS,
                        disabled=pagina_actual.current >= total_paginas - 1,
                        on_click=lambda e: cambiar_pagina(pagina_actual.current + 1)
                    )
                ], alignment=ft.MainAxisAlignment.END)
            ]

        if tabla_gas.current and tabla_gas.current.page: 
            tabla_gas.current.update()
        if pie_tabla.current and pie_tabla.current.page: 
            pie_tabla.current.update()

    def cambiar_pagina(nueva_pagina):
        pagina_actual.current = nueva_pagina
        actualizar_tabla()

    titulo = ft.Text("Censo de Gas", size=26, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)

    boton_añadir = ft.ElevatedButton(
        text="Añadir Registro",
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.ADD_ROUNDED,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18, vertical=12)
        ),
        on_click=lambda e: e.page.go("/registro_gas")
    )

    boton_exportar = ft.OutlinedButton(
        text="Exportar PDF",
        icon=ft.Icons.PICTURE_IN_PICTURE_ROUNDED,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            color=COLOR_VERDE,
            padding=ft.padding.symmetric(horizontal=15, vertical=12)
        ),
        on_click=lambda e: file_picker.save_file(file_name="Reporte_Censo_Gas.pdf")
    )

    # Cálculo de métricas
    with SessionLocal() as session:
        registros = session.query(RegistroGas).all()
        total_kg10 = sum(r.kg10 or 0 for r in registros)
        total_kg18 = sum(r.kg18 or 0 for r in registros)
        total_kg27 = sum(r.kg27 or 0 for r in registros)
        total_kg43 = sum(r.kg43 or 0 for r in registros)
        total_cilindros = total_kg10 + total_kg18 + total_kg27 + total_kg43

    def caja_resumen(titulo_text, cantidad, icono, color_fondo, color_texto):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icono, color=color_texto, size=24),
                    bgcolor="#FFFFFF",
                    padding=10,
                    border_radius=10
                ),
                ft.Column([
                    ft.Text(titulo_text, size=12, weight=ft.FontWeight.W_500, color=COLOR_GRIS),
                    ft.Text(str(cantidad), size=20, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
            ], spacing=12),
            bgcolor=color_fondo,
            padding=15,
            border_radius=12,
            border=ft.border.all(1, "#E0E0E0"),
            width=210,
            height=80
        )

    resumen = ft.Row([
        caja_resumen("Total Cilindros", total_cilindros, ft.Icons.PROPANE_TANK_ROUNDED, "#E8F5E9", COLOR_VERDE),
        caja_resumen("Cilindros 10kg", total_kg10, ft.Icons.GAS_METER_ROUNDED, "#E3F2FD", "#2196F3"),
        caja_resumen("Cilindros 18kg", total_kg18, ft.Icons.GAS_METER_ROUNDED, "#FFF8E1", "#FFB300"),
        caja_resumen("Cilindros 27kg", total_kg27, ft.Icons.GAS_METER_ROUNDED, "#FCE4EC", "#E91E63"),
        caja_resumen("Cilindros 43kg", total_kg43, ft.Icons.GAS_METER_ROUNDED, "#F3E5F5", "#9C27B0"),
    ], wrap=True, spacing=15)

    tabla_gas.current = ft.DataTable(
        heading_row_color="#F8F9FA",
        heading_row_height=45,
        data_row_min_height=50,
        columns=[
            ft.DataColumn(ft.Text("JEFE DE FAMILIA", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
            ft.DataColumn(ft.Text("DIRECCIÓN", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
            ft.DataColumn(ft.Text("10kg", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
            ft.DataColumn(ft.Text("18kg", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
            ft.DataColumn(ft.Text("27kg", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
            ft.DataColumn(ft.Text("43kg", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
            ft.DataColumn(ft.Text("ACCIONES", weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
        ],
        rows=[]
    )

    pie_tabla.current = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    encabezado = ft.Row(
        controls=[
            ft.Text("Resumen del Censo de Gas", size=18, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
            ft.Row([boton_exportar, boton_añadir], spacing=10)
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    columna_principal = ft.Container(
        content=ft.Column([
            titulo,
            resumen,
            ft.Divider(height=10, color="transparent"),
            encabezado,
            ft.Container(
                content=ft.Column([
                    tabla_gas.current,
                    ft.Divider(height=1, color="#E0E0E0"),
                    pie_tabla.current
                ], spacing=0),
                bgcolor=COLOR_BLANCO,
                padding=15,
                border_radius=12,
                border=ft.border.all(1, "#E0E0E0"),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color="#10000000")
            )
        ], spacing=15, scroll=ft.ScrollMode.AUTO),
        padding=25,
        bgcolor="#F4F6F8",
        expand=True
    )

    def inicializar():
        actualizar_tabla()

    return {"vista": columna_principal, "actualizar": inicializar}


def exportar_pdf(path_destino: str, pagina: ft.Page):
    archivo = path_destino
    if not archivo.lower().endswith(".pdf"):
        archivo += ".pdf"

    with SessionLocal() as session:
        registros = (
            session.query(RegistroGas)
            .options(joinedload(RegistroGas.familia).joinedload(Familia.calle))
            .all()
        )

    generar_pdf_gas(registros, archivo)

    dlg = ft.AlertDialog(
        title=ft.Text("Exportación exitosa"),
        content=ft.Text(f"El informe PDF fue guardado correctamente en:\n{archivo}"),
        actions=[
            ft.TextButton("Aceptar", on_click=lambda ev: pagina.close(dlg))
        ]
    )
    pagina.open(dlg)


def vista_registro_gas(pagina: ft.Page = None):
    # Campos estilizados
    campo_familia = ft.Dropdown(
        label="Seleccionar Familia", 
        width=320,
        border_radius=8,
        bgcolor=COLOR_BLANCO
    )
    campo_cedula = ft.TextField(label="Cédula", width=200, read_only=True, border_radius=8, bgcolor="#F5F5F5")
    campo_direccion = ft.TextField(label="Dirección", width=350, read_only=True, border_radius=8, bgcolor="#F5F5F5")

    campo_kg10 = ft.TextField(label="10kg", width=110, value="0", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    campo_kg18 = ft.TextField(label="18kg", width=110, value="0", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    campo_kg27 = ft.TextField(label="27kg", width=110, value="0", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    campo_kg43 = ft.TextField(label="43kg", width=110, value="0", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)

    def guardar_registro(e):
        if not campo_familia.value:
            dlg = ft.AlertDialog(
                title=ft.Text("Campo Requerido"),
                content=ft.Text("Por favor seleccione una familia para registrar el censo de gas."),
                actions=[ft.TextButton("Entendido", on_click=lambda ev: e.page.close(dlg))]
            )
            e.page.open(dlg)
            return

        with SessionLocal() as session:
            nuevo = RegistroGas(
                familia_id=int(campo_familia.value),
                kg10=int(campo_kg10.value or 0),
                kg18=int(campo_kg18.value or 0),
                kg27=int(campo_kg27.value or 0),
                kg43=int(campo_kg43.value or 0)
            )
            session.add(nuevo)
            session.commit()

        e.page.go("/gas")

    def cancelar(e):
        e.page.go("/gas")

    def actualizar_datos(e):
        familia_id = e.control.value
        if not familia_id:
            return

        with SessionLocal() as session:
            familia = (
                session.query(Familia)
                .options(joinedload(Familia.calle))
                .filter(Familia.id == int(familia_id))
                .first()
            )

            if familia:
                campo_cedula.value = f"{familia.tipo_id}-{familia.cedula_jefe}"
                calle_nom = familia.calle.nombre if familia.calle else "Sin Calle"
                casa_num = f", Casa {familia.casa_num}" if familia.casa_num else ""
                campo_direccion.value = f"{calle_nom}{casa_num}"
                
                campo_cedula.update()
                campo_direccion.update()

    # Cargar listado de familias
    with SessionLocal() as session:
        familias = session.query(Familia).all()
        campo_familia.options = [
            ft.dropdown.Option(
                key=str(f.id), 
                text=f"{f.nombres_jefe} {f.apellidos_jefe}"
            ) for f in familias
        ]

    campo_familia.on_change = actualizar_datos

    boton_guardar = ft.ElevatedButton(
        "Guardar Registro", 
        bgcolor=COLOR_VERDE, 
        color=COLOR_BLANCO, 
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=guardar_registro
    )
    boton_cancelar = ft.OutlinedButton("Cancelar", on_click=cancelar, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

    formulario = ft.Column([
        ft.Text("Nuevo Registro de Censo de Gas", size=22, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
        ft.Divider(color="transparent", height=10),
        ft.Text("Datos de la Familia", weight=ft.FontWeight.BOLD, color=COLOR_GRIS),
        ft.Row([campo_familia, campo_cedula, campo_direccion], wrap=True, spacing=15),
        ft.Divider(color="transparent", height=10),
        ft.Text("Cantidad de Cilindros por Peso", weight=ft.FontWeight.BOLD, color=COLOR_GRIS),
        ft.Row([campo_kg10, campo_kg18, campo_kg27, campo_kg43], wrap=True, spacing=15),
        ft.Divider(color="transparent", height=15),
        ft.Row([boton_cancelar, boton_guardar], alignment=ft.MainAxisAlignment.END, spacing=15)
    ], spacing=10)

    return ft.Container(
        content=formulario, 
        bgcolor=COLOR_BLANCO, 
        padding=30, 
        border_radius=12,
        border=ft.border.all(1, "#E0E0E0"),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color="#10000000"),
        expand=True
    )