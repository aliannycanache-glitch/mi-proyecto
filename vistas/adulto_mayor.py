import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import joinedload
from modelo import Familia, SessionLocal, AdultoMayor
from generador_reportes import generar_pdf_adultos_mayores

# ==========================================
# PALETA DE COLORES PASTEL
# ==========================================
PASTEL_VERDE_PRIMARIO = "#2E7D32"  # Verde selva suave para textos e iconos principales
PASTEL_VERDE_FONDO = "#E8F5E9"     # Fondo verde menta pastel para badges/tarjetas
PASTEL_VERDE_ACCENTO = "#A8E6CF"   # Menta pastel brillante
PASTEL_AMARILLO_FONDO = "#FFF9C4"  # Amarillo pastel muy claro
PASTEL_AMARILLO_TEXTO = "#F57F17"  # Texto ámbar cálido
PASTEL_GRIS_FONDO = "#F4F6F8"      # Gris perla claro para superficies
PASTEL_GRIS_BORDER = "#E0E6ED"     # Borde sutil
PASTEL_GRIS_TEXTO = "#78909C"      # Gris azulado para subtítulos
COLOR_BLANCO = "#FFFFFF"
COLOR_NEGRO = "#263238"


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
        pagina.open(ft.SnackBar(ft.Text(f"✅ Reporte guardado con éxito en: {destino}")))

    file_picker = ft.FilePicker(on_result=exportar_pdf)
    pagina.overlay.append(file_picker)

    habitantes = obtener_padron()
    total_adultos_mayores = len(habitantes)
    total_bolsas = sum(1 for habitante in habitantes if habitante.categoria == "Bolsa Adulto Mayor")

    # 📌 Tarjetas de resumen pastel estilizadas
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
            width=260,
        )

    resumen_adulto_mayor = ft.Row(
        [
            tarjeta_resumen(
                "Bolsas asignadas", 
                total_bolsas, 
                "Beneficio Adulto Mayor (60+)", 
                ft.Icons.SHOPPING_BAG, 
                PASTEL_VERDE_FONDO, 
                PASTEL_VERDE_PRIMARIO
            ),
            tarjeta_resumen(
                "Total detectados", 
                total_adultos_mayores, 
                "Adultos mayores en censo (50+)", 
                ft.Icons.SUPERVISED_USER_CIRCLE, 
                "#E1F5FE", 
                "#0288D1"
            ),
        ],
        spacing=16,
        wrap=True,
    )

    # 📌 Generación de filas para la tabla
    filas = []
    for hab in habitantes:
        edad = hab.edad
        aplica = "Si" if edad is not None and edad >= 60 else "No"
        categoria = "Bolsa Adulto Mayor" if edad is not None and edad >= 60 else "Adulto Mayor sin bolsa"

        # Badge pastel personalizado
        if aplica == "Si":
            badge_bg = PASTEL_VERDE_FONDO
            badge_fg = PASTEL_VERDE_PRIMARIO
            texto_badge = "APLICA (Bolsa AM)"
            icono_badge = ft.Icons.CHECK_CIRCLE
        else:
            badge_bg = PASTEL_AMARILLO_FONDO
            badge_fg = PASTEL_AMARILLO_TEXTO
            texto_badge = "NO APLICA"
            icono_badge = ft.Icons.INFO

        badge_beneficio = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icono_badge, size=14, color=badge_fg),
                    ft.Text(texto_badge, color=badge_fg, weight=ft.FontWeight.BOLD, size=11),
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor=badge_bg,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
            border_radius=20,
            border=ft.border.all(1, badge_fg),
        )

        filas.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(f"{hab.tipo_id}-{hab.cedula}", weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(f"{hab.nombres} {hab.apellidos}", weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Text(hab.fecha_nacimiento.strftime("%d/%m/%Y") if hab.fecha_nacimiento else "—")),
                    ft.DataCell(ft.Text(str(edad) if edad is not None else "—")),
                    ft.DataCell(ft.Text("Sí", weight=ft.FontWeight.BOLD, color=PASTEL_VERDE_PRIMARIO)),
                    ft.DataCell(badge_beneficio),
                    ft.DataCell(ft.Text(categoria, size=12)),
                    ft.DataCell(ft.Text(getattr(hab, "bono", "Ninguno"), size=12)),
                ]
            )
        )

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Cédula", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("Nombre y Apellido", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("Fecha Nacimiento", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("Edad", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("¿Adulto Mayor?", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("Bolsa", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("Categoría", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
            ft.DataColumn(ft.Text("Bono familiar", weight=ft.FontWeight.BOLD, color=PASTEL_GRIS_TEXTO)),
        ],
        rows=filas,
        heading_row_color="#F0F7F4",
        divider_thickness=1,
        horizontal_margin=15,
        column_spacing=20,
    )

    tabla_contenedor = ft.Container(
        content=ft.Column([tabla], scroll=ft.ScrollMode.AUTO),
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
                                ft.Text(
                                    "Beneficio Alimentario Especial",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_NEGRO,
                                ),
                                ft.Text(
                                    "Personas de 50 años o más detectadas automáticamente desde el Censo de Familias.",
                                    size=13,
                                    color=PASTEL_GRIS_TEXTO,
                                ),
                            ],
                            expand=True,
                        ),
                        ft.ElevatedButton(
                            "Reporte PDF",
                            icon=ft.Icons.PICTURE_AS_PDF,
                            bgcolor=PASTEL_VERDE_PRIMARIO,
                            color=COLOR_BLANCO,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                            ),
                            on_click=lambda e: file_picker.save_file(
                                dialog_title="Guardar reporte de adulto mayor",
                                file_name="Reporte_Adulto_Mayor.pdf",
                                allowed_extensions=["pdf"],
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color=PASTEL_GRIS_BORDER, height=20),
                ft.Text("Resumen general", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                resumen_adulto_mayor,
                ft.Divider(color=PASTEL_GRIS_BORDER, height=20),
                ft.Text("Padron de Habitantes Detectados", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
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


def vista_registro_adulto_mayor():
    tipo_id = ft.Dropdown(
        label="Tipo ID",
        width=100,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    cedula = ft.TextField(label="Cédula", width=180, keyboard_type=ft.KeyboardType.NUMBER)
    nombres = ft.TextField(label="Nombres", width=250)
    apellidos = ft.TextField(label="Apellidos", width=250)
    fecha_nacimiento = ft.TextField(label="Fecha de Nacimiento", width=200, read_only=True)
    edad = ft.TextField(label="Edad", width=90, disabled=True)
    telefono = ft.TextField(label="Teléfono", width=220, keyboard_type=ft.KeyboardType.NUMBER)
    direccion = ft.TextField(label="Dirección", width=510)
    beneficio = ft.Dropdown(
        label="Programa o bono",
        width=260,
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
    condicion_salud = ft.TextField(label="Condición de salud", width=250)
    observaciones = ft.TextField(label="Observaciones", width=510, multiline=True, min_lines=3)

    def abrir_fecha(e):
        def on_change(ev):
            if isinstance(ev.control.value, datetime):
                dt = ev.control.value
                fecha_nacimiento.value = dt.strftime("%d/%m/%Y")
                calculo_edad = (datetime.now().year - dt.year) - ((datetime.now().month, datetime.now().day) < (dt.month, dt.day))
                edad.value = str(calculo_edad)
                aplica_bono.value = "Si" if calculo_edad >= 60 else "No"
                beneficio.value = "Bolsa Adulto Mayor" if calculo_edad >= 60 else "Atención gerontológica"
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
            e.page.open(ft.SnackBar(ft.Text(" Completa los datos obligatorios del habitante.")))
            return

        try:
            fecha = datetime.strptime(fecha_nacimiento.value, "%d/%m/%Y").date()
        except Exception:
            e.page.open(ft.SnackBar(ft.Text(" Debes ingresar una fecha de nacimiento válida.")))
            return

        hoy = datetime.today()
        edad_actual = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))

        if edad_actual < 50:
            e.page.open(ft.SnackBar(ft.Text(" No aplica como adulto mayor: requiere tener 50 años o más.")))
            return

        es_adulto_mayor = "Si" if edad_actual >= 50 else "No"
        aplica_bolsa = "Si" if edad_actual >= 60 else "No"
        categoria = "Bolsa Adulto Mayor" if edad_actual >= 60 else "Adulto Mayor sin bolsa"
        beneficio_registro = "Bolsa Adulto Mayor" if edad_actual >= 60 else beneficio.value or "Atención gerontológica"

        session = SessionLocal()
        existente = session.query(AdultoMayor).filter(AdultoMayor.cedula == cedula.value.strip()).first()
        if existente:
            session.close()
            e.page.open(ft.SnackBar(ft.Text(" Ya existe un registro con esa cédula.")))
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

        e.page.open(ft.SnackBar(ft.Text(f"✅ Registro guardado correctamente: {categoria}")))
        e.page.go("/adulto_mayor")

    boton_fecha = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        icon_color=PASTEL_VERDE_PRIMARIO,
        tooltip="Seleccionar fecha de nacimiento",
        on_click=abrir_fecha,
    )
    boton_guardar = ft.ElevatedButton(
        "Guardar Registro",
        bgcolor=PASTEL_VERDE_PRIMARIO,
        color=COLOR_BLANCO,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
        ),
        on_click=guardar,
    )
    boton_cancelar = ft.OutlinedButton("Cancelar", on_click=lambda e: e.page.go("/adulto_mayor"))

    tarjeta_datos_personales = ft.Container(
        content=ft.Column(
            [
                ft.Text("Información Personal", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Divider(height=10, color=PASTEL_GRIS_BORDER),
                ft.Row([nombres, apellidos], wrap=True, spacing=15),
                ft.Row([tipo_id, cedula, telefono], wrap=True, spacing=15),
                ft.Row([fecha_nacimiento, boton_fecha, edad], wrap=True, spacing=10),
                ft.Row([direccion], wrap=True, spacing=15),
            ],
            spacing=12,
        ),
        padding=20,
        bgcolor=COLOR_BLANCO,
        border_radius=12,
        border=ft.border.all(1, PASTEL_GRIS_BORDER),
    )

    tarjeta_evaluacion = ft.Container(
        content=ft.Column(
            [
                ft.Text("Evaluación y Programa", size=16, weight=ft.FontWeight.BOLD, color=COLOR_NEGRO),
                ft.Divider(height=10, color=PASTEL_GRIS_BORDER),
                ft.Row([beneficio, aplica_bono], wrap=True, spacing=15),
                ft.Row([condicion_salud], wrap=True, spacing=15),
                ft.Row([observaciones], wrap=True, spacing=15),
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
                ft.Text("Registro de Adulto Mayor", size=24, weight="bold", color=COLOR_NEGRO),
                ft.Text(
                    "La evaluación se realiza automáticamente: desde 50 años se registra como adulto mayor y desde 60 años aplica a la Bolsa de Alimentación.",
                    size=13,
                    color=PASTEL_GRIS_TEXTO,
                ),
                ft.Divider(color=PASTEL_GRIS_BORDER, height=20),
                tarjeta_datos_personales,
                tarjeta_evaluacion,
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

    return formulario
