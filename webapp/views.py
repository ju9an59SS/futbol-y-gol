from datetime import datetime, timedelta
from functools import wraps
import mimetypes
import secrets

import openpyxl
import resend

from django.conf import settings
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.utils.crypto import get_random_string

from .forms import (
    RegistroAdministradorForm,
    RegistroClienteForm,
)
from .models import (
    EstadoAcceso,
    PerfilAdministrador,
    PerfilCliente,
    Reservas,
)


# =========================================================
# CONFIGURACIÓN RESEND
# =========================================================

resend.api_key = settings.RESEND_API_KEY

TOKEN_EXPIRACION_MINUTOS = 10
MAX_INTENTOS_TOKEN = 5


# =========================================================
# CONTRASEÑA TEMPORAL
# =========================================================

def generar_password_temporal():

    while True:

        password = get_random_string(
            12,
            allowed_chars=(
                "ABCDEFGHJKLMNPQRSTUVWXYZ"
                "abcdefghijkmnopqrstuvwxyz"
                "23456789@#$%"
            ),
        )

        try:
            validate_password(password)
            return password

        except ValidationError:
            continue


# =========================================================
# CAMBIO OBLIGATORIO DE CONTRASEÑA
# =========================================================

def marcar_cambio_password(
    usuario,
    requerido=True,
):

    estado, _ = EstadoAcceso.objects.get_or_create(
        usuario=usuario
    )

    estado.debe_cambiar_password = requerido

    estado.save(
        update_fields=[
            "debe_cambiar_password"
        ]
    )


def requiere_cambio_password(usuario):

    if not usuario.is_authenticated:
        return False

    estado, _ = EstadoAcceso.objects.get_or_create(
        usuario=usuario
    )

    return estado.debe_cambiar_password


def cambio_password_obligatorio(view_func):

    @wraps(view_func)
    def wrapper(
        request,
        *args,
        **kwargs,
    ):

        if requiere_cambio_password(
            request.user
        ):
            return redirect(
                "cambiar_password_inicial"
            )

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper


# =========================================================
# VALIDAR COMPROBANTE
# =========================================================

def validar_comprobante(archivo):

    if not archivo:
        return

    tipos_permitidos = [
        "image/jpeg",
        "image/png",
        "image/webp",
    ]

    if archivo.content_type not in tipos_permitidos:

        raise ValidationError(
            "El comprobante debe ser JPG, PNG o WEBP."
        )

    if archivo.size > (5 * 1024 * 1024):

        raise ValidationError(
            "El comprobante no puede superar 5 MB."
        )


# =========================================================
# INICIO
# =========================================================

def index(request):

    return render(
        request,
        "index.html",
    )


# =========================================================
# REGISTRAR CLIENTE
# =========================================================

