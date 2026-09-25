import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import selectinload
from colores import COLOR_BLANCO, COLOR_GRIS, COLOR_NEGRO, COLOR_VERDE
from modelo import AdultoMayor, Familia, Miembro, ProteccionIntegral, SessionLocal
from generador_reportes import generar_pdf_proteccion_integral


def _calcular_edad(fecha_nacimiento):
    if fecha_nacimiento is None:
        return None
    hoy = datetime.today()
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))


def vista_proteccion_integral(pagina: ft.Page):
    def exportar_pdf(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        destino = e.path if e.path.lower().endswith(".pdf") else f"{e.path}.pdf"
        with SessionLocal() as session:
            casos = session.query(ProteccionIntegral).order_by(ProteccionIntegral.id.desc()).all()
            generar_pdf_proteccion_integral(casos, destino)
        pagina.snack_bar = ft.SnackBar(ft.Text(f"Reporte guardado en: {destino}"))
        pagina.snack_bar.open = True
        pagina.update()

    file_picker = ft.FilePicker(on_result=exportar_pdf)
    pagina.overlay.append(file_picker)

    session = SessionLocal()
    familias = session.query(Familia).options(selectinload(Familia.miembros)).order_by(Familia.id.desc()).all()
    total_casos = session.query(ProteccionIntegral).count()
    session.close()

    personas = []
    for familia in familias:
        personas.append((familia.cedula_jefe, f"{familia.nombres_jefe} {familia.apellidos_jefe}", familia.id, familia.fecha_nacimiento_jefe, familia.es_beneficiario, familia.bono))
        personas.extend((miembro.cedula, f"{miembro.nombres} {miembro.apellidos}", familia.id, miembro.fecha_nacimiento, miembro.es_beneficiario, miembro.bonos) for miembro in familia.miembros)
    total_ayudas = sum(1 for persona in personas if persona[4] == "Si" or (persona[5] or "Ninguno") != "Ninguno")

    def tarjeta(label: str, valor, color=COLOR_VERDE):
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=COLOR_GRIS),
                        ft.Text(str(valor), size=22, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text("Registros", size=10, color=COLOR_GRIS),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=14,
                width=175,
                height=110,
            )
        )

    resumen = ft.Row(
        [
            tarjeta("Personas con ayudas", total_ayudas),
            tarjeta("Casos de protección", total_casos),
        ],
        wrap=True,
        spacing=12,
    )

    filas_padron = []
    for cedula_persona, nombre_persona, familia_id, fecha, beneficiario_persona, bonos_persona in personas:
        edad = _calcular_edad(fecha)
        categoria = "Bolsa Adulto Mayor" if edad is not None and edad >= 60 else "Adulto Mayor sin bolsa" if edad is not None and edad >= 50 else "Sin clasificación"
        filas_padron.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(cedula_persona)),
            ft.DataCell(ft.Text(nombre_persona)),
            ft.DataCell(ft.Text(str(familia_id))),
            ft.DataCell(ft.Text(categoria)),
            ft.DataCell(ft.Text(beneficiario_persona or "No")),
            ft.DataCell(ft.Text(bonos_persona or "Ninguno")),
        ]))

    tabla_padron = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cédula")),
            ft.DataColumn(ft.Text("Nombre")),
            ft.DataColumn(ft.Text("Cód. Familia")),
            ft.DataColumn(ft.Text("Categoría")),
            ft.DataColumn(ft.Text("Beneficiario")),
            ft.DataColumn(ft.Text("Bonos")),
        ],
        rows=filas_padron,
    )

    contenido = ft.Container(
        content=ft.Column(
            [
                ft.Text("Gestión de Protección Integral", size=26, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Text(
                    "Seguimiento de familias, condiciones de vulnerabilidad y clasificación de adultos mayores.",
                    size=13,
                    color=COLOR_GRIS,
                ),
                ft.Divider(),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Reporte PDF",
                            icon=ft.Icons.PICTURE_AS_PDF,
                            on_click=lambda e: file_picker.save_file(
                                dialog_title="Guardar reporte de protección integral",
                                file_name="Reporte_Proteccion_Integral.pdf",
                                allowed_extensions=["pdf"],
                            ),
                        ),
                        ft.ElevatedButton(
                            "Registrar caso",
                            icon=ft.Icons.ADD,
                            bgcolor=COLOR_VERDE,
                            color=COLOR_BLANCO,
                            on_click=lambda e: pagina.go("/registro_proteccion_integral"),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
                ft.Text("Resumen general", size=18, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                resumen,
                ft.Divider(),
                ft.Text("Padrón de ayudas y protección", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Container(content=tabla_padron, padding=10, bgcolor="#83d5e877", border=ft.border.all(1, COLOR_GRIS), border_radius=8),
            ],
            spacing=18,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=COLOR_BLANCO,
        padding=20,
        border_radius=12,
        expand=True,
    )

    return {"vista": contenido, "actualizar": lambda: None}


def vista_registro_proteccion_integral():
    tipo_id = ft.Dropdown(
        label="Tipo de ID",
        width=120,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula = ft.TextField(label="Cédula", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    nombres = ft.TextField(label="Nombres", width=260)
    apellidos = ft.TextField(label="Apellidos", width=260)
    telefono = ft.TextField(label="Teléfono", width=220, keyboard_type=ft.KeyboardType.NUMBER)
    direccion = ft.TextField(label="Dirección", width=520)
    tipo_caso = ft.Dropdown(
        label="Tipo de caso",
        width=260,
        options=[
            ft.dropdown.Option("Vulnerabilidad social"),
            ft.dropdown.Option("Violencia de género"),
            ft.dropdown.Option("Protección infantil"),
            ft.dropdown.Option("Adulto mayor"),
            ft.dropdown.Option("Otro"),
        ],
    )
    descripcion = ft.TextField(label="Descripción del caso", width=520, multiline=True, min_lines=4)
    estado = ft.Dropdown(
        label="Estado",
        width=220,
        options=[ft.dropdown.Option("Abierto"), ft.dropdown.Option("En proceso"), ft.dropdown.Option("Cerrado")],
    )
    atendido_por = ft.TextField(label="Atendido por", width=260)

    def guardar(e):
        if not nombres.value.strip() or not apellidos.value.strip() or not cedula.value.strip() or not descripcion.value.strip():
            e.page.snack_bar = ft.SnackBar(ft.Text("Completa los campos obligatorios del caso."))
            e.page.snack_bar.open = True
            e.page.update()
            return

        session = SessionLocal()
        existente = session.query(ProteccionIntegral).filter(ProteccionIntegral.cedula == cedula.value.strip()).first()
        if existente:
            session.close()
            e.page.snack_bar = ft.SnackBar(ft.Text("Ya existe un caso registrado con esa cédula."))
            e.page.snack_bar.open = True
            e.page.update()
            return

        nuevo = ProteccionIntegral(
            nombres=nombres.value.strip(),
            apellidos=apellidos.value.strip(),
            tipo_id=tipo_id.value or "V",
            cedula=cedula.value.strip(),
            telefono=telefono.value.strip() or None,
            direccion=direccion.value.strip() or "Sin dirección",
            tipo_caso=tipo_caso.value.strip() or "Otro",
            descripcion=descripcion.value.strip(),
            estado=estado.value or "Abierto",
            fecha_registro=datetime.today().date(),
            atendido_por=atendido_por.value.strip() or None,
        )
        session.add(nuevo)
        session.commit()
        session.close()
        e.page.go("/proteccion_integral")

    boton_guardar = ft.ElevatedButton("Guardar", bgcolor=COLOR_VERDE, color=COLOR_BLANCO, on_click=guardar)
    boton_cancelar = ft.TextButton("Cancelar", on_click=lambda e: e.page.go("/proteccion_integral"))

    formulario = ft.Container(
        content=ft.Column(
            [
                ft.Text("Registro de Protección Integral", size=28, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Divider(),
                ft.Row([nombres, apellidos], spacing=20),
                ft.Row([tipo_id, cedula], spacing=20),
                ft.Row([telefono, estado], spacing=20),
                ft.Row([direccion], spacing=20),
                ft.Row([tipo_caso, atendido_por], spacing=20),
                ft.Row([descripcion], spacing=20),
                ft.Row([boton_cancelar, boton_guardar], alignment=ft.MainAxisAlignment.END, spacing=20),
            ],
            spacing=18,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=COLOR_BLANCO,
        padding=30,
        border_radius=10,
        expand=True,
    )

    return formulario
