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
    file_picker = ft.FilePicker(on_result=lambda e: exportar_pdf(e))
    pagina.overlay.append(file_picker)

    def eliminar_registro(registro_id, e):
        session = SessionLocal()
        registro = session.query(RegistroGas).filter(RegistroGas.id == registro_id).first()
        if registro:
            session.delete(registro)
            session.commit()
        session.close()
        actualizar_tabla()
        e.page.update()

    # Ejemplo optimizado en vista_gas
    def actualizar_tabla():
        nonlocal resultados_filtrados
        with SessionLocal() as session:
            resultados_filtrados = (
                session.query(RegistroGas)
                .options(joinedload(RegistroGas.familia).joinedload(Familia.calle))
                .all()
            )
        # Cierre automático al salir del bloque 'with'

        total_paginas = (len(resultados_filtrados) + registros_por_pagina - 1) // registros_por_pagina
        pagina_actual.current = min(pagina_actual.current, max(total_paginas - 1, 0))

        inicio = pagina_actual.current * registros_por_pagina
        fin = inicio + registros_por_pagina
        visibles = resultados_filtrados[inicio:fin]

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
                ft.DataCell(ft.Container(ft.Text(nombre_jefe), width=200)),
                ft.DataCell(ft.Container(ft.Text(direccion_jefe), width=300)),
                ft.DataCell(ft.Container(ft.Text(str(r.kg10)), width=50)),
                ft.DataCell(ft.Container(ft.Text(str(r.kg18)), width=50)),
                ft.DataCell(ft.Container(ft.Text(str(r.kg27)), width=50)),
                ft.DataCell(ft.Container(ft.Text(str(r.kg43)), width=50)),
                ft.DataCell(ft.Container(ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color=COLOR_ROJO,
                        tooltip="Eliminar",
                        on_click=lambda e, rid=r.id: eliminar_registro(rid, e)
                    )
                ], spacing=5), width=70))
            ]))

        pie_tabla.current.controls = [
            ft.Text(
                f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} registros",
                color=COLOR_GRIS
            ),
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_ARROW_LEFT,
                    tooltip="Anterior",
                    icon_color=COLOR_GRIS if pagina_actual.current == 0 else COLOR_NEGRO,
                    disabled=pagina_actual.current == 0,
                    on_click=lambda e: cambiar_pagina(pagina_actual.current - 1)
                ),
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
                    tooltip="Siguiente",
                    icon_color=COLOR_GRIS if pagina_actual.current >= total_paginas - 1 else COLOR_NEGRO,
                    disabled=pagina_actual.current >= total_paginas - 1,
                    on_click=lambda e: cambiar_pagina(pagina_actual.current + 1)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ]

        if tabla_gas.current.page: tabla_gas.current.update()
        if pie_tabla.current.page: pie_tabla.current.update()

    def cambiar_pagina(nueva_pagina):
        pagina_actual.current = nueva_pagina
        actualizar_tabla()

    titulo = ft.Text("Censo de Gas", size=30, weight=ft.FontWeight.BOLD)

    boton_añadir = ft.ElevatedButton(
        text="Añadir Registro",
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.ADD,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: e.page.go("/registro_gas")
    )

    boton_exportar = ft.IconButton(
        icon=ft.Icons.DOWNLOAD,
        tooltip="Exportar informe PDF",
        icon_color=COLOR_VERDE,
        on_click=lambda e: file_picker.save_file(file_name="Reporte_Censo_Gas.pdf")
    )

    session = SessionLocal()
    registros = session.query(RegistroGas).all()
    session.close()

    total_kg10 = sum(r.kg10 or 0 for r in registros)
    total_kg18 = sum(r.kg18 or 0 for r in registros)
    total_kg27 = sum(r.kg27 or 0 for r in registros)
    total_kg43 = sum(r.kg43 or 0 for r in registros)
    total_cilindros = total_kg10 + total_kg18 + total_kg27 + total_kg43

    def caja_resumen(titulo, cantidad):
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD),
                ft.Text(str(cantidad), size=20, weight=ft.FontWeight.BOLD, color=COLOR_VERDE)
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=COLOR_BLANCO,
            padding=20,
            border_radius=10,
            width=220,
            height=100
        )

    resumen = ft.Row([
        caja_resumen("Total Cilindros", total_cilindros),
        caja_resumen("Cilindros 10kg", total_kg10),
        caja_resumen("Cilindros 18kg", total_kg18),
        caja_resumen("Cilindros 27kg", total_kg27),
        caja_resumen("Cilindros 43kg", total_kg43),
    ], wrap=True, spacing=10)

    tabla_gas.current = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("JEFE DE FAMILIA")),
            ft.DataColumn(ft.Text("DIRECCIÓN")),
            ft.DataColumn(ft.Text("10kg")),
            ft.DataColumn(ft.Text("18kg")),
            ft.DataColumn(ft.Text("27kg")),
            ft.DataColumn(ft.Text("43kg")),
            ft.DataColumn(ft.Text("ACCIONES")),
        ],
        rows=[]
    )

    pie_tabla.current = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    pie_card = ft.Container(
        content=pie_tabla.current,
        bgcolor="#ffffff66",
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        border_radius=10,
        border=ft.border.all(1, COLOR_GRIS),
        width=1200
    )

    encabezado = ft.Row(
        controls=[
            ft.Text("Resumen del Censo de Gas", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([boton_exportar, boton_añadir], spacing=10)
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    columna_principal = ft.Container(
        content=ft.Column([
            titulo,
            resumen,
            encabezado,
            ft.Container(
                content=tabla_gas.current,
                bgcolor="#ffffff66",
                padding=20,
                border_radius=10,
                border=ft.border.all(1, COLOR_GRIS),
                width=1200,
                expand=True
            ),
            pie_card
        ], spacing=20, scroll=ft.ScrollMode.AUTO),
        padding=20,
        bgcolor=COLOR_BLANCO,
        border_radius=10,
        expand=True
    )

    def inicializar():
        actualizar_tabla()

    return {"vista": columna_principal, "actualizar": inicializar}


def exportar_pdf(e: ft.FilePickerUploadEvent):
    if not e.path:
        return

    archivo = e.path
    if not archivo.lower().endswith(".pdf"):
        archivo += ".pdf"

    # Consultar datos completos desde la base de datos
    session = SessionLocal()
    registros = (
        session.query(RegistroGas)
        .options(joinedload(RegistroGas.familia).joinedload(Familia.calle))
        .all()
    )
    session.close()

    # Generar el PDF del censo de gas
    generar_pdf_gas(registros, archivo)

    # Notificación de éxito
    dlg = ft.AlertDialog(
        title=ft.Text("Exportación completada"),
        content=ft.Text(f"El informe PDF del censo de gas fue guardado en:\n{archivo}"),
        actions=[ft.TextButton("Cerrar", on_click=lambda ev: e.page.close_dialog())]
    )
    e.page.dialog = dlg
    dlg.open = True
    e.page.update()


def vista_registro_gas():
    campo_familia = ft.Ref[ft.Dropdown]()
    campo_cedula = ft.Ref[ft.TextField]()
    campo_direccion = ft.Ref[ft.TextField]()
    campo_kg10 = ft.Ref[ft.TextField]()
    campo_kg18 = ft.Ref[ft.TextField]()
    campo_kg27 = ft.Ref[ft.TextField]()
    campo_kg43 = ft.Ref[ft.TextField]()

    def guardar_registro(e):
        familia_id = campo_familia.current.value
        if not familia_id:
            return

        session = SessionLocal()
        nuevo = RegistroGas(
            familia_id=int(familia_id),
            kg10=int(campo_kg10.current.value or 0),
            kg18=int(campo_kg18.current.value or 0),
            kg27=int(campo_kg27.current.value or 0),
            kg43=int(campo_kg43.current.value or 0)
        )
        session.add(nuevo)
        session.commit()
        session.close()
        e.page.go("/gas")

    def cancelar(e):
        e.page.go("/gas")

    def actualizar_datos(e):
        familia_id = e.control.value
        if not familia_id:
            return

        session = SessionLocal()
        familia = (
            session.query(Familia)
            .options(joinedload(Familia.calle))
            .filter(Familia.id == int(familia_id))
            .first()
        )
        session.close()

        if familia:
            campo_cedula.current.value = f"{familia.tipo_id}-{familia.cedula_jefe}"
            calle_nom = familia.calle.nombre if familia.calle else "Sin Calle"
            casa_num = f", Casa {familia.casa_num}" if familia.casa_num else ""
            campo_direccion.current.value = f"{calle_nom}{casa_num}"
            
            campo_cedula.current.update()
            campo_direccion.current.update()

    session = SessionLocal()
    familias = session.query(Familia).all()
    
    opciones_familias = [
        ft.dropdown.Option(
            key=str(f.id), 
            text=f"{f.nombres_jefe} {f.apellidos_jefe}"
        ) for f in familias
    ]
    session.close()

    campo_familia.current = ft.Dropdown(
        label="Familia", 
        width=300, 
        options=opciones_familias, 
        on_change=actualizar_datos
    )
    campo_cedula.current = ft.TextField(label="Cédula", width=200, read_only=True)
    campo_direccion.current = ft.TextField(label="Dirección", width=300, read_only=True)

    campo_kg10.current = ft.TextField(label="Cilindros 10kg", width=100)
    campo_kg18.current = ft.TextField(label="Cilindros 18kg", width=100)
    campo_kg27.current = ft.TextField(label="Cilindros 27kg", width=100)
    campo_kg43.current = ft.TextField(label="Cilindros 43kg", width=100)

    boton_guardar = ft.ElevatedButton(
        "Guardar Registro", 
        bgcolor=COLOR_VERDE, 
        color=COLOR_BLANCO, 
        on_click=guardar_registro
    )
    boton_cancelar = ft.TextButton("Cancelar", on_click=cancelar)

    formulario = ft.Column([
        ft.Text("Registro de Gas", size=24, weight="bold", color=COLOR_NEGRO),
        ft.Row([campo_familia.current, campo_cedula.current, campo_direccion.current], spacing=20),
        ft.Row([campo_kg10.current, campo_kg18.current, campo_kg27.current, campo_kg43.current], spacing=20),
        ft.Row([boton_cancelar, boton_guardar], alignment=ft.MainAxisAlignment.END)
    ], spacing=20)

    return ft.Container(
        content=formulario, 
        bgcolor=COLOR_BLANCO, 
        padding=20, 
        border_radius=12, 
        expand=True
    )