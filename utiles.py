import flet as ft
import datetime

def abrir_datepicker_fecha_nacimiento(e, campo_fecha: ft.TextField, campo_edad: ft.TextField,
                                      formato="%Y-%m-%d", fecha_minima=datetime.datetime(1900, 1, 1)):
    def on_change(ev: ft.ControlEvent):
        if isinstance(ev.control.value, datetime.datetime):
            dt = ev.control.value
            campo_fecha.value = dt.strftime(formato)
            hoy = datetime.date.today()
            edad = hoy.year - dt.year - ((hoy.month, hoy.day) < (dt.month, dt.day))
            campo_edad.value = str(edad)
            e.page.update()

    e.page.open(
        ft.DatePicker(
            first_date=fecha_minima,
            last_date=datetime.datetime.today(),
            on_change=on_change
        )
    )

def abrir_datepicker_solo_fecha(e, campo_fecha: ft.TextField,
                                formato="%Y-%m-%d", fecha_minima=datetime.datetime(1900, 1, 1)):
    def on_change(ev: ft.ControlEvent):
        if isinstance(ev.control.value, datetime.datetime):
            campo_fecha.value = ev.control.value.strftime(formato)
            e.page.update()

    e.page.open(
        ft.DatePicker(
            first_date=fecha_minima,
            last_date=datetime.datetime.today(),
            on_change=on_change
        )
    )

def validar_cedula(e: ft.ControlEvent, campo_cedula: ft.TextField):
    """
    Valida una cédula con formato 00.000.000.
    - Solo permite dígitos.
    - Debe tener entre 7 y 8 dígitos.
    - Formatea con puntos de miles.
    """
    valor = campo_cedula.value.replace(".", "").strip()
    if len(valor) > 8:
        valor = valor[:8]
    if not valor.isdigit():
        campo_cedula.error_text = "Solo se permiten dígitos"
    elif len(valor) < 7 or len(valor) > 8:
        campo_cedula.error_text = "Debe tener entre 7 y 8 dígitos"
    else:
        campo_cedula.error_text = None
        valor_formateado = f"{int(valor):,}".replace(",", ".")
        campo_cedula.value = valor_formateado
    e.page.update()


def validar_telefono(e: ft.ControlEvent, campo_telefono: ft.TextField):
    """
    Valida un teléfono con formato 0000-000-0000.
    - Solo permite dígitos.
    - Debe tener exactamente 11 dígitos.
    - Formatea con guiones.
    """
    valor = "".join(ch for ch in campo_telefono.value if ch.isdigit())
    if len(valor) > 11:
        valor = valor[:11]
    if not valor.isdigit():
        campo_telefono.error_text = "Solo se permiten dígitos"
    elif len(valor) != 11:
        campo_telefono.error_text = "Debe tener exactamente 11 dígitos"
    else:
        campo_telefono.error_text = None
        valor_formateado = f"{valor[0:4]}-{valor[4:7]}-{valor[7:]}"
        campo_telefono.value = valor_formateado
    e.page.update()

# Lista de dominios permitidos
DOMINIOS_VALIDOS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com"
]

def validar_correo(e: ft.ControlEvent, campo_correo: ft.TextField):
    """
    Valida un correo electrónico:
    - Debe tener formato usuario@dominio
    - Solo acepta dominios comunes: Gmail, Yahoo, Outlook, Hotmail
    """
    valor = campo_correo.value.strip().lower()

    if "@" not in valor:
        campo_correo.error_text = "Debe contener @"
    else:
        usuario, _, dominio = valor.partition("@")
        if not usuario or dominio not in DOMINIOS_VALIDOS:
            campo_correo.error_text = (
                "Correo inválido. Usa dominios: gmail.com, yahoo.com, outlook.com, hotmail.com"
            )
        else:
            campo_correo.error_text = None

    e.page.update()