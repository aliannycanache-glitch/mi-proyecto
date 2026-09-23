import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from sqlalchemy.orm import joinedload
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO
from modelo import SessionLocal, Familia, Miembro, RegistroGas, Usuario
from generador_reportes import generar_pdf_familias

def vista_panel(pagina):
    # ✅ Consultar totales desde la BD
    session = SessionLocal()
    familias = session.query(Familia).all()
    total_familias = len(familias)
    total_miembros = session.query(Miembro).count()
    total_personas = total_familias + total_miembros
    total_adultos_mayores = 0
    for familia in familias:
        edades = [familia.edad_jefe] + [miembro.edad for miembro in familia.miembros]
        total_adultos_mayores += sum(1 for edad in edades if edad is not None and edad >= 50)

    registros_gas = session.query(RegistroGas).all()
    total_cilindros = sum(r.kg10 + r.kg18 + r.kg27 + r.kg43 for r in registros_gas)
    usuario_activo = session.query(Usuario).filter(Usuario.id == getattr(pagina, "session_usuario_id", None)).first()
    session.close()
    saludo = "Bienvenida" if usuario_activo and usuario_activo.sexo == "Mujer" else "Bienvenido"
    nombre_activo = usuario_activo.nombre if usuario_activo else "a la comunidad"

    def exportar_reporte(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        destino = e.path if e.path.lower().endswith(".pdf") else f"{e.path}.pdf"
        with SessionLocal() as session_reporte:
            familias = session_reporte.query(Familia).options(
                joinedload(Familia.miembros), joinedload(Familia.calle)
            ).all()
            generar_pdf_familias(familias, destino)
        pagina.snack_bar = ft.SnackBar(ft.Text(f"Reporte PDF guardado en: {destino}"))
        pagina.snack_bar.open = True
        pagina.update()

    file_picker_reporte = ft.FilePicker(on_result=exportar_reporte)
    pagina.overlay.append(file_picker_reporte)

    # Tarjetas resumen
    tarjetas = ft.Row([
        ft.Container(
            content=ft.Column([
                ft.Text(str(total_familias), size=32, weight="bold", color=COLOR_NEGRO),
                ft.Text("Familias registradas", size=16, color=COLOR_GRIS)
            ], spacing=6),
            bgcolor="#eaf6ffcc",
            padding=20,
            border_radius=12,
            width=280
        ),
        ft.Container(
            content=ft.Column([
                ft.Text(str(total_personas), size=32, weight="bold", color=COLOR_NEGRO),
                ft.Text("Personas en el sector", size=16, color=COLOR_GRIS)
            ], spacing=6),
            bgcolor="#eaf6ffcc",
            padding=20,
            border_radius=12,
            width=280
        ),
        ft.Container(
            content=ft.Column([
                ft.Text(str(total_cilindros), size=32, weight="bold", color=COLOR_NEGRO),
                ft.Text("Cilindros en el sector", size=16, color=COLOR_GRIS)
            ], spacing=6),
            bgcolor="#eaf6ffcc",
            padding=20,
            border_radius=12,
            width=280
        ),
        ft.Container(
            content=ft.Column([
                ft.Text(str(total_adultos_mayores), size=32, weight="bold", color=COLOR_NEGRO),
                ft.Text("Adultos mayores", size=16, color=COLOR_GRIS)
            ], spacing=6),
            bgcolor="#eaf6ffcc",
            padding=20,
            border_radius=12,
            width=280
        )
    ], spacing=30, alignment=ft.MainAxisAlignment.CENTER)

    # Gráfico resumen
    grafico = ft.BarChart(
        bar_groups=[
            ft.BarChartGroup(x=0, bar_rods=[ft.BarChartRod(to_y=total_familias, color="#35b779", width=30, tooltip="Familias")]),
            ft.BarChartGroup(x=1, bar_rods=[ft.BarChartRod(to_y=total_personas, color="#3d9bc3", width=30, tooltip="Personas")]),
            ft.BarChartGroup(x=2, bar_rods=[ft.BarChartRod(to_y=total_cilindros, color="#287f8f", width=30, tooltip="Cilindros")]),
            ft.BarChartGroup(x=3, bar_rods=[ft.BarChartRod(to_y=total_adultos_mayores, color="#ed7048", width=30, tooltip="Adultos mayores")]),
        ],
        expand=True,
        max_y=max(total_familias, total_personas, total_cilindros, total_adultos_mayores) + 5,
        height=250,
        width=760,
        groups_space=48,
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(value=0, label=ft.Text("Familias", size=12)),
                ft.ChartAxisLabel(value=1, label=ft.Text("Personas", size=12)),
                ft.ChartAxisLabel(value=2, label=ft.Text("Cilindros", size=12)),
                ft.ChartAxisLabel(value=3, label=ft.Text("Adultos mayores", size=12)),
            ],
            labels_size=42,
        )
    )

    grafico_card = ft.Container(
        content=ft.Column([
            ft.Text("Gráfico de resumen", size=18, weight="bold", color=COLOR_NEGRO),
            grafico,
        ], spacing=10),
        bgcolor="#eaf6ffcc",
        padding=20,
        border_radius=12,
        border=ft.border.all(1, COLOR_GRIS),
        alignment=ft.alignment.center
    )

    # Botones de acción
    botones = ft.Row([
        ft.ElevatedButton(
            text="Añadir Familia",
            icon=ft.Icons.GROUP_ADD,
            bgcolor=COLOR_VERDE,
            color=COLOR_BLANCO,
            on_click=lambda e: e.page.go("/registro_familia"),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), padding=20)
        ),
        ft.ElevatedButton(
            text="Crear Reporte",
            icon=ft.Icons.DESCRIPTION,
            bgcolor=COLOR_VERDE,
            color=COLOR_BLANCO,
            on_click=lambda e: file_picker_reporte.save_file(
                dialog_title="Guardar reporte de familias",
                file_name="Reporte_Censo_Familiar.pdf",
                allowed_extensions=["pdf"],
            ),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), padding=20)
        )
    ], spacing=30, alignment=ft.MainAxisAlignment.CENTER)

    # Logo
    logo = ft.Container(
        content=ft.Image(src="imagenes/Comunidatoslogo.png", width=180, height=180, fit=ft.ImageFit.CONTAIN),
        alignment=ft.alignment.center,
        width=200
    )

    # Contenido principal
    contenido = ft.Column([
        ft.Text(f"{saludo}, {nombre_activo}!", size=26, weight="bold", color=COLOR_NEGRO),
        ft.Divider(),
        ft.Text("Resumen del Sector", size=20, weight="bold", color=COLOR_NEGRO),
        tarjetas,
        ft.Container(height=20),
        grafico_card,
        ft.Container(height=20),
        botones,
    ], spacing=20, expand=True)

    return ft.Row([
        logo,
        ft.Container(content=contenido, expand=True, alignment=ft.alignment.center)
    ], expand=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
