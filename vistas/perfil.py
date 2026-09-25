import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft
from colores import COLOR_VERDE, COLOR_GRIS, COLOR_BLANCO, COLOR_NEGRO, COLOR_ROJO
from datetime import datetime
from modelo import SessionLocal, Usuario 

# Validadores
def validar_telefono(e):
    campo = e.control
    valor = "".join(ch for ch in campo.value if ch.isdigit())
    if len(valor) > 11:
        valor = valor[:11]
    campo.value = valor
    e.page.update()

def validar_cedula(e):
    campo = e.control
    valor = "".join(ch for ch in campo.value if ch.isdigit())
    campo.value = valor
    e.page.update()

def calcular_edad(e, campo_fecha, campo_edad):
    try:
        fecha = datetime.strptime(campo_fecha.value, "%d/%m/%Y")
        hoy = datetime.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        campo_edad.value = str(edad)
    except:
        campo_edad.value = ""
    e.page.update()

def vista_perfil(usuario_id):
    # Obtener datos del usuario desde la BD
    session = SessionLocal()
    usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
    session.close()

    # Campos cargados desde BD, bloqueados inicialmente
    campo_nombre = ft.TextField(label="Nombre", value=usuario.nombre, dense=True, read_only=True)
    campo_apellido = ft.TextField(label="Apellido", value=usuario.apellido, dense=True, read_only=True)
    campo_correo = ft.TextField(label="Correo Electrónico", value=usuario.correo, dense=True, read_only=True)
    campo_telefono = ft.TextField(label="Teléfono", value=usuario.telefono, on_change=validar_telefono, dense=True, read_only=True)
    campo_fecha = ft.TextField(
        label="Fecha de Nacimiento",
        value=usuario.fecha_nacimiento.strftime("%d/%m/%Y") if usuario.fecha_nacimiento else "",
        hint_text="dd/mm/aaaa",
        width=180,
        dense=True,
        read_only=True
    )
    campo_edad = ft.TextField(label="Edad", value=str(usuario.edad), read_only=True, dense=True)
    campo_fecha.on_change = lambda e: calcular_edad(e, campo_fecha, campo_edad)

    campo_tipo_id = ft.Dropdown(
        label="Tipo de ID",
        width=180,
        dense=True,
        content_padding=8,
        value=usuario.tipo_id,
        options=[ft.dropdown.Option("V"), ft.dropdown.Option("E")],
    )
    campo_tipo_id.disabled = True  # bloqueado

    campo_sexo = ft.Dropdown(
        label="Sexo",
        width=150,
        dense=True,
        value=usuario.sexo or "No especificado",
        options=[ft.dropdown.Option("Hombre"), ft.dropdown.Option("Mujer"), ft.dropdown.Option("Otro")],
        disabled=True,
    )

    campo_cedula = ft.TextField(label="Número de Cédula", value=usuario.cedula, on_change=validar_cedula, dense=True, read_only=True)
    campo_rol = ft.TextField(label="Rol", value=usuario.rol, read_only=True, dense=True, width=250)

    # Preguntas de seguridad
    pregunta1 = ft.TextField(label="Pregunta 1", value=usuario.pregunta1, dense=True, read_only=True)
    respuesta1 = ft.TextField(label="Respuesta 1", value=usuario.respuesta1, dense=True, read_only=True)
    pregunta2 = ft.TextField(label="Pregunta 2", value=usuario.pregunta2, dense=True, read_only=True)
    respuesta2 = ft.TextField(label="Respuesta 2", value=usuario.respuesta2, dense=True, read_only=True)

    # Contraseña (solo para cambiar)
    campo_pass = ft.TextField(label="Nueva Contraseña", password=True, can_reveal_password=True, dense=True, disabled=True)
    campo_confirmar = ft.TextField(label="Confirmar Nueva Contraseña", password=True, can_reveal_password=True, dense=True, disabled=True)

    # Función para habilitar edición
    def habilitar_edicion(e):
        for campo in [
            campo_nombre, campo_apellido, campo_correo, campo_telefono,
            campo_fecha, campo_tipo_id, campo_cedula,
            campo_sexo,
            pregunta1, respuesta1, pregunta2, respuesta2
        ]:
            if isinstance(campo, ft.Dropdown):
                campo.disabled = False
            else:
                campo.read_only = False
            campo.update()
        campo_pass.disabled = False
        campo_confirmar.disabled = False
        campo_pass.update()
        campo_confirmar.update()

    # Función para guardar cambios en BD
    def guardar_cambios(e):
        if campo_pass.value and campo_pass.value != campo_confirmar.value:
            e.page.snack_bar = ft.SnackBar(ft.Text("Las contraseñas no coinciden"))
            e.page.snack_bar.open = True
            e.page.update()
            return

        session = SessionLocal()
        usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
        usuario.nombre = campo_nombre.value
        usuario.apellido = campo_apellido.value
        usuario.correo = campo_correo.value
        usuario.telefono = campo_telefono.value
        usuario.tipo_id = campo_tipo_id.value
        usuario.sexo = campo_sexo.value or "No especificado"
        usuario.cedula = campo_cedula.value
        usuario.rol = campo_rol.value
        try:
            usuario.fecha_nacimiento = datetime.strptime(campo_fecha.value, "%d/%m/%Y").date()
        except:
            usuario.fecha_nacimiento = None
        usuario.pregunta1 = pregunta1.value
        usuario.respuesta1 = respuesta1.value
        usuario.pregunta2 = pregunta2.value
        usuario.respuesta2 = respuesta2.value
        if campo_pass.value:
            usuario.clave_hash = campo_pass.value
        session.commit()
        session.close()

        e.page.snack_bar = ft.SnackBar(ft.Text("Perfil actualizado correctamente"))
        e.page.snack_bar.open = True
        for campo in [
            campo_nombre, campo_apellido, campo_correo, campo_telefono,
            campo_fecha, campo_tipo_id, campo_cedula, campo_sexo,
            pregunta1, respuesta1, pregunta2, respuesta2,
        ]:
            if isinstance(campo, ft.Dropdown):
                campo.disabled = True
            else:
                campo.read_only = True
            campo.update()
        campo_pass.value = ""
        campo_confirmar.value = ""
        campo_pass.disabled = True
        campo_confirmar.disabled = True
        campo_pass.update()
        campo_confirmar.update()
        e.page.update()

    # Botones
    botones = ft.Row([
        ft.TextButton("Editar", style=ft.ButtonStyle(color=COLOR_NEGRO), on_click=habilitar_edicion),
        ft.ElevatedButton("Guardar Cambios", bgcolor=COLOR_VERDE, color=COLOR_BLANCO, on_click=guardar_cambios),
    ], alignment=ft.MainAxisAlignment.END)

    # Distribución visual
    layout = ft.Column([
        ft.Text("Mi Perfil", size=30, weight=ft.FontWeight.BOLD),
        ft.Divider(),

        ft.Row([campo_nombre, campo_apellido], spacing=20),
        ft.Row([campo_correo, campo_telefono], spacing=20),
        ft.Row([campo_fecha, campo_edad, campo_tipo_id, campo_cedula, campo_sexo], spacing=20),
        campo_rol,

        ft.Divider(),
        ft.Text("Preguntas de Seguridad", size=18, weight=ft.FontWeight.BOLD),
        ft.Row([pregunta1, respuesta1], spacing=20),
        ft.Row([pregunta2, respuesta2], spacing=20),

        ft.Divider(),
        ft.Text("Cambiar Contraseña", size=18, weight=ft.FontWeight.BOLD),
        ft.Row([campo_pass, campo_confirmar], spacing=20),

        botones
    ], spacing=15)

    return ft.Container(
        content=layout,
        padding=20,
        bgcolor=COLOR_BLANCO,
        border_radius=10,
        expand=True
    )
