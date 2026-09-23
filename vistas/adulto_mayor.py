import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import joinedload
from colores import COLOR_BLANCO, COLOR_GRIS, COLOR_NEGRO, COLOR_VERDE, COLOR_ROJO
from modelo import Familia, SessionLocal
from generador_reportes import generar_pdf_adultos_mayores


def calcular_estado(fecha_nac_str):
    fecha_nac = datetime.strptime(fecha_nac_str, "%Y-%m-%d")
    hoy = datetime.now()
    edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))

    if edad >= 60:
        return edad, "Si", "Si", "Bolsa Adulto Mayor"
    if edad >= 50:
        return edad, "Si", "No", "Adulto Mayor sin bolsa"
    return edad, "No", "No", "No aplica"


def vista_adulto_mayor(pagina: ft.Page):
    def obtener_padron():
        padron = []
        with SessionLocal() as session:
            familias = session.query(Familia).options(
                joinedload(Familia.miembros), joinedload(Familia.calle)
            ).all()
            for familia in familias:
                direccion = f"{familia.calle.nombre if familia.calle else 'Sin calle'} #{familia.casa_num or ''}".strip()
                personas = [
                    (familia.nombres_jefe, familia.apellidos_jefe, familia.tipo_id,
                     familia.cedula_jefe, familia.fecha_nacimiento_jefe,
                     familia.telefono_jefe),
                ]
                personas.extend(
                    (miembro.nombres, miembro.apellidos, miembro.tipo_id,
                     miembro.cedula, miembro.fecha_nacimiento, None)
                    for miembro in familia.miembros
                )
                for nombre, apellido, tipo_id, cedula, fecha, telefono in personas:
                    if not fecha:
                        continue
                    edad = date.today().year - fecha.year - ((date.today().month, date.today().day) < (fecha.month, fecha.day))
                    if edad < 50:
                        continue
                    padron.append(SimpleNamespace(
                        tipo_id=tipo_id or "V", cedula=cedula, nombres=nombre,
                        apellidos=apellido, fecha_nacimiento=fecha, edad=edad,
                        telefono=telefono, direccion=direccion,
                        categoria="Bolsa Adulto Mayor" if edad >= 60 else "Adulto Mayor sin bolsa",
                        aplica_bolsa="Si" if edad >= 60 else "No",
                        bono=familia.bono or "Ninguno",
                    ))
        return padron

    def exportar_pdf(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        destino = e.path if e.path.lower().endswith(".pdf") else f"{e.path}.pdf"
        generar_pdf_adultos_mayores(obtener_padron(), destino)
        pagina.snack_bar = ft.SnackBar(ft.Text(f"Reporte guardado en: {destino}"))
        pagina.snack_bar.open = True
        pagina.update()

    file_picker = ft.FilePicker(on_result=exportar_pdf)
    pagina.overlay.append(file_picker)

    habitantes = obtener_padron()
    total_adultos_mayores = len(habitantes)
    total_bolsas = sum(1 for habitante in habitantes if habitante.categoria == "Bolsa Adulto Mayor")

    def tarjeta_resumen(titulo, valor, subtitulo):
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(titulo, size=12, weight=ft.FontWeight.BOLD, color=COLOR_GRIS),
                        ft.Text(str(valor), size=22, weight=ft.FontWeight.BOLD, color=COLOR_VERDE),
                        ft.Text(subtitulo, size=10, color=COLOR_GRIS),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=14,
                width=220,
                height=110,
            )
        )

    resumen_adulto_mayor = ft.Row(
        [
            tarjeta_resumen("Bolsas recibidas", total_bolsas, "Bolsas Adulto Mayor"),
            tarjeta_resumen("Adultos mayores", total_adultos_mayores, "Registros"),
        ],
        spacing=16,
        wrap=True,
    )

    filas = []
    for hab in habitantes:
        edad = hab.edad
        if edad is None:
            estado = "No"
            aplica = "No"
            categoria = "Sin fecha"
        else:
            estado = "Si" if edad >= 50 else "No"
            aplica = "Si" if edad >= 60 else "No"
            categoria = "Bolsa Adulto Mayor" if edad >= 60 else "Adulto Mayor sin bolsa" if edad >= 50 else "No aplica"

        badge_beneficio = ft.Container(
            content=ft.Text(
                "APLICA (Bolsa AM)" if aplica == "Si" else "NO APLICA",
                color=COLOR_BLANCO,
                weight=ft.FontWeight.BOLD,
                size=12,
            ),
            bgcolor=COLOR_VERDE if aplica == "Si" else COLOR_GRIS,
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            border_radius=15,
        )

        filas.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(f"{hab.tipo_id}-{hab.cedula}")),
                    ft.DataCell(ft.Text(f"{hab.nombres} {hab.apellidos}")),
                    ft.DataCell(ft.Text(hab.fecha_nacimiento.strftime("%d/%m/%Y") if hab.fecha_nacimiento else "—")),
                    ft.DataCell(ft.Text(str(edad) if edad is not None else "—")),
                    ft.DataCell(ft.Text(estado, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO)),
                    ft.DataCell(badge_beneficio),
                    ft.DataCell(ft.Text(categoria)),
                    ft.DataCell(ft.Text(getattr(hab, "bono", "Ninguno"))),
                ]
            )
        )

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cédula")),
            ft.DataColumn(ft.Text("Nombre y Apellido")),
            ft.DataColumn(ft.Text("Fecha Nacimiento")),
            ft.DataColumn(ft.Text("Edad")),
            ft.DataColumn(ft.Text("¿Adulto Mayor?")),
            ft.DataColumn(ft.Text("Bolsa")),
            ft.DataColumn(ft.Text("Categoría")),
            ft.DataColumn(ft.Text("Bono familiar")),
        ],
        rows=filas,
        border=ft.border.all(1, COLOR_GRIS),
    )

    contenido = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Beneficio Alimentario Especial",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_NEGRO,
                                ),
                                ft.Text(
                                    "Personas de 50 años o más detectadas automáticamente desde el Censo de Familias.",
                                    size=13,
                                    color=COLOR_GRIS,
                                ),
                            ],
                            expand=True,
                        ),
                        ft.OutlinedButton(
                            "Reporte PDF",
                            icon=ft.Icons.PICTURE_AS_PDF,
                            on_click=lambda e: file_picker.save_file(
                                dialog_title="Guardar reporte de adulto mayor",
                                file_name="Reporte_Adulto_Mayor.pdf",
                                allowed_extensions=["pdf"],
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.Text("Resumen general", size=18, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                resumen_adulto_mayor,
                ft.Divider(),
                tabla,
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


def vista_registro_adulto_mayor():
    tipo_id = ft.Dropdown(
        label="Tipo de ID",
        width=120,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula = ft.TextField(label="Cédula", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    nombres = ft.TextField(label="Nombres", width=260)
    apellidos = ft.TextField(label="Apellidos", width=260)
    fecha_nacimiento = ft.TextField(label="Fecha de Nacimiento", width=240, read_only=True)
    edad = ft.TextField(label="Edad", width=120, disabled=True)
    telefono = ft.TextField(label="Teléfono", width=220, keyboard_type=ft.KeyboardType.NUMBER)
    direccion = ft.TextField(label="Dirección", width=520)
    beneficio = ft.Dropdown(
        label="Programa o bono",
        width=280,
        options=[
            ft.dropdown.Option("Bolsa Adulto Mayor"),
            ft.dropdown.Option("Atención gerontológica"),
            ft.dropdown.Option("Ayuda social"),
            ft.dropdown.Option("Ninguno"),
        ],
        value="Atención gerontológica",
    )
    aplica_bono = ft.Dropdown(
        label="¿Aplica bono? (automático)",
        width=220,
        options=[ft.dropdown.Option("Si"), ft.dropdown.Option("No")],
        value="No",
        disabled=True,
    )
    condicion_salud = ft.TextField(label="Condición de salud", width=260)
    observaciones = ft.TextField(label="Observaciones", width=520, multiline=True, min_lines=3)

    def abrir_fecha(e):
        def on_change(ev):
            if isinstance(ev.control.value, datetime):
                dt = ev.control.value
                fecha_nacimiento.value = dt.strftime("%d/%m/%Y")
                edad.value = str(
                    (datetime.now().year - dt.year)
                    - ((datetime.now().month, datetime.now().day) < (dt.month, dt.day))
                )
                edad_calculada = int(edad.value)
                aplica_bono.value = "Si" if edad_calculada >= 60 else "No"
                beneficio.value = "Bolsa Adulto Mayor" if edad_calculada >= 60 else "Atención gerontológica"
                e.page.update()

        e.page.open(
            ft.DatePicker(
                first_date=datetime(1900, 1, 1),
                last_date=datetime.today(),
                on_change=on_change,
            )
        )

    def guardar(e):
        if not nombres.value.strip() or not apellidos.value.strip() or not cedula.value.strip() or not direccion.value.strip():
            e.page.snack_bar = ft.SnackBar(ft.Text("Completa los datos obligatorios del habitante."))
            e.page.snack_bar.open = True
            e.page.update()
            return

        try:
            fecha = datetime.strptime(fecha_nacimiento.value, "%d/%m/%Y").date()
        except Exception:
            e.page.snack_bar = ft.SnackBar(ft.Text("Debes ingresar la fecha de nacimiento válida."))
            e.page.snack_bar.open = True
            e.page.update()
            return

        hoy = datetime.today()
        edad_actual = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))

        if edad_actual < 50:
            e.page.snack_bar = ft.SnackBar(ft.Text("No aplica como adulto mayor: requiere tener 50 años o más."))
            e.page.snack_bar.open = True
            e.page.update()
            return

        es_adulto_mayor = "Si" if edad_actual >= 50 else "No"
        aplica_bolsa = "Si" if edad_actual >= 60 else "No"
        categoria = "Bolsa Adulto Mayor" if edad_actual >= 60 else "Adulto Mayor sin bolsa"
        beneficio_registro = "Bolsa Adulto Mayor" if edad_actual >= 60 else beneficio.value or "Atención gerontológica"

        session = SessionLocal()
        existente = session.query(AdultoMayor).filter(AdultoMayor.cedula == cedula.value.strip()).first()
        if existente:
            session.close()
            e.page.snack_bar = ft.SnackBar(ft.Text("Ya existe un registro con esa cédula."))
            e.page.snack_bar.open = True
            e.page.update()
            return

        nuevo = AdultoMayor(
            nombres=nombres.value.strip(),
            apellidos=apellidos.value.strip(),
            tipo_id=tipo_id.value or "V",
            cedula=cedula.value.strip(),
            fecha_nacimiento=fecha,
            telefono=telefono.value.strip() or None,
            direccion=direccion.value.strip(),
            condicion_salud=condicion_salud.value.strip() or None,
            servicio=beneficio_registro,
            observaciones=observaciones.value.strip() or None,
            es_adulto_mayor=es_adulto_mayor,
            aplica_bolsa=aplica_bolsa,
            categoria=categoria,
        )
        session.add(nuevo)
        session.commit()
        session.close()

        e.page.snack_bar = ft.SnackBar(ft.Text(f"Registro guardado correctamente: {categoria}"))
        e.page.snack_bar.open = True
        e.page.update()
        e.page.go("/adulto_mayor")

    boton_fecha = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color=COLOR_VERDE, on_click=abrir_fecha)
    boton_guardar = ft.ElevatedButton("Guardar", bgcolor=COLOR_VERDE, color=COLOR_BLANCO, on_click=guardar)
    boton_cancelar = ft.TextButton("Cancelar", on_click=lambda e: e.page.go("/adulto_mayor"))

    formulario = ft.Container(
        content=ft.Column(
            [
                ft.Text("Registro automático del Adulto Mayor", size=28, weight="bold", color=COLOR_NEGRO),
                ft.Text("La evaluación se hace automáticamente: desde 50 años es adulto mayor y desde 60 aplica a la bolsa.", size=13, color=COLOR_GRIS),
                ft.Divider(),
                ft.Row([nombres, apellidos], spacing=20),
                ft.Row([tipo_id, cedula], spacing=20),
                ft.Row([fecha_nacimiento, boton_fecha, edad], spacing=10),
                ft.Row([telefono, direccion], spacing=20),
                ft.Row([beneficio, aplica_bono, condicion_salud], spacing=20),
                ft.Row([observaciones], spacing=20),
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