def registrar_cliente(request):

    if request.user.is_authenticated:

        if requiere_cambio_password(
            request.user
        ):
            return redirect(
                "cambiar_password_inicial"
            )

        if (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return redirect(
                "reservas"
            )

        return redirect(
            "perfil_cliente"
        )

    if request.method == "POST":

        form = RegistroClienteForm(
            request.POST
        )

        if form.is_valid():

            password_temporal = (
                generar_password_temporal()
            )

            usuario = form.save(
                commit=False
            )

            usuario.first_name = (
                form.cleaned_data[
                    "first_name"
                ]
            )

            usuario.last_name = (
                form.cleaned_data[
                    "last_name"
                ]
            )

            usuario.email = (
                form.cleaned_data[
                    "email"
                ]
            )

            usuario.is_staff = False
            usuario.is_superuser = False
            usuario.is_active = True

            usuario.set_password(
                password_temporal
            )

            usuario.save()

            PerfilCliente.objects.create(
                usuario=usuario,
                tipo_documento=(
                    form.cleaned_data[
                        "tipo_documento"
                    ]
                ),
                documento=(
                    form.cleaned_data[
                        "documento"
                    ]
                ),
                celular=(
                    form.cleaned_data[
                        "celular"
                    ]
                ),
            )

            marcar_cambio_password(
                usuario,
                True,
            )

            request.session[
                "usuario_creado"
            ] = usuario.username

            request.session[
                "password_temporal"
            ] = password_temporal

            return redirect(
                "registro_cliente_exitoso"
            )

    else:

        form = RegistroClienteForm()

    return render(
        request,
        "registro_cliente.html",
        {
            "form": form,
        },
    )


# =========================================================
# REGISTRO CLIENTE EXITOSO
# =========================================================

def registro_cliente_exitoso(request):

    usuario = request.session.pop(
        "usuario_creado",
        None,
    )

    password_temporal = request.session.pop(
        "password_temporal",
        None,
    )

    if (
        not usuario
        or not password_temporal
    ):
        return redirect(
            "login_cliente"
        )

    return render(
        request,
        "registro_cliente_exitoso.html",
        {
            "usuario": usuario,
            "password_temporal": (
                password_temporal
            ),
        },
    )


# =========================================================
# LOGIN CLIENTE
# =========================================================

def login_cliente(request):

    mensaje = ""

    if (
        request.user.is_authenticated
        and not request.user.is_staff
        and not request.user.is_superuser
    ):

        if requiere_cambio_password(
            request.user
        ):
            return redirect(
                "cambiar_password_inicial"
            )

        return redirect(
            "perfil_cliente"
        )

    if request.method == "POST":

        usuario = request.POST.get(
            "usuario",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        if not usuario or not password:

            mensaje = (
                "Debe ingresar usuario y contraseña."
            )

        else:

            user = authenticate(
                request,
                username=usuario,
                password=password,
            )

            if (
                user is not None
                and not user.is_staff
                and not user.is_superuser
            ):

                auth_login(
                    request,
                    user,
                )

                if requiere_cambio_password(
                    user
                ):
                    return redirect(
                        "cambiar_password_inicial"
                    )

                return redirect(
                    "perfil_cliente"
                )

            mensaje = (
                "Usuario o contraseña incorrectos."
            )

    return render(
        request,
        "login_cliente.html",
        {
            "mensaje": mensaje,
        },
    )


# =========================================================
# LOGOUT CLIENTE
# =========================================================

def logout_cliente(request):

    auth_logout(request)

    return redirect(
        "login_cliente"
    )


# =========================================================
# CAMBIO INICIAL DE CONTRASEÑA
# =========================================================

@login_required
def cambiar_password_inicial(request):

    if not requiere_cambio_password(
        request.user
    ):

        if (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return redirect(
                "reservas"
            )

        return redirect(
            "perfil_cliente"
        )

    mensaje = ""

    if request.method == "POST":

        password1 = request.POST.get(
            "password1",
            "",
        )

        password2 = request.POST.get(
            "password2",
            "",
        )

        if not password1 or not password2:

            mensaje = (
                "Debe diligenciar ambos campos."
            )

        elif password1 != password2:

            mensaje = (
                "Las contraseñas no coinciden."
            )

        else:

            try:

                validate_password(
                    password1,
                    user=request.user,
                )

            except ValidationError as exc:

                mensaje = " ".join(
                    exc.messages
                )

            else:

                username = (
                    request.user.username
                )

                es_admin = (
                    request.user.is_staff
                    or request.user.is_superuser
                )

                request.user.set_password(
                    password1
                )

                request.user.save(
                    update_fields=[
                        "password"
                    ]
                )

                marcar_cambio_password(
                    request.user,
                    False,
                )

                user = authenticate(
                    request,
                    username=username,
                    password=password1,
                )

                if user is not None:

                    auth_login(
                        request,
                        user,
                    )

                if es_admin:

                    return redirect(
                        "reservas"
                    )

                return redirect(
                    "perfil_cliente"
                )

    return render(
        request,
        "cambiar_password_inicial.html",
        {
            "mensaje": mensaje,
        },
    )


# =========================================================
# PERFIL CLIENTE
# =========================================================

@login_required(
    login_url="login_cliente"
)
@cambio_password_obligatorio
def perfil_cliente(request):

    if (
        request.user.is_staff
        or request.user.is_superuser
    ):
        return redirect(
            "reservas"
        )

    perfil = get_object_or_404(
        PerfilCliente,
        usuario=request.user,
    )

    total_reservas = (
        Reservas.objects.filter(
            cliente=request.user
        ).count()
    )

    return render(
        request,
        "perfil_cliente.html",
        {
            "perfil": perfil,
            "total_reservas": (
                total_reservas
            ),
        },
    )


# =========================================================
# MIS RESERVAS
# =========================================================

@login_required(
    login_url="login_cliente"
)
@cambio_password_obligatorio
def mis_reservas(request):

    if (
        request.user.is_staff
        or request.user.is_superuser
    ):
        return redirect(
            "reservas"
        )

    mensaje = ""
    tipo_mensaje = ""

    if request.method == "POST":

        accion = request.POST.get(
            "accion",
            "",
        )

        if accion == "subir_comprobante":

            reserva_id = request.POST.get(
                "reserva_id"
            )

            reserva = get_object_or_404(
                Reservas,
                id=reserva_id,
                cliente=request.user,
            )

            comprobante = (
                request.FILES.get(
                    "comprobante_pago"
                )
            )

            if not comprobante:

                mensaje = (
                    "Debe seleccionar un comprobante."
                )

                tipo_mensaje = "error"

            else:

                try:

                    validar_comprobante(
                        comprobante
                    )

                except ValidationError as exc:

                    mensaje = " ".join(
                        exc.messages
                    )

                    tipo_mensaje = "error"

                else:

                    reserva.comprobante_pago = (
                        comprobante
                    )

                    reserva.pago = False

                    reserva.save(
                        update_fields=[
                            "comprobante_pago",
                            "pago",
                        ]
                    )

                    mensaje = (
                        "Comprobante cargado correctamente. "
                        "Queda pendiente de validación."
                    )

                    tipo_mensaje = "exito"

    reservas_lista = (
        Reservas.objects.filter(
            cliente=request.user
        )
        .order_by(
            "-fecha",
            "-hora",
        )
    )

    return render(
        request,
        "mis_reservas.html",
        {
            "reservas": reservas_lista,
            "mensaje": mensaje,
            "tipo_mensaje": tipo_mensaje,
        },
    )


# =========================================================
# ESTADO DE RESERVAS
# =========================================================

@login_required(
    login_url="login_cliente"
)
def estado_reservas_cliente(request):

    if (
        request.user.is_staff
        or request.user.is_superuser
    ):

        return JsonResponse(
            {
                "error": "No autorizado"
            },
            status=403,
        )

    reservas = (
        Reservas.objects.filter(
            cliente=request.user
        )
        .values(
            "id",
            "pago",
        )
    )

    return JsonResponse(
        {
            "reservas": list(
                reservas
            )
        }
    )


# =========================================================
# VER COMPROBANTE
# =========================================================

@login_required
def ver_comprobante(
    request,
    reserva_id,
):

    reserva = get_object_or_404(
        Reservas,
        id=reserva_id,
    )

    es_admin = (
        request.user.is_staff
        or request.user.is_superuser
    )

    es_propietario = (
        reserva.cliente_id
        == request.user.id
    )

    if not (
        es_admin
        or es_propietario
    ):

        raise Http404

    if not reserva.comprobante_pago:

        raise Http404

    archivo = (
        reserva.comprobante_pago
    )

    content_type, _ = (
        mimetypes.guess_type(
            archivo.name
        )
    )

    return FileResponse(
        archivo.open("rb"),
        content_type=(
            content_type
            or "application/octet-stream"
        ),
    )


# =========================================================
# RESERVAR
# =========================================================

@login_required(
    login_url="login_cliente"
)
@cambio_password_obligatorio
def reservar(request):

    if (
        request.user.is_staff
        or request.user.is_superuser
    ):
        return redirect(
            "reservas"
        )

    perfil = get_object_or_404(
        PerfilCliente,
        usuario=request.user,
    )

    datos_cliente = {

        "nombre_cliente":
            request.user.first_name,

        "apellido_cliente":
            request.user.last_name,

        "tipo_documento_cliente":
            perfil.tipo_documento,

        "documento_cliente":
            perfil.documento,

        "cel_cliente":
            perfil.celular,
    }

    if request.method == "POST":

        cancha = request.POST.get(
            "cancha",
            "",
        ).strip()

        fecha = request.POST.get(
            "fecha",
            "",
        ).strip()

        hora = request.POST.get(
            "hora",
            "",
        ).strip()

        duracion = request.POST.get(
            "duracion",
            "",
        ).strip()

        comprobante = (
            request.FILES.get(
                "comprobante_pago"
            )
        )

        contexto = {
            **datos_cliente,
            "mensaje": "",
            "tipo_mensaje": "error",
        }

        if not all([
            cancha,
            fecha,
            hora,
            duracion,
        ]):

            contexto["mensaje"] = (
                "Debe completar todos los campos obligatorios."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )

        if duracion not in [
            "1",
            "2",
        ]:

            contexto["mensaje"] = (
                "La duración debe ser de 1 o 2 horas."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )

        if comprobante:

            try:

                validar_comprobante(
                    comprobante
                )

            except ValidationError as exc:

                contexto["mensaje"] = (
                    " ".join(
                        exc.messages
                    )
                )

                return render(
                    request,
                    "reservar.html",
                    contexto,
                )

        duracion = int(
            duracion
        )

        try:

            inicio_nueva = (
                datetime.strptime(
                    f"{fecha} {hora}",
                    "%Y-%m-%d %H:%M",
                )
            )

        except ValueError:

            contexto["mensaje"] = (
                "La fecha o la hora no es válida."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )

        ahora = (
            timezone.localtime()
            .replace(
                tzinfo=None
            )
        )

        if inicio_nueva < ahora:

            contexto["mensaje"] = (
                "No puede reservar una fecha "
                "u hora anterior a la actual."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )

        fin_nueva = (
            inicio_nueva
            + timedelta(
                hours=duracion
            )
        )

        reservas_dia = (
            Reservas.objects.filter(
                cancha=cancha,
                fecha=fecha,
            )
        )

        for existente in reservas_dia:

            inicio_existente = (
                datetime.combine(
                    existente.fecha,
                    existente.hora,
                )
            )

            fin_existente = (
                inicio_existente
                + timedelta(
                    hours=(
                        existente.duracion
                    )
                )
            )

            if (
                inicio_nueva
                < fin_existente
                and fin_nueva
                > inicio_existente
            ):

                contexto["mensaje"] = (
                    "La cancha ya está reservada "
                    "en ese horario."
                )

                return render(
                    request,
                    "reservar.html",
                    contexto,
                )

        Reservas.objects.create(
            cliente=request.user,
            nombre=(
                request.user.first_name
            ),
            apellido=(
                request.user.last_name
            ),
            tipo_documento=(
                perfil.tipo_documento
            ),
            documento=(
                perfil.documento
            ),
            cancha=cancha,
            fecha=fecha,
            hora=hora,
            duracion=duracion,
            cel=perfil.celular,
            comprobante_pago=(
                comprobante
            ),
            pago=False,
        )

        return redirect(
            "mis_reservas"
        )

    return render(
        request,
        "reservar.html",
        datos_cliente,
    )


# =========================================================
# LOGIN ADMINISTRADOR
# =========================================================

def login(request):

    mensaje = ""

    if (
        request.user.is_authenticated
        and (
            request.user.is_staff
            or request.user.is_superuser
        )
    ):

        if requiere_cambio_password(
            request.user
        ):
            return redirect(
                "cambiar_password_inicial"
            )

        return redirect(
            "reservas"
        )

    if request.method == "POST":

        usuario = request.POST.get(
            "usuario",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        if not usuario or not password:

            mensaje = (
                "Debe ingresar usuario y contraseña."
            )

        else:

            user = authenticate(
                request,
                username=usuario,
                password=password,
            )

            if (
                user is not None
                and (
                    user.is_staff
                    or user.is_superuser
                )
            ):

                auth_login(
                    request,
                    user,
                )

                if requiere_cambio_password(
                    user
                ):
                    return redirect(
                        "cambiar_password_inicial"
                    )

                return redirect(
                    "reservas"
                )

            mensaje = (
                "Usuario o contraseña "
                "administrativa incorrectos."
            )

    return render(
        request,
        "login.html",
        {
            "mensaje": mensaje,
        },
    )


# =========================================================
# LOGOUT ADMIN
# =========================================================

def logout(request):

    auth_logout(request)

    return redirect(
        "login"
    )


# =========================================================
# REGISTRAR ADMINISTRADOR
# PÚBLICO DESDE LOGIN ADMIN
# =========================================================

def registrar_administrador(request):

    # Si un cliente normal ya inició sesión,
    # no debe crear administradores.
    if request.user.is_authenticated:

        if (
            not request.user.is_staff
            and not request.user.is_superuser
        ):

            return redirect(
                "perfil_cliente"
            )

    if request.method == "POST":

        form = RegistroAdministradorForm(
            request.POST
        )

        if form.is_valid():

            password_temporal = (
                generar_password_temporal()
            )

            usuario = form.save(
                commit=False
            )

            usuario.first_name = (
                form.cleaned_data[
                    "first_name"
                ]
            )

            usuario.last_name = (
                form.cleaned_data[
                    "last_name"
                ]
            )

            usuario.email = (
                form.cleaned_data[
                    "email"
                ]
            )

            usuario.is_staff = True
            usuario.is_superuser = False
            usuario.is_active = True

            usuario.set_password(
                password_temporal
            )

            usuario.save()

            PerfilAdministrador.objects.create(
                usuario=usuario,
                tipo_documento=(
                    form.cleaned_data[
                        "tipo_documento"
                    ]
                ),
                documento=(
                    form.cleaned_data[
                        "documento"
                    ]
                ),
                celular=(
                    form.cleaned_data[
                        "celular"
                    ]
                ),
            )

            marcar_cambio_password(
                usuario,
                True,
            )

            return render(
                request,
                "registro_administrador_exitoso.html",
                {
                    "usuario":
                        usuario.username,

                    "password_temporal":
                        password_temporal,
                },
            )

    else:

        form = (
            RegistroAdministradorForm()
        )

    return render(
        request,
        "registro_administrador.html",
        {
            "form": form,
        },
    )


# =========================================================
# ADMINISTRAR RESERVAS
# =========================================================

@login_required(
    login_url="login"
)
@cambio_password_obligatorio
def reservas(request):

    if not (
        request.user.is_staff
        or request.user.is_superuser
    ):

        return redirect(
            "login"
        )

    mensaje = ""

    if request.method == "POST":

        accion = request.POST.get(
            "accion",
            "",
        )

        if accion == "actualizar_pago":

            reserva_id = request.POST.get(
                "reserva_id"
            )

            reserva = get_object_or_404(
                Reservas,
                id=reserva_id,
            )

            reserva.pago = (
                request.POST.get(
                    "pago"
                )
                == "on"
            )

            reserva.save(
                update_fields=[
                    "pago"
                ]
            )

            mensaje = (
                f"Reserva #{reserva.id} "
                f"actualizada correctamente."
            )

    reservas_lista = (
        Reservas.objects.all()
        .select_related(
            "cliente"
        )
        .order_by(
            "-fecha",
            "-hora",
        )
    )

    return render(
        request,
        "reservas.html",
        {
            "reservas":
                reservas_lista,

            "admin_usuario":
                request.user.username,

            "mensaje":
                mensaje,
        },
    )


# =========================================================
# GENERAR TOKEN
# =========================================================

def generar_token_recuperacion():

    return str(
        secrets.randbelow(
            900000
        )
        + 100000
    )


# =========================================================
# LIMPIAR SESIÓN DE RECUPERACIÓN
# =========================================================

def limpiar_recuperacion_session(
    request
):

    claves = [
        "recuperacion_usuario_id",
        "recuperacion_tipo",
        "recuperacion_token_hash",
        "recuperacion_expira",
        "recuperacion_intentos",
        "recuperacion_token_validado",
    ]

    for clave in claves:

        request.session.pop(
            clave,
            None,
        )

    request.session.modified = True


# =========================================================
# GUARDAR TOKEN EN SESIÓN
# =========================================================

def guardar_recuperacion(
    request,
    usuario,
    tipo,
    token,
):

    expiracion = (
        timezone.now()
        + timedelta(
            minutes=(
                TOKEN_EXPIRACION_MINUTOS
            )
        )
    )

    request.session[
        "recuperacion_usuario_id"
    ] = usuario.id

    request.session[
        "recuperacion_tipo"
    ] = tipo

    request.session[
        "recuperacion_token_hash"
    ] = make_password(
        token
    )

    request.session[
        "recuperacion_expira"
    ] = expiracion.timestamp()

    request.session[
        "recuperacion_intentos"
    ] = 0

    request.session[
        "recuperacion_token_validado"
    ] = False

    request.session.modified = True


# =========================================================
# TOKEN VIGENTE
# =========================================================

def token_vigente(request):

    valor = request.session.get(
        "recuperacion_expira"
    )

    if not valor:
        return False

    try:
        valor = float(valor)

    except (
        TypeError,
        ValueError,
    ):
        return False

    return (
        timezone.now().timestamp()
        <= valor
    )


# =========================================================
# ENVIAR TOKEN RESEND
# =========================================================

def enviar_token_resend(
    usuario,
    token,
    tipo,
):

    if not settings.RESEND_API_KEY:

        raise RuntimeError(
            "RESEND_API_KEY no está configurada."
        )

    tipo_cuenta = (
        "administrador"
        if tipo == "admin"
        else "cliente"
    )

    nombre = (
        usuario.first_name
        or usuario.username
    )

    html = f"""
    <div style="
        font-family: Arial, sans-serif;
        max-width: 600px;
        margin: auto;
        padding: 30px;
    ">

        <h2>Futbol y Gol</h2>

        <p>
            Hola <strong>{nombre}</strong>.
        </p>

        <p>
            Recibimos una solicitud para
            recuperar tu cuenta de
            {tipo_cuenta}.
        </p>

        <p>
            Tu código es:
        </p>

        <div style="
            font-size: 34px;
            font-weight: bold;
            letter-spacing: 8px;
            padding: 20px;
            background: #eeeeee;
            text-align: center;
        ">
            {token}
        </div>

        <p>
            Este código vence en
            {TOKEN_EXPIRACION_MINUTOS}
            minutos.
        </p>

    </div>
    """

    return resend.Emails.send({

        "from":
            settings.RESEND_FROM_EMAIL,

        "to": [
            usuario.email
        ],

        "subject":
            "Código de recuperación "
            "- Futbol y Gol",

        "html":
            html,
    })


# =========================================================
# RECUPERAR CONTRASEÑA
# =========================================================

def recuperar_password(
    request,
    tipo="cliente",
):

    tipo = (
        "admin"
        if tipo == "admin"
        else "cliente"
    )

    mensaje = ""

    if request.method == "POST":

        username = request.POST.get(
            "usuario",
            "",
        ).strip()

        correo = request.POST.get(
            "correo",
            "",
        ).strip().lower()

        if not username or not correo:

            mensaje = (
                "Debe ingresar usuario "
                "y correo electrónico."
            )

        else:

            usuario = (
                User.objects.filter(
                    username__iexact=username,
                    email__iexact=correo,
                    is_active=True,
                )
                .first()
            )

            usuario_valido = False

            if usuario:

                if tipo == "admin":

                    usuario_valido = (
                        usuario.is_staff
                        or usuario.is_superuser
                    )

                else:

                    usuario_valido = (
                        not usuario.is_staff
                        and not usuario.is_superuser
                    )

            if not usuario_valido:

                mensaje = (
                    "El usuario y el correo "
                    "no corresponden a una cuenta válida."
                )

            else:

                token = (
                    generar_token_recuperacion()
                )

                limpiar_recuperacion_session(
                    request
                )

                guardar_recuperacion(
                    request,
                    usuario,
                    tipo,
                    token,
                )

                try:

                    enviar_token_resend(
                        usuario,
                        token,
                        tipo,
                    )

                except Exception as error:

                    print(
                        "ERROR RESEND:",
                        repr(error),
                    )

                    limpiar_recuperacion_session(
                        request
                    )

                    mensaje = (
                        "No fue posible enviar "
                        "el código al correo."
                    )

                else:

                    return redirect(
                        "validar_token_recuperacion"
                    )

    return render(
        request,
        "recuperar_password.html",
        {
            "tipo": tipo,
            "mensaje": mensaje,
        },
    )


# =========================================================
# VALIDAR TOKEN
# =========================================================

def validar_token_recuperacion(
    request
):

    usuario_id = request.session.get(
        "recuperacion_usuario_id"
    )

    tipo = request.session.get(
        "recuperacion_tipo"
    )

    token_hash = request.session.get(
        "recuperacion_token_hash"
    )

    if (
        not usuario_id
        or tipo not in [
            "cliente",
            "admin",
        ]
        or not token_hash
    ):

        return redirect(
            "login"
            if tipo == "admin"
            else "login_cliente"
        )

    if not token_vigente(
        request
    ):

        limpiar_recuperacion_session(
            request
        )

        return render(
            request,
            "validar_token_recuperacion.html",
            {
                "mensaje":
                    "El código expiró. "
                    "Solicita uno nuevo.",

                "expirado":
                    True,

                "tipo":
                    tipo,
            },
        )

    mensaje = ""

    if request.method == "POST":

        token = request.POST.get(
            "token",
            "",
        ).strip()

        intentos = int(
            request.session.get(
                "recuperacion_intentos",
                0,
            )
        )

        if (
            len(token) != 6
            or not token.isdigit()
        ):

            mensaje = (
                "El código debe contener "
                "exactamente 6 dígitos."
            )

        elif check_password(
            token,
            token_hash,
        ):

            request.session[
                "recuperacion_token_validado"
            ] = True

            request.session.modified = True

            return redirect(
                "confirmar_recuperacion"
            )

        else:

            intentos += 1

            request.session[
                "recuperacion_intentos"
            ] = intentos

            request.session.modified = True

            restantes = (
                MAX_INTENTOS_TOKEN
                - intentos
            )

            if restantes <= 0:

                limpiar_recuperacion_session(
                    request
                )

                return render(
                    request,
                    "validar_token_recuperacion.html",
                    {
                        "mensaje":
                            "Superaste el máximo "
                            "de intentos.",

                        "expirado":
                            True,

                        "tipo":
                            tipo,
                    },
                )

            mensaje = (
                f"Código incorrecto. "
                f"Quedan {restantes} intentos."
            )

    return render(
        request,
        "validar_token_recuperacion.html",
        {
            "mensaje": mensaje,
            "expirado": False,
            "tipo": tipo,
        },
    )


# =========================================================
# CONFIRMAR RECUPERACIÓN
# =========================================================

def confirmar_recuperacion(
    request
):

    usuario_id = request.session.get(
        "recuperacion_usuario_id"
    )

    tipo = request.session.get(
        "recuperacion_tipo"
    )

    validado = request.session.get(
        "recuperacion_token_validado",
        False,
    )

    if (
        not usuario_id
        or not validado
        or not token_vigente(request)
    ):

        limpiar_recuperacion_session(
            request
        )

        return render(
            request,
            "confirmar_recuperacion.html",
            {
                "valido": False,
                "cambiada": False,
                "tipo": (
                    tipo or "cliente"
                ),
                "mensaje":
                    "La recuperación no "
                    "es válida o expiró.",
            },
        )

    usuario = get_object_or_404(
        User,
        id=usuario_id,
        is_active=True,
    )

    mensaje = ""

    if request.method == "POST":

        password1 = request.POST.get(
            "password1",
            "",
        )

        password2 = request.POST.get(
            "password2",
            "",
        )

        if not password1 or not password2:

            mensaje = (
                "Debe diligenciar ambos campos."
            )

        elif password1 != password2:

            mensaje = (
                "Las contraseñas no coinciden."
            )

        else:

            try:

                validate_password(
                    password1,
                    user=usuario,
                )

            except ValidationError as exc:

                mensaje = " ".join(
                    exc.messages
                )

            else:

                usuario.set_password(
                    password1
                )

                usuario.save(
                    update_fields=[
                        "password"
                    ]
                )

                marcar_cambio_password(
                    usuario,
                    False,
                )

                tipo_final = tipo

                limpiar_recuperacion_session(
                    request
                )

                return render(
                    request,
                    "confirmar_recuperacion.html",
                    {
                        "valido": True,
                        "cambiada": True,
                        "tipo": tipo_final,
                        "mensaje": "",
                    },
                )

    return render(
        request,
        "confirmar_recuperacion.html",
        {
            "valido": True,
            "cambiada": False,
            "tipo": tipo,
            "mensaje": mensaje,
        },
    )


# =========================================================
# EXPORTAR EXCEL
# =========================================================

@login_required(
    login_url="login"
)
@cambio_password_obligatorio
def exportar_excel(request):

    if not (
        request.user.is_staff
        or request.user.is_superuser
    ):

        return redirect(
            "login"
        )

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="reservas.xlsx"'
    )

    workbook = openpyxl.Workbook()

    worksheet = workbook.active

    worksheet.title = "Reservas"

    worksheet.append([
        "ID Reserva",
        "Usuario",
        "Nombre",
        "Apellido",
        "Tipo documento",
        "Documento",
        "Cancha",
        "Fecha",
        "Hora",
        "Duración",
        "Celular",
        "Comprobante",
        "Estado de pago",
    ])

    reservas_lista = (
        Reservas.objects.all()
        .select_related(
            "cliente"
        )
        .order_by(
            "fecha",
            "hora",
        )
    )

    for reserva in reservas_lista:

        usuario = (
            reserva.cliente.username
            if reserva.cliente
            else "No asociado"
        )

        tiene_comprobante = (
            "Sí"
            if reserva.comprobante_pago
            else "No"
        )

        estado_pago = (
            "Pagado"
            if reserva.pago
            else "Pendiente"
        )

        worksheet.append([
            reserva.id,
            usuario,
            reserva.nombre,
            reserva.apellido,
            reserva.get_tipo_documento_display(),
            reserva.documento,
            reserva.cancha,
            reserva.fecha,
            reserva.hora,
            reserva.duracion,
            reserva.cel,
            tiene_comprobante,
            estado_pago,
        ])

    workbook.save(
        response
    )

    return response