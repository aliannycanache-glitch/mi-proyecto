import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import selectinload
from modelo import Familia, Miembro, ProteccionIntegral, SessionLocal
from generador_reportes import generar_pdf_proteccion_integral

# ==========================================
# PALETA DE COLORES PASTEL
# ==========================================
PASTEL_VERDE_PRIMARIO = "#2E7D32"
PASTEL_VERDE_FONDO = "#E8F5E9"
PASTEL_LAVANDA_FONDO = "#F3E5F5"
PASTEL_LAVANDA_TEXTO = "#7B1FA2"
PASTEL_GRIS_FONDO = "#F4F6F8"
PASTEL_GRIS_BORDER = "#E0E6ED"
PASTEL_GRIS_TEXTO = "#78909C"
COLOR_BLANCO = "#FFFFFF"
COLOR_NEGRO = "#263238"


def _calcular_edad(fecha_nacimiento):
    if fecha_nacimiento is None:
        return None
    hoy = datetime.today()
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))


def vista_proteccion_integral(pagina: ft.Page = None):
    try:
        def exportar_pdf(e: ft.FilePickerResultEvent):
            if not e.path:
                return
            destino = e.path if e.path.lower().endswith(".pdf") else f"{e.path}.pdf"
            try:
                with SessionLocal() as session:
                    casos = session.query(ProteccionIntegral).order_by(ProteccionIntegral.id.desc()).all()
                    generar_pdf_proteccion_integral(casos, destino)
                if e.page:
                    e.page.open(ft.SnackBar(ft.Text(f"✅ Reporte guardado en: {destino}")))
            except Exception as err:
                if e.page:
                    e.page.open(ft.SnackBar(ft.Text(f"❌ Error al generar PDF: {err}")))

        file_picker = ft.FilePicker(on_result=exportar_pdf)
        if pagina and hasattr(pagina, "overlay"):
            pagina.overlay.append(file_picker)

        personas = []
        total_casos = 0
        total_ayudas = 0

        with SessionLocal() as session:
            try:
                familias = session.query(Familia).options(selectinload(Familia.miembros)).order_by(Familia.id.desc()).all()
                total_casos = session.query(ProteccionIntegral).count()

                for familia in familias:
                    personas.append((
                        familia.cedula_jefe or "No posee",
                        f"{familia.nombres_jefe or ''} {familia.apellidos_jefe or ''}".strip(),
                        familia.id,
                        familia.fecha_nacimiento_jefe,
                        familia.es_beneficiario or "No",
                        familia.bono or "Ninguno"
                    ))
                    for miembro in familia.miembros:
                        personas.append((
                            miembro.cedula or "No posee",
                            f"{miembro.nombres or ''} {miembro.apellidos or ''}".strip(),
                            familia.id,
                            miembro.fecha_nacimiento,
                            miembro.es_beneficiario or "No",
                            miembro.bonos or "Ninguno"
                        ))
                total_ayudas = sum(1 for p in personas if p[4] == "Si" or (p[5] or "Ninguno") != "Ninguno")
            except Exception as db_err:
                print(f"Error consultando BD en proteccion_integral: {db_err}")

        def tarjeta_resumen(titulo, valor, subtitulo, icono, color_fondo, color_texto):
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icono, color=color_texto, size=28),
                            bgcolor=COLOR_BLANCO,
                            padding=10,
                            border_radius=12,
                        ),
                        ft.Column(
                            [
                                ft.Text(titulo, size=12, weight=ft.FontWeight.W_600, color=PASTEL_GRIS_TEXTO),
                                ft.Text(str(valor), size=24, weight=ft.FontWeight.BOLD, color=color_texto),
                                ft.Text(subtitulo, size=11, color=PASTEL_GRIS_TEXTO),
                            ],
                            spacing=2,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=12,
                ),
                bgcolor=color_fondo,
                padding=16,
                border_radius=14,
                border=ft.border.all(1, PASTEL_GRIS_BORDER),
                width=240,
            )

        resumen = ft.Row(
            [
                tarjeta_resumen("Personas con ayudas", total_ayudas, "Beneficiarios / Bonos", ft.Icons.VOLUNTEER_AUTOMATION, PASTEL_VERDE_FONDO, PASTEL_VERDE_PRIMARIO),
                tarjeta_resumen("Casos de protección", total_casos, "Casos vulnerables", ft.Icons.SECURITY, PASTEL_LAVANDA_FONDO, PASTEL_LAVANDA_TEXTO),
            ],
            wrap=True,
            spacing=16,
        )

        filas_padron = []
        for cedula_persona, nombre_persona, familia_id, fecha, beneficiario_persona, bonos_persona in personas:
            edad = _calcular_edad(fecha)
            categoria = "Bolsa Adulto Mayor" if edad is not None and edad >= 60 else "Adulto Mayor sin bolsa" if edad is not None and edad >= 50 else "Sin clasificación"
            
            es_benef = beneficiario_persona == "Si"
            badge_benef = ft.Container(
                content=ft.Text("Sí" if es_benef else "No", color=PASTEL_VERDE_PRIMARIO if es_benef else PASTEL_GRIS_TEXTO, weight=ft.FontWeight.BOLD, size=11),
                bgcolor=PASTEL_VERDE_FONDO if es_benef else "#ECEFF1",
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                border_radius=12,
            )

            filas_padron.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(cedula_persona, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(nombre_persona, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(f"FAM-{familia_id}", color=PASTEL_GRIS_TEXTO)),
                        ft.DataCell(ft.Text(categoria, size=12)),
                        ft.DataCell(badge_benef),
                        ft.DataCell(ft.Text(bonos_persona or "Ninguno", size=12)),
                    ]
                )
            )

        tabla_padron = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Cédula", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
                ft.DataColumn(ft.Text("Nombre", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
                ft.DataColumn(ft.Text("Cód. Familia", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
                ft.DataColumn(ft.Text("Categoría", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
                ft.DataColumn(ft.Text("Beneficiario", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
                ft.DataColumn(ft.Text("Bonos Asignados", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ],
            rows=filas_padron,
            heading_row_color="#E0F2F1",
            divider_thickness=1,
            horizontal_margin=15,
            column_spacing=20,
        )

        tabla_contenedor = ft.Container(
            content=ft.Column([tabla_padron], scroll=ft.ScrollMode.AUTO),
            border_radius=12,
            border=ft.border.all(1, PASTEL_GRIS_BORDER),
            bgcolor=COLOR_BLANCO,
            padding=10,
        )

        contenido = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("Gestión de Protección Integral", size=24, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                                    ft.Text("Seguimiento de familias, condiciones de vulnerabilidad y clasificación social.", size=13, color=PASTEL_GRIS_TEXTO),
                                ],
                                expand=True,
                            ),
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
                                        "+ Registrar caso",
                                        icon=ft.Icons.ADD,
                                        bgcolor=PASTEL_VERDE_PRIMARIO,
                                        color=COLOR_BLANCO,
                                        on_click=lambda e: e.page.go("/registro_proteccion_integral") if e.page else None,
                                    ),
                                ],
                                spacing=10,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(color=PASTEL_GRIS_BORDER, height=20),
                    ft.Text("Resumen general", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                    resumen,
                    ft.Divider(color=PASTEL_GRIS_BORDER, height=20),
                    ft.Text("Padrón de Ayudas y Protección Social", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                    tabla_contenedor,
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=PASTEL_GRIS_FONDO,
            padding=25,
            border_radius=14,
            expand=True,
        )

        return {"vista": contenido, "actualizar": lambda: None}

    except Exception as general_err:
        error_container = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE, color="#D32F2F", size=48),
                ft.Text("Error al cargar la vista de Protección Integral", size=18, weight="bold", color="#D32F2F"),
                ft.Text(f"Detalle del error: {general_err}", color=COLOR_NEGRO, size=13),
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#FFEBEE",
            padding=30,
            border_radius=12,
            alignment=ft.alignment.center,
            expand=True,
        )
        return {"vista": error_container, "actualizar": lambda: None}


def vista_registro_proteccion_integral(pagina: ft.Page = None):
    tipo_id = ft.Dropdown(
        label="Tipo ID",
        width=100,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula = ft.TextField(label="Cédula", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    nombres = ft.TextField(label="Nombres", width=250)
    apellidos = ft.TextField(label="Apellidos", width=250)
    telefono = ft.TextField(label="Teléfono", width=220, keyboard_type=ft.KeyboardType.NUMBER)
    direccion = ft.TextField(label="Dirección", width=510)
    tipo_caso = ft.Dropdown(
        label="Tipo de caso",
        width=250,
        options=[
            ft.dropdown.Option("Vulnerabilidad social"),
            ft.dropdown.Option("Violencia de género"),
            ft.dropdown.Option("Protección infantil"),
            ft.dropdown.Option("Adulto mayor"),
            ft.dropdown.Option("Otro"),
        ],
    )
    descripcion = ft.TextField(label="Descripción del caso", width=510, multiline=True, min_lines=4)
    estado = ft.Dropdown(
        label="Estado del caso",
        width=220,
        options=[ft.dropdown.Option("Abierto"), ft.dropdown.Option("En proceso"), ft.dropdown.Option("Cerrado")],
        value="Abierto",
    )
    atendido_por = ft.TextField(label="Atendido por", width=250)

    def guardar(e):
        if not nombres.value.strip() or not apellidos.value.strip() or not cedula.value.strip() or not descripcion.value.strip():
            e.page.open(ft.SnackBar(ft.Text("⚠️ Completa los campos obligatorios del caso.")))
            return

        try:
            session = SessionLocal()
            existente = session.query(ProteccionIntegral).filter(ProteccionIntegral.cedula == cedula.value.strip()).first()
            if existente:
                session.close()
                e.page.open(ft.SnackBar(ft.Text("⚠️ Ya existe un caso registrado con esa cédula.")))
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

            e.page.open(ft.SnackBar(ft.Text("✅ Caso de Protección registrado con éxito.")))
            e.page.go("/proteccion_integral")
        except Exception as err:
            e.page.open(ft.SnackBar(ft.Text(f"❌ Error al guardar el caso: {err}")))

    boton_guardar = ft.ElevatedButton(
        "Guardar Caso",
        bgcolor=PASTEL_VERDE_PRIMARIO,
        color=COLOR_BLANCO,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        ),
        on_click=guardar,
    )
    boton_cancelar = ft.OutlinedButton("Cancelar", on_click=lambda e: e.page.go("/proteccion_integral"))

    tarjeta_ciudadano = ft.Container(
        content=ft.Column(
            [
                ft.Text("Datos del Ciudadano / Solicitante", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Divider(height=10, color=PASTEL_GRIS_BORDER),
                ft.Row([nombres, apellidos], wrap=True, spacing=15),
                ft.Row([tipo_id, cedula, telefono], wrap=True, spacing=15),
                ft.Row([direccion], wrap=True, spacing=15),
            ],
            spacing=12,
        ),
        padding=20,
        bgcolor=COLOR_BLANCO,
        border_radius=12,
        border=ft.border.all(1, PASTEL_GRIS_BORDER),
    )

    tarjeta_caso = ft.Container(
        content=ft.Column(
            [
                ft.Text("Detalles del Caso Social", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Divider(height=10, color=PASTEL_GRIS_BORDER),
                ft.Row([tipo_caso, estado, atendido_por], wrap=True, spacing=15),
                ft.Row([descripcion], wrap=True, spacing=15),
            ],
            spacing=12,
        ),
        padding=20,
        bgcolor=COLOR_BLANCO,
        border_radius=12,
        border=ft.border.all(1, PASTEL_GRIS_BORDER),
    )

    formulario = ft.Container(
        content=ft.Column(
            [
                ft.Text("Registro de Caso de Protección Integral", size=24, weight="bold", color=COLOR_NEGRO),
                ft.Text("Ingrese la información requerida para aperturar el expediente de atención social.", size=13, color=PASTEL_GRIS_TEXTO),
                ft.Divider(color=PASTEL_GRIS_BORDER, height=20),
                tarjeta_ciudadano,
                tarjeta_caso,
                ft.Row([boton_cancelar, boton_guardar], alignment=ft.MainAxisAlignment.END, spacing=15),
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=PASTEL_GRIS_FONDO,
        padding=25,
        border_radius=14,
        expand=True,
    )

    # Retorno en formato diccionario para compatibilidad total con main.py
    return {"vista": formulario, "actualizar": lambda: None}