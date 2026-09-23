import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO
from modelo import SessionLocal, Usuario   # 👈 Importamos el modelo y la sesión

def vista_login(pagina: ft.Page):
    mensaje_login = ft.Text("", size=12, color=COLOR_ROJO, text_align=ft.TextAlign.CENTER)

    def mostrar_mensaje_login(mensaje):
        mensaje_login.value = mensaje
        if mensaje_login.page:
            mensaje_login.update()

    def mostrar_snackbar(e, mensaje):
        mostrar_mensaje_login(mensaje)
        pagina.snack_bar = ft.SnackBar(ft.Text(mensaje))
        pagina.snack_bar.open = True
        pagina.update()

    mensaje_exito = ft.Text("", color=COLOR_VERDE)
    if hasattr(pagina, "registro_exitoso") and pagina.registro_exitoso:
        mensaje_exito.value = "¡Registro exitoso! Ahora puedes iniciar sesión."
        pagina.registro_exitoso = False

    usuario = ft.TextField(label="Correo o Cédula", width=360)
    clave = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=360)
    mensaje_caps = ft.Text("", size=12, color=COLOR_ROJO)

    def recuperar_contrasena(e):
        identificador = ft.TextField(label="Correo o cédula", width=320)
        pregunta_1 = ft.TextField(label="Pregunta 1", width=320, read_only=True)
        respuesta_1 = ft.TextField(label="Respuesta 1", width=320)
        pregunta_2 = ft.TextField(label="Pregunta 2", width=320, read_only=True)
        respuesta_2 = ft.TextField(label="Respuesta 2", width=320)
        nueva_clave = ft.TextField(label="Nueva contraseña", password=True, width=320)
        confirmar_clave = ft.TextField(label="Confirmar contraseña", password=True, width=320)
        mensaje = ft.Text("", color=COLOR_ROJO, size=12)

        def cargar_preguntas(ev):
            with SessionLocal() as session:
                usuario_recuperacion = session.query(Usuario).filter(
                    (Usuario.correo == identificador.value.strip()) |
                    (Usuario.cedula == identificador.value.strip())
                ).first()
                if usuario_recuperacion:
                    pregunta_1.value = usuario_recuperacion.pregunta1 or "No registrada"
                    pregunta_2.value = usuario_recuperacion.pregunta2 or "No registrada"
                    mensaje.value = "Responde ambas preguntas para continuar."
                else:
                    mensaje.value = "Usuario no encontrado."
            pregunta_1.update()
            pregunta_2.update()
            mensaje.update()

        def cambiar_clave(ev):
            if not identificador.value.strip() or not respuesta_1.value.strip() or not respuesta_2.value.strip() or not nueva_clave.value:
                mensaje.value = "Completa todos los campos de recuperación."
            elif nueva_clave.value != confirmar_clave.value:
                mensaje.value = "Las contraseñas no coinciden."
            else:
                with SessionLocal() as session:
                    usuario_recuperacion = session.query(Usuario).filter(
                        (Usuario.correo == identificador.value.strip()) |
                        (Usuario.cedula == identificador.value.strip())
                    ).first()
                    respuestas_validas = usuario_recuperacion and (
                        (usuario_recuperacion.respuesta1 or "").strip().lower() == respuesta_1.value.strip().lower()
                        and (usuario_recuperacion.respuesta2 or "").strip().lower() == respuesta_2.value.strip().lower()
                    )
                    if not respuestas_validas:
                        mensaje.value = "Las respuestas de seguridad no coinciden."
                    else:
                        usuario_recuperacion.clave_hash = nueva_clave.value
                        usuario_recuperacion.intentos_fallidos = 0
                        usuario_recuperacion.bloqueado = 0
                        session.commit()
                        pagina.close_dialog()
                        mostrar_snackbar(ev, "Contraseña actualizada correctamente")
                        return
            mensaje.update()

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Recuperar contraseña"),
            content=ft.Column([
                identificador,
                ft.ElevatedButton("Buscar preguntas", on_click=cargar_preguntas),
                pregunta_1, respuesta_1, pregunta_2, respuesta_2,
                nueva_clave, confirmar_clave, mensaje,
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: pagina.close_dialog()),
                ft.ElevatedButton("Cambiar contraseña", on_click=cambiar_clave),
            ],
        )
        pagina.dialog = dialogo
        dialogo.open = True
        pagina.update()

    def iniciar_sesion(e):
        if not usuario.value.strip() or not clave.value.strip():
            mostrar_snackbar(e, "Por favor completa todos los campos")
            return

        session = SessionLocal()
        usr = session.query(Usuario).filter(
            (Usuario.correo == usuario.value.strip()) | (Usuario.cedula == usuario.value.strip())
        ).first()

        if usr is None:
            session.close()
            mostrar_snackbar(e, "Usuario o contraseña incorrecta")
        elif usr.bloqueado:
            session.close()
            mostrar_snackbar(e, "Usuario bloqueado. Usa Recuperar contraseña.")
        elif usr.clave_hash != clave.value:  # 👈 CORREGIDO: Cambiado de usr.clave a usr.clave_hash
            usr.intentos_fallidos += 1
            intentos_restantes = max(0, 3 - usr.intentos_fallidos)
            if usr.intentos_fallidos >= 3:
                usr.bloqueado = 1
                mensaje = "Usuario o contraseña incorrecta. Usuario bloqueado después de 3 intentos."
            else:
                mensaje = f"Usuario o contraseña incorrecta. Te quedan {intentos_restantes} intento(s)."
            session.commit()
            session.close()
            mostrar_snackbar(e, mensaje)
        else:
            usuario_id = usr.id
            usr.intentos_fallidos = 0
            session.commit()
            session.close()
            # Guardar id en la sesión y redirigir al panel principal
            pagina.session_usuario_id = usuario_id
            pagina.go("/panel")

    boton_login = ft.ElevatedButton(
        "Iniciar sesión",
        width=200,
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        on_click=iniciar_sesion
    )

    enlace_registro = ft.TextButton(
        content=ft.Text("Regístrate", weight="bold", color=COLOR_VERDE),
        on_click=lambda e: pagina.go("/registro_usuario")
    )

    enlace_recuperar = ft.TextButton(
        "Recuperar contraseña",
        on_click=recuperar_contrasena,
    )

    columna_derecha = ft.Column(
        controls=[
            mensaje_exito,
            ft.Image(src="imagenes/ComuniDatoslogo.png", width=140, height=56),
            ft.Container(height=8),
            ft.Text("Bienvenido", size=24, weight="bold", color=COLOR_NEGRO),
            ft.Text("Inicia sesión para acceder a tu cuenta.", size=14, color=COLOR_GRIS, text_align=ft.TextAlign.CENTER),
            ft.Container(height=12),
            ft.Container(content=usuario, width=360),
            ft.Container(content=clave, width=360),
            ft.Container(content=mensaje_caps),
            ft.Container(content=mensaje_login, width=360),
            ft.Container(height=6),
            ft.Row([boton_login], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=6),
            ft.Row([
                ft.Text("¿No tienes cuenta?", size=12, color=COLOR_GRIS),
                enlace_registro
            ], alignment=ft.MainAxisAlignment.CENTER),
            enlace_recuperar,
            ft.Container(height=8),
            ft.Text("v1.2", size=12, color="#9aa0a6")
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    tarjeta_visual = ft.Container(
        width=360,
        bgcolor=COLOR_BLANCO,
        content=ft.Image(
            src="imagenes/ComuniDatos.png",
            fit=ft.ImageFit.COVER,
            repeat=ft.ImageRepeat.NO_REPEAT
        ),
        padding=0,
        border_radius=ft.border_radius.all(8)
    )

    contenedor_principal = ft.Container(
        content=ft.Row(
            controls=[
                tarjeta_visual,
                ft.Container(
                    content=columna_derecha,
                    alignment=ft.alignment.center,
                    padding=40
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True
        ),
        bgcolor=COLOR_BLANCO,
        border_radius=ft.border_radius.all(12),
        padding=20,
        alignment=ft.alignment.center,
        height=920
    )

    return contenedor_principal