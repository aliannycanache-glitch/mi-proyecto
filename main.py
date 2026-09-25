import flet as ft
import datetime
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO

# Importación de vistas
from vistas.login import vista_login
from vistas.registro import vista_registro
from vistas.panel_principal import vista_panel
from vistas.censo_familias import vista_familia, vista_registro_familia
from vistas.censo_gas import vista_gas, vista_registro_gas
from vistas.carta_residencia import vista_residencia
from vistas.calles import vista_calles, vista_registro_calles
from vistas.perfil import vista_perfil
from vistas.adulto_mayor import vista_adulto_mayor, vista_registro_adulto_mayor
from vistas.proteccion_integral import vista_proteccion_integral, vista_registro_proteccion_integral

def main(pagina: ft.Page):
    print("[DEBUG] main() iniciado")
    pagina.title = "ComuniDatos"
    pagina.theme_mode = "light"
    pagina.bgcolor = "#cae6fbbe"
    pagina.padding = 0
    pagina.window.maximized = True

    def fondo_de_aplicacion(contenido):
        return ft.Stack(
            controls=[
                ft.Container(
                    content=ft.Image(
                        src="imagenes/Comunidatoslogo.png",
                        fit=ft.ImageFit.CONTAIN,
                        opacity=0.35,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                ),
                ft.Container(
                    content=contenido,
                    expand=True,
                ),
            ],
            expand=True,
        )

    def contenedor_de_vista(contenido):
        return ft.Container(
            content=fondo_de_aplicacion(contenido),
            alignment=ft.alignment.center,
            padding=18,
            margin=0.03,
            border_radius=28,
            expand=True,
            bgcolor="#d4e7f6f0",
        )

    rutas = {
        "Panel Principal": "/panel",
        "Censo de Familia": "/familia",
        "Registro de Familia": "/registro_familia",
        "Censo de Gas": "/gas",
        "Registro de Gas": "/registro_gas",
        "Carta de Residencia": "/residencia",
        "Calles": "/calles",
        "Registro de Calle": "/registro_calle",
        "Atención del Adulto Mayor": "/adulto_mayor",
        "Registro de Adulto Mayor": "/registro_adulto_mayor",
        "Gestión de Protección Integral": "/proteccion_integral",
        "Registro de Protección Integral": "/registro_proteccion_integral",
        "Perfil": "/perfil",
        "Registro de Usuario": "/registro_usuario",
        "Cerrar Sesión": "/login"
    }

    destinos_interactivos = [
        "Panel Principal",
        "Censo de Familia",
        "Censo de Gas",
        "Carta de Residencia",
        "Calles",
        "Atención del Adulto Mayor",
        "Gestión de Protección Integral",
        "Perfil",
        "Cerrar Sesión"
    ]

    pagina.drawer = ft.NavigationDrawer(
        bgcolor="#d6ebfbdc",
        elevation=2,
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Text("ComuniDatos", size=22, weight="bold", color=COLOR_VERDE),
                    ft.Text("Gestión comunitaria", size=12, color=COLOR_GRIS),
                ], spacing=2),
                padding=ft.padding.only(left=18, top=20, right=18, bottom=10),
                bgcolor="#eaf6ff5a",
            ),
            ft.NavigationDrawerDestination(icon=ft.Icons.DASHBOARD, label="Panel Principal"),
            ft.NavigationDrawerDestination(icon=ft.Icons.GROUP, label="Censo de Familia"),
            ft.NavigationDrawerDestination(icon=ft.Icons.GAS_METER, label="Censo de Gas"),
            ft.NavigationDrawerDestination(icon=ft.Icons.HOME, label="Carta de Residencia"),
            ft.NavigationDrawerDestination(icon=ft.Icons.MAP, label="Calles"),
            ft.NavigationDrawerDestination(icon=ft.Icons.ELDERLY, label="Atención del Adulto Mayor"),
            ft.NavigationDrawerDestination(icon=ft.Icons.SHIELD, label="Gestión de Protección Integral"),
            ft.Divider(),
            ft.NavigationDrawerDestination(icon=ft.Icons.PERSON, label="Perfil"),
            ft.NavigationDrawerDestination(icon=ft.Icons.LOGOUT_OUTLINED, label="Cerrar Sesión")
        ]
    )

    def construir_contenido(ruta):
        if ruta == "/login":
            return vista_login(pagina)
        elif ruta == "/registro_usuario":
            return vista_registro()
        elif ruta == "/panel":
            return vista_panel(pagina)
        elif ruta.startswith("/registro_familia"):
            import urllib.parse
            parsed = urllib.parse.urlparse(ruta)
            params = urllib.parse.parse_qs(parsed.query)
            edit_id = int(params.get("edit", [None])[0]) if "edit" in params else None
            return vista_registro_familia(pagina, edit_id)
        elif ruta == "/registro_gas":
            return vista_registro_gas()
        elif ruta == "/residencia":
            return vista_residencia(pagina)
        elif ruta.startswith("/calles"):
            return vista_calles()
        elif ruta.startswith("/registro_calle"):
            import urllib.parse
            parsed = urllib.parse.urlparse(ruta)
            params = urllib.parse.parse_qs(parsed.query)
            edit_index = int(params.get("edit", [None])[0]) if "edit" in params else None
            return vista_registro_calles(edit_index)
        elif ruta == "/adulto_mayor":
            return vista_adulto_mayor(pagina)
        elif ruta == "/registro_adulto_mayor":
            return vista_registro_adulto_mayor()
        elif ruta == "/proteccion_integral":
            return vista_proteccion_integral(pagina)
        elif ruta == "/registro_proteccion_integral":
            return vista_registro_proteccion_integral()
        elif ruta == "/perfil":
            if hasattr(pagina, "session_usuario_id"):
                return vista_perfil(pagina.session_usuario_id)
            else:
                return ft.Text("⚠️ No hay usuario en sesión", size=20, color=COLOR_ROJO)
        else:
            return ft.Text("❌ Página no encontrada", size=30)

    def construir_vista(ruta):
        mostrar_navegacion = ruta not in ["/login", "/registro_usuario"]

        # 1. Agregamos "/registro_proteccion_integral" a las rutas con formato de diccionario
        rutas_con_diccionario = [
            "/familia",
            "/gas",
            "/adulto_mayor",
            "/proteccion_integral",
            "/registro_proteccion_integral"
        ]

        if ruta in rutas_con_diccionario:
            if ruta == "/familia":
                resultado = vista_familia(pagina)
            elif ruta == "/gas":
                resultado = vista_gas(pagina)
            elif ruta == "/adulto_mayor":
                resultado = vista_adulto_mayor(pagina)
            elif ruta == "/proteccion_integral":
                resultado = vista_proteccion_integral(pagina)
            elif ruta == "/registro_proteccion_integral":
                resultado = vista_registro_proteccion_integral(pagina)

            # Validamos si la vista devolvió un diccionario o el Container directamente
            if isinstance(resultado, dict):
                vista = resultado.get("vista")
                actualizar = resultado.get("actualizar")
            else:
                vista = resultado
                actualizar = None

            return ft.View(
                route=ruta,
                appbar=ft.AppBar(
                    title=ft.Text("ComuniDatos", color=COLOR_BLANCO),
                    bgcolor=COLOR_VERDE,
                    center_title=True,
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.HOME,
                            tooltip="Inicio",
                            on_click=lambda e: pagina.go("/panel")
                        )
                    ],
                ) if mostrar_navegacion else None,
                controls=[contenedor_de_vista(vista)],
                drawer=pagina.drawer if mostrar_navegacion else None,
                padding=0,
            ), actualizar

        else:
            contenido = construir_contenido(ruta)
            return ft.View(
                route=ruta,
                appbar=ft.AppBar(
                    title=ft.Text("ComuniDatos", color=COLOR_BLANCO),
                    bgcolor=COLOR_VERDE,
                    center_title=True,
                ) if mostrar_navegacion else None,
                controls=[
                    contenedor_de_vista(
                        ft.Column(
                            [contenido],
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        )
                    )
                ],
                drawer=pagina.drawer if mostrar_navegacion else None,
                padding=0,
            ), None

    def cambio_ruta(e):
        pagina.views.clear()
        nueva_vista, actualizar = construir_vista(pagina.route)
        pagina.views.append(nueva_vista)
        pagina.update()

        if actualizar:
            actualizar()

    def cambio_menu(e):
        destino_label = destinos_interactivos[e.control.selected_index]
        pagina.go(rutas.get(destino_label, "/panel"))

    pagina.on_route_change = cambio_ruta
    pagina.drawer.on_change = cambio_menu

    pagina.go("/login")

if __name__ == "__main__":
    ft.app(target=main)
