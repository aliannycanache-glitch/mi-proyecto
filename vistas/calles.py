import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO
from modelo import SessionLocal, Calle

def vista_calles():
    registros_por_pagina = 5
    pagina_actual = ft.Ref[int]()
    pagina_actual.current = 0

    buscador = ft.Ref[ft.TextField]()
    tabla_calles = ft.Ref[ft.DataTable]()
    pie_tabla = ft.Ref[ft.Row]()
    resultados_filtrados = []

    def filtrar_datos(texto):
        session = SessionLocal()
        query = session.query(Calle)
        if texto:
            texto = texto.lower().strip()
            query = query.filter(
                (Calle.nombre.ilike(f"%{texto}%")) |
                (Calle.sector.ilike(f"%{texto}%"))
            )
        datos = query.all()
        session.close()
        return datos

    def actualizar_tabla():
        nonlocal resultados_filtrados
        resultados_filtrados = filtrar_datos(buscador.current.value)
        total_paginas = (len(resultados_filtrados) + registros_por_pagina - 1) // registros_por_pagina
        pagina_actual.current = min(pagina_actual.current, max(total_paginas - 1, 0))

        inicio = pagina_actual.current * registros_por_pagina
        fin = inicio + registros_por_pagina
        visibles = resultados_filtrados[inicio:fin]

        tabla_calles.current.rows.clear()

        if not visibles:
            tabla_calles.current.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("—", width=250)),
                        ft.DataCell(ft.Text("No hay calles registradas", width=300)),
                        ft.DataCell(ft.Text("—", width=150)),
                        ft.DataCell(ft.Text("—"))
                    ]
                )
            )
        else:
            for calle in visibles:
                tabla_calles.current.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(calle.sector, width=250)),
                    ft.DataCell(ft.Text(calle.nombre, width=300)),
                    ft.DataCell(ft.Text(calle.numero, width=150)),
                    ft.DataCell(ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            icon_color=COLOR_VERDE,
                            tooltip="Editar",
                            on_click=lambda e, i=calle.id: e.page.go(f"/registro_calle?edit={i}")
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=COLOR_ROJO,
                            tooltip="Eliminar",
                            on_click=lambda e, i=calle.id: eliminar_calle(i, e)
                        )
                    ], spacing=5))
                ]))

        pie_tabla.current.controls = [
            ft.Text(
                f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} resultados",
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

        if tabla_calles.current.page is not None:
            tabla_calles.current.update()
        if pie_tabla.current.page is not None:
            pie_tabla.current.update()

    def eliminar_calle(indice, e):
        session = SessionLocal()
        calle = session.query(Calle).filter(Calle.id == indice).first()
        if calle:
            session.delete(calle)
            session.commit()
        session.close()
        actualizar_tabla()
        e.page.update()

    def cambiar_pagina(nueva_pagina):
        pagina_actual.current = max(0, nueva_pagina)
        actualizar_tabla()

    titulo = ft.Text("Gestión de Calles", size=26, weight="bold", color=COLOR_NEGRO)

    buscador.current = ft.TextField(
        hint_text="Buscar por nombre o sector",
        prefix_icon=ft.Icons.SEARCH,
        width=300,
        border_radius=8,
        on_change=lambda e: cambiar_pagina(0)
    )

    boton_nueva_calle = ft.ElevatedButton(
        text="Añadir Nueva Calle",
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.ADD,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=lambda e: e.page.go("/registro_calle")
    )

    tarjeta_superior = ft.Container(
        content=ft.Row(
            controls=[buscador.current, boton_nueva_calle],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=20
        ),
        bgcolor="#ffffff66",
        padding=20,
        border_radius=10
    )

    tabla_calles.current = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("SECTOR")),
            ft.DataColumn(ft.Text("NOMBRE DE CALLE")),
            ft.DataColumn(ft.Text("NÚMERO")),
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

    actualizar_tabla()

    return ft.Column(
        controls=[
            titulo,
            tarjeta_superior,
            ft.Container(
                content=tabla_calles.current,
                bgcolor="#ffffff66",
                padding=20,
                border_radius=10,
                border=ft.border.all(1, COLOR_GRIS),
                width=1200,
                expand=True
            ),
            pie_card
        ],
        spacing=20,
        scroll="auto",
        expand=True
    )

def vista_registro_calles(edit_index=None):
    session = SessionLocal()
    calle = session.query(Calle).filter(Calle.id == edit_index).first() if edit_index else None
    session.close()

    sector_valor = calle.sector if calle else ""
    nombre_valor = calle.nombre if calle else ""
    numero_valor = calle.numero if calle else ""
    titulo_texto = "📍 Editar Calle" if calle else "Registrar Nueva Calle"

    nombre_sector = ft.TextField(label="Nombre del Sector", width=500, value=sector_valor)
    nombre_calle = ft.TextField(label="Nombre de la Calle", width=500, value=nombre_valor)
    numero_calle = ft.TextField(
        label="Número de Calle",
        width=250,
        keyboard_type=ft.KeyboardType.NUMBER,
        value=numero_valor
    )

    def guardar_calle(e):
        session = SessionLocal()
        if calle:
            calle.sector = nombre_sector.value.strip()
            calle.nombre = nombre_calle.value.strip()
            calle.numero = numero_calle.value.strip()
        else:
            nueva = Calle(
                sector=nombre_sector.value.strip(),
                nombre=nombre_calle.value.strip(),
                numero=numero_calle.value.strip()
            )
            session.add(nueva)
        session.commit()
        session.close()
        e.page.go("/calles")

    boton_guardar = ft.ElevatedButton(
        "Guardar",
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.SAVE,
        on_click=guardar_calle
    )
    boton_cancelar = ft.TextButton(
        "Cancelar",
        icon=ft.Icons.CANCEL,
        on_click=lambda e: e.page.go("/calles")
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(titulo_texto, size=26, weight="bold", color="black"),
                ft.Text("Complete la información de la calle para agregarla al sistema.", size=14, color="gray"),
                ft.Divider(),
                ft.Text("Información de la Calle", size=18, weight="bold", color="black"),
                ft.Row([nombre_sector], spacing=20),
                ft.Row([nombre_calle], spacing=20),
                ft.Row([numero_calle], spacing=20),
                ft.Container(height=20),
                ft.Row([boton_cancelar, boton_guardar], alignment=ft.MainAxisAlignment.END, spacing=20),
            ]
        ),
        bgcolor="white",
        padding=30,
        border_radius=12,
        expand=True,
    )
