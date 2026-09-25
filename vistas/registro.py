import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
import datetime
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO
from modelo import SessionLocal, Usuario   # 👈 Modelo y sesión de SQLAlchemy

def vista_registro():
    # Campos de fecha y edad
    fecha_nacimiento = ft.TextField(label="Fecha de nacimiento", width=250, dense=True, read_only=True)
    edad = ft.TextField(label="Edad", width=80, dense=True, read_only=True)

    def abrir_fecha_nacimiento(e):
        def on_change(ev: ft.ControlEvent):
            if isinstance(ev.control.value, datetime.datetime):
                dt = ev.control.value
                fecha_str = dt.strftime("%Y-%m-%d")
                fecha_nacimiento.value = fecha_str
                hoy = datetime.date.today()
                edad_calc = hoy.year - dt.year - ((hoy.month, hoy.day) < (dt.month, dt.day))
                edad.value = str(edad_calc)
                e.page.update()

        e.page.open(
            ft.DatePicker(
                first_date=datetime.datetime(1900, 1, 1),
                last_date=datetime.datetime.today(),
                on_change=on_change,
            )
        )

    boton_fecha = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color=COLOR_VERDE, on_click=abrir_fecha_nacimiento)

    # Campos del formulario
    nombre = ft.TextField(label="Nombre", width=250, dense=True)
    apellido = ft.TextField(label="Apellido", width=250, dense=True)
    correo = ft.TextField(label="Correo Electrónico", width=250, dense=True)
    telefono = ft.TextField(label="Teléfono", width=250, dense=True)
    tipo_id = ft.Dropdown(
        label="Tipo de ID",
        width=250,
        dense=True,
        content_padding=8,
        options=[
            ft.dropdown.Option("V"),
            ft.dropdown.Option("E"),
        ]
    )
    cedula = ft.TextField(label="Cédula", width=250, dense=True)
    sexo = ft.Dropdown(
        label="Sexo",
        width=150,
        dense=True,
        options=[ft.dropdown.Option("Hombre"), ft.dropdown.Option("Mujer"), ft.dropdown.Option("Otro")],
    )
    rol = ft.Dropdown(
        label="Rol",
        width=250,
        dense=True,
        options=[
            ft.dropdown.Option("Líder Político"),
            ft.dropdown.Option("Encargado de Gas")
        ]
    )
    clave = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=250, dense=True)
    confirmar_clave = ft.TextField(label="Confirmar Contraseña", password=True, can_reveal_password=True, width=250, dense=True)
    pregunta1 = ft.TextField(label="Pregunta de seguridad 1", width=250, dense=True)
    respuesta1 = ft.TextField(label="Respuesta 1", width=250, dense=True)
    pregunta2 = ft.TextField(label="Pregunta de seguridad 2", width=250, dense=True)
    respuesta2 = ft.TextField(label="Respuesta 2", width=250, dense=True)

    mensaje_error = ft.Text("", size=12, color=COLOR_ROJO, text_align=ft.TextAlign.CENTER)

    # Función para crear cuenta y guardar en BD
    def crear_cuenta(e):
        # Validación general del formulario
        campos = [
            nombre, apellido, correo, telefono, fecha_nacimiento, tipo_id,
            cedula, rol, clave, confirmar_clave, pregunta1, respuesta1,
            pregunta2, respuesta2
        ]
        if any((not getattr(c, "value", "").strip()) for c in campos if getattr(c, "value", None) is not None):
            e.page.snack_bar = ft.SnackBar(ft.Text("Por favor completa todos los campos"))
            e.page.snack_bar.open = True
            e.page.update()
            return
        elif clave.value != confirmar_clave.value:
            mensaje_error.value = "Las contraseñas no coinciden"
            e.page.update()
            return
        else:
            session = SessionLocal()
            try:
                if not fecha_nacimiento.value:
                    raise ValueError("Debes ingresar la fecha de nacimiento")

                fecha_nac = datetime.datetime.strptime(fecha_nacimiento.value, "%Y-%m-%d").date()

                nuevo_usuario = Usuario(
                    nombre=nombre.value,
                    apellido=apellido.value,
                    correo=correo.value,
                    telefono=telefono.value,
                    tipo_id=tipo_id.value or "V",
                    cedula=cedula.value,
                    rol=rol.value,
                    sexo=sexo.value or "No especificado",
                    fecha_nacimiento=fecha_nac,
                    clave_hash=clave.value,
                    pregunta1=pregunta1.value if 'pregunta1' in locals() else pregunta1.value,
                    respuesta1=respuesta1.value,
                    pregunta2=pregunta2.value if 'pregunta2' in locals() else pregunta2.value,
                    respuesta2=respuesta2.value,
                )
                session.add(nuevo_usuario)
                session.commit()
                usuario_id = nuevo_usuario.id
                session.close()

                e.page.session_usuario_id = usuario_id
                e.page.registro_exitoso = True
                e.page.go("/login")
            except Exception as err:
                session.rollback()
                session.close()
                mensaje_error.value = f"Error al guardar: {err}"
                e.page.update()

    boton_registro = ft.ElevatedButton(
        "Registrarse",
        width=200,
        bgcolor=COLOR_VERDE,
        color=COLOR_BLANCO,
        on_click=crear_cuenta
    )

    enlace_login = ft.TextButton(
        content=ft.Text("Inicia sesión", weight="bold", color=COLOR_VERDE),
        on_click=lambda e: e.page.go("/login")
    )

    # Columna derecha (formulario con scroll vertical)
    columna_derecha = ft.Column(
        controls=[
            ft.Image(src="imagenes/ComuniDatoslogo.png", width=140, height=56),
            ft.Container(height=8),
            ft.Text("Registro de Administradores", size=24, weight="bold", color=COLOR_NEGRO),
            ft.Text("Crea una cuenta para empezar a gestionar tu comunidad.", size=14, color=COLOR_GRIS, text_align=ft.TextAlign.CENTER),
            ft.Container(height=12),
            ft.Row([nombre, apellido], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([correo, telefono], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                ft.Container(content=boton_fecha, alignment=ft.alignment.top_left, width=40),
                ft.Container(content=fecha_nacimiento, width=190),
                ft.Container(content=edad, width=80)
            ], spacing=20, alignment=ft.MainAxisAlignment.START, width=520),
            ft.Row([tipo_id, cedula, sexo], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([rol], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([clave, confirmar_clave], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(content=ft.Divider(), width=600, alignment=ft.alignment.center),
            ft.Text("Preguntas de seguridad (elige y responde)", size=14, weight="bold", color=COLOR_NEGRO),
            ft.Row([pregunta1, respuesta1], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([pregunta2, respuesta2], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(content=mensaje_error),
            ft.Container(height=6),
            ft.Row([boton_registro], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=6),
            ft.Row([
                ft.Text("¿Ya tienes cuenta?", size=12, color=COLOR_GRIS),
                enlace_login
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=8),
            ft.Text("v1.6", size=12, color=COLOR_GRIS)
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO
    )

    # Imagen lateral
    tarjeta_visual = ft.Container(
        width=360,
        bgcolor=COLOR_BLANCO,
        content=ft.Image(
            src="imagenes/ComuniDatos.png",
            fit=ft.ImageFit.COVER,
            repeat=ft.ImageRepeat.NO_REPEAT
        ),
        padding=0,
        border_radius=ft.border_radius.all(8),
        margin=ft.margin.only(left=300)
    )

    # Contenedor principal
    contenedor_principal = ft.Container(
        content=ft.Row(
            controls=[
                tarjeta_visual,
                ft.Container(content=columna_derecha, alignment=ft.alignment.center, padding=40, expand=True)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True
        ),
        bgcolor=COLOR_BLANCO,
        border_radius=ft.border_radius.all(12),
        padding=20,
        alignment=ft.alignment.center,
        height=920,
        expand=True
    )

    return contenedor_principal