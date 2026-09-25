import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO
from modelo import SessionLocal, Calle

# --- Definición de colores pastel para el módulo ---
PASTEL_BG = "#F4F6F8"
PASTEL_CARD = "#FFFFFF"
PASTEL_VERDE = COLOR_VERDE if 'COLOR_VERDE' in globals() else "#4CAF50"
PASTEL_VERDE_HOVER = "#388E3C"
PASTEL_TEXTO_SEC = "#6C757D"
PASTEL_BORDE = "#E0E0E0"

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
        total_paginas = max(1, (len(resultados_filtrados) + registros_por_pagina - 1) // registros_por_pagina)
        pagina_actual.current = min(pagina_actual.current, max(total_paginas - 1, 0))

        inicio = pagina_actual.current * registros_por_pagina
        fin = inicio + registros_por_pagina
        visibles = resultados_filtrados[inicio:fin]

        tabla_calles.current.rows.clear()

        if not visibles:
            tabla_calles.current.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                        ft.DataCell(ft.Text("No hay calles registradas", color=PASTEL_TEXTO_SEC, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC)),
                        ft.DataCell(ft.Text("—", color=PASTEL_TEXTO_SEC))
                    ]
                )
            )
        else:
            for calle in visibles:
                tabla_calles.current.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(calle.sector, size=14, weight=ft.FontWeight.W_500, color="#2C3E50")),
                            ft.DataCell(ft.Text(calle.nombre, size=14, color="#34495E")),
                            ft.DataCell(ft.Container(
                                content=ft.Text(str(calle.numero), size=13, weight=ft.FontWeight.BOLD, color=PASTEL_VERDE),
                                bgcolor="#E8F5E9",
                                padding=ft.padding.symmetric(horizontal=12, vertical=4),
                                border_radius=12
                            )),
                            ft.DataCell(
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_color=PASTEL_VERDE,
                                        tooltip="Editar calle",
                                        icon_size=20,
                                        on_click=lambda e, i=calle.id: e.page.go(f"/registro_calle?edit={i}")
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINED,
                                        icon_color="#E57373",
                                        tooltip="Eliminar calle",
                                        icon_size=20,
                                        on_click=lambda e, i=calle.id: eliminar_calle(i, e)
                                    )
                                ], spacing=5)
                            )
                        ]
                    )
                )

        pie_tabla.current.controls = [
            ft.Text(
                f"Mostrando {0 if len(resultados_filtrados) == 0 else inicio + 1} a {min(fin, len(resultados_filtrados))} de {len(resultados_filtrados)} resultados",
                size=13,
                color=PASTEL_TEXTO_SEC
            ),
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_ARROW_LEFT,
                    tooltip="Página anterior",
                    icon_color=PASTEL_TEXTO_SEC if pagina_actual.current == 0 else "#2C3E50",
                    disabled=pagina_actual.current == 0,
                    on_click=lambda e: cambiar_pagina(pagina_actual.current - 1)
                ),
                ft.Text(f"{pagina_actual.current + 1} / {total_paginas}", size=13, weight=ft.FontWeight.BOLD, color="#2C3E50"),
                ft.IconButton(
                    icon=ft.Icons.KEYBOARD_ARROW_RIGHT,
                    tooltip="Página siguiente",
                    icon_color=PASTEL_TEXTO_SEC if pagina_actual.current >= total_paginas - 1 else "#2C3E50",
                    disabled=pagina_actual.current >= total_paginas - 1,
                    on_click=lambda e: cambiar_pagina(pagina_actual.current + 1)
                )
            ], alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.CENTER)
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

    def cambiar_pagina(nueva_pagina):
        pagina_actual.current = max(0, nueva_pagina)
        actualizar_tabla()

    titulo = ft.Row([
        ft.Icon(ft.Icons.ROUNDED_CORNER, size=30, color=PASTEL_VERDE),
        ft.Text("Gestión de Calles", size=24, weight=ft.FontWeight.BOLD, color="#2C3E50")
    ], spacing=10)

    buscador.current = ft.TextField(
        hint_text="Buscar por nombre o sector...",
        prefix_icon=ft.Icons.SEARCH,
        width=350,
        height=45,
        content_padding=ft.padding.symmetric(horizontal=15, vertical=0),
        border_radius=10,
        border_color=PASTEL_BORDE,
        focused_border_color=PASTEL_VERDE,
        bgcolor="#F9FAFB",
        on_change=lambda e: cambiar_pagina(0)
    )

    boton_nueva_calle = ft.ElevatedButton(
        text="Añadir Nueva Calle",
        bgcolor=PASTEL_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.ADD_ROUNDED,
        height=45,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            elevation=2
        ),
        on_click=lambda e: e.page.go("/registro_calle")
    )

    tarjeta_superior = ft.Container(
        content=ft.Row(
            controls=[buscador.current, boton_nueva_calle],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        bgcolor=PASTEL_CARD,
        padding=15,
        border_radius=12,
        shadow=ft.BoxShadow(blur_radius=10, color="#0000000D", offset=ft.Offset(0, 4))
    )

    tabla_calles.current = ft.DataTable(
        heading_row_color="#F8FAFC",
        heading_row_height=45,
        data_row_min_height=50,
        divider_thickness=1,
        horizontal_margin=20,
        column_spacing=40,
        columns=[
            ft.DataColumn(ft.Text("SECTOR", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
            ft.DataColumn(ft.Text("NOMBRE DE CALLE", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
            ft.DataColumn(ft.Text("NÚMERO", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
            ft.DataColumn(ft.Text("ACCIONES", size=12, weight=ft.FontWeight.BOLD, color=PASTEL_TEXTO_SEC)),
        ],
        rows=[]
    )

    pie_tabla.current = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    pie_card = ft.Container(
        content=pie_tabla.current,
        bgcolor=PASTEL_CARD,
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        border_radius=12,
        shadow=ft.BoxShadow(blur_radius=10, color="#0000000D", offset=ft.Offset(0, 4))
    )

    actualizar_tabla()

    return ft.Container(
        content=ft.Column(
            controls=[
                titulo,
                tarjeta_superior,
                ft.Container(
                    content=ft.Column([tabla_calles.current], scroll="auto"),
                    bgcolor=PASTEL_CARD,
                    padding=10,
                    border_radius=12,
                    shadow=ft.BoxShadow(blur_radius=10, color="#0000000D", offset=ft.Offset(0, 4)),
                    expand=True
                ),
                pie_card
            ],
            spacing=15,
            expand=True
        ),
        padding=20,
        expand=True
    )

def vista_registro_calles(edit_index=None):
    session = SessionLocal()
    calle = session.query(Calle).filter(Calle.id == edit_index).first() if edit_index else None
    session.close()

    sector_valor = calle.sector if calle else ""
    nombre_valor = calle.nombre if calle else ""
    numero_valor = calle.numero if calle else ""
    titulo_texto = "Editar Calle" if calle else "Registrar Nueva Calle"

    nombre_sector = ft.TextField(
        label="Nombre del Sector",
        width=500,
        value=sector_valor,
        border_radius=10,
        border_color=PASTEL_BORDE,
        focused_border_color=PASTEL_VERDE,
        bgcolor="#F9FAFB"
    )
    
    nombre_calle = ft.TextField(
        label="Nombre de la Calle",
        width=500,
        value=nombre_valor,
        border_radius=10,
        border_color=PASTEL_BORDE,
        focused_border_color=PASTEL_VERDE,
        bgcolor="#F9FAFB"
    )
    
    numero_calle = ft.TextField(
        label="Número de Calle",
        width=250,
        keyboard_type=ft.KeyboardType.NUMBER,
        value=numero_valor,
        border_radius=10,
        border_color=PASTEL_BORDE,
        focused_border_color=PASTEL_VERDE,
        bgcolor="#F9FAFB"
    )

    def guardar_calle(e):
        if not nombre_sector.value.strip() or not nombre_calle.value.strip():
            return

        session = SessionLocal()
        if calle:
            calle_db = session.query(Calle).filter(Calle.id == edit_index).first()
            if calle_db:
                calle_db.sector = nombre_sector.value.strip()
                calle_db.nombre = nombre_calle.value.strip()
                calle_db.numero = numero_calle.value.strip()
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
        bgcolor=PASTEL_VERDE,
        color=COLOR_BLANCO,
        icon=ft.Icons.SAVE_ROUNDED,
        height=45,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=guardar_calle
    )
    
    boton_cancelar = ft.OutlinedButton(
        "Cancelar",
        icon=ft.Icons.CANCEL_OUTLINED,
        height=45,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            side=ft.BorderSide(1, PASTEL_BORDE)
        ),
        on_click=lambda e: e.page.go("/calles")
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.ADD_LOCATION_ALT_ROUNDED, size=28, color=PASTEL_VERDE),
                    ft.Text(titulo_texto, size=22, weight=ft.FontWeight.BOLD, color="#2C3E50")
                ], spacing=10),
                ft.Text("Complete la información de la calle para actualizar o agregarla al sistema.", size=13, color=PASTEL_TEXTO_SEC),
                ft.Divider(color=PASTEL_BORDE, height=20),
                ft.Text("Información de la Calle", size=16, weight=ft.FontWeight.W_600, color="#2C3E50"),
                ft.Column([
                    nombre_sector,
                    nombre_calle,
                    numero_calle,
                ], spacing=15),
                ft.Container(height=20),
                ft.Row([boton_cancelar, boton_guardar], alignment=ft.MainAxisAlignment.END, spacing=15),
            ],
            spacing=10
        ),
        bgcolor=PASTEL_CARD,
        padding=30,
        border_radius=12,
        shadow=ft.BoxShadow(blur_radius=10, color="#0000000D", offset=ft.Offset(0, 4)),
        margin=20,
        expand=True
    )
