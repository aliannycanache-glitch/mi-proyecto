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


def vista_panel(page):
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
    usuario_activo = session.query(Usuario).filter(Usuario.id == getattr(page, "session_usuario_id", None)).first()
    session.close()

    saludo = "Bienvenida" if usuario_activo and usuario_activo.sexo == "Mujer" else "Bienvenido"
    nombre_activo = usuario_activo.nombre if usuario_activo else "a la comunidad"

    # Exportar reporte PDF
    def exportar_reporte(e: ft.FilePickerResultEvent):
        if not e.path:
            return
        destino = e.path if e.path.lower().endswith(".pdf") else f"{e.path}.pdf"
        with SessionLocal() as session_reporte:
            familias = session_reporte.query(Familia).options(
                joinedload(Familia.miembros), joinedload(Familia.calle)
            ).all()
            generar_pdf_familias(familias, destino)
        page.snack_bar = ft.SnackBar(ft.Text(f"Reporte PDF guardado en: {destino}"))
        page.snack_bar.open = True
        page.update()

    file_picker_reporte = ft.FilePicker(on_result=exportar_reporte)
    page.overlay.append(file_picker_reporte)

    # Función auxiliar para crear tarjetas estilizadas con icono
    def crear_tarjeta_metrica(titulo, valor, icono, color_icono):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(str(valor), size=30, weight="bold", color=COLOR_NEGRO),
                            ft.Text(titulo, size=13, color=COLOR_GRIS, weight="w500"),
                        ],
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        content=ft.Icon(icono, color=color_icono, size=28),
                        bgcolor="#F3F4F6",
                        padding=10,
                        border_radius=10,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="white",
            padding=18,
            border_radius=14,
            shadow=ft.BoxShadow(blur_radius=10, spread_radius=1, color="#0D000000", offset=ft.Offset(0, 3)),
            expand=True,
        )

    # Tarjetas resumen mejoradas
    tarjetas = ft.Row(
        [
            crear_tarjeta_metrica("Familias registradas", total_familias, ft.Icons.HOME_ROUNDED, "#35b779"),
            crear_tarjeta_metrica("Personas en sector", total_personas, ft.Icons.PEOPLE_ROUNDED, "#3d9bc3"),
            crear_tarjeta_metrica("Cilindros de gas", total_cilindros, ft.Icons.PROPANE_TANK_ROUNDED, "#287f8f"),
            crear_tarjeta_metrica("Adultos mayores", total_adultos_mayores, ft.Icons.ELDERLY_ROUNDED, "#ed7048"),
        ],
        spacing=15,
    )

    # Gráfico resumen
    max_val = max(total_familias, total_personas, total_cilindros, total_adultos_mayores, 1)
    grafico = ft.BarChart(
        bar_groups=[
            ft.BarChartGroup(x=0, bar_rods=[ft.BarChartRod(to_y=total_familias, color="#35b779", width=20, border_radius=6)]),
            ft.BarChartGroup(x=1, bar_rods=[ft.BarChartRod(to_y=total_personas, color="#3d9bc3", width=20, border_radius=6)]),
            ft.BarChartGroup(x=2, bar_rods=[ft.BarChartRod(to_y=total_cilindros, color="#287f8f", width=20, border_radius=6)]),
            ft.BarChartGroup(x=3, bar_rods=[ft.BarChartRod(to_y=total_adultos_mayores, color="#ed7048", width=20, border_radius=6)]),
        ],
        max_y=max_val + (5 if max_val < 20 else 10),
        height=220,
        groups_space=30,
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(value=0, label=ft.Text("Familias", size=11, weight="bold")),
                ft.ChartAxisLabel(value=1, label=ft.Text("Personas", size=11, weight="bold")),
                ft.ChartAxisLabel(value=2, label=ft.Text("Cilindros", size=11, weight="bold")),
                ft.ChartAxisLabel(value=3, label=ft.Text("Adultos", size=11, weight="bold")),
            ],
            labels_size=30,
        ),
    )

    grafico_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.BAR_CHART_ROUNDED, color="#287f8f", size=22),
                        ft.Text("Estadísticas del Sector", size=16, weight="bold", color="#1f2937"),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=1),
                grafico,
            ],
            spacing=12,
        ),
        bgcolor="white",
        padding=20,
        border_radius=14,
        shadow=ft.BoxShadow(blur_radius=10, spread_radius=1, color="#0D000000", offset=ft.Offset(0, 3)),
        expand=2,
    )

    # Panel lateral de accesos rápidos y estado del sistema
    panel_lateral = ft.Container(
        content=ft.Column(
            [
                ft.Text("Acciones Rápidas", size=16, weight="bold", color="#1f2937"),
                ft.Divider(height=1),
                ft.ElevatedButton(
                    text="Añadir Nueva Familia",
                    icon=ft.Icons.GROUP_ADD,
                    bgcolor=COLOR_VERDE,
                    color=COLOR_BLANCO,
                    width=float("inf"),
                    on_click=lambda e: e.page.go("/registro_familia"),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=16),
                ),
                ft.OutlinedButton(
                    text="Exportar Reporte PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    width=float("inf"),
                    on_click=lambda e: file_picker_reporte.save_file(
                        dialog_title="Guardar reporte de familias",
                        file_name="Reporte_Censo_Familiar.pdf",
                        allowed_extensions=["pdf"],
                    ),
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=16),
                ),
                ft.Container(height=10),
                ft.Text("Información de Jornada", size=15, weight="bold", color="#1f2937"),
               ft.Container(
    content=ft.Column(
        [
            ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=16), ft.Text("Base de Datos: Conectada", size=12)]),
            ft.Row([ft.Icon(ft.Icons.PERSON, color="blue", size=16), ft.Text(f"Rol: {usuario_activo.rol if usuario_activo else 'Usuario'}", size=12)]),
        ],
        spacing=8,
    ),
    bgcolor="#F9FAFB",
    padding=12,
    border_radius=8,
)
            ],
            spacing=12,
        ),
        bgcolor="white",
        padding=20,
        border_radius=14,
        shadow=ft.BoxShadow(blur_radius=10, spread_radius=1, color="#0D000000", offset=ft.Offset(0, 3)),
        expand=1,
    )

    # Fila central compuesta (Gráfico + Panel Lateral)
    seccion_central = ft.Row(
        [
            grafico_card,
            panel_lateral,
        ],
        spacing=20,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    # Encabezado del Panel
    encabezado = ft.Row(
        [
            ft.Column(
                [
                    ft.Text(f"{saludo}, {nombre_activo}!", size=26, weight="bold", color=COLOR_NEGRO),
                    ft.Text("Panel general de control e información del sector comunitario.", size=14, color=COLOR_GRIS),
                ],
                spacing=2,
            ),
            ft.Image(
                src="imagenes/Comunidatoslogo.png",
                width=80,
                height=80,
                fit=ft.ImageFit.CONTAIN,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # Contenido general
    contenido = ft.Column(
        [
            encabezado,
            ft.Divider(),
            tarjetas,
            ft.Container(height=10),
            seccion_central,
        ],
        spacing=15,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        content=contenido,
        padding=25,
        expand=True,
    )