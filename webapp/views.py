import mimetypes
import os
import secrets

from datetime import datetime, timedelta
from functools import wraps
from uuid import uuid4

import openpyxl

from django.conf import settings

from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
)

from django.contrib.auth.decorators import (
    login_required,
)

from django.contrib.auth.hashers import (
    check_password,
    make_password,
)

from django.contrib.auth.models import User

from django.contrib.auth.password_validation import (
    validate_password,
)

from django.core.exceptions import (
    ValidationError,
)

from django.core.mail import (
    send_mail,
)

from django.http import (
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

from django.utils.crypto import (
    get_random_string,
)

from vercel.blob import BlobClient

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
# CONFIGURACIÓN GENERAL
# =========================================================

TOKEN_EXPIRACION_MINUTOS = 10

MAX_INTENTOS_TOKEN = 5

MAX_COMPROBANTE_BYTES = (
    4 * 1024 * 1024
)

TIPOS_COMPROBANTE = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


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
                "23456789"
                "@#$%"
            ),
        )

        try:

            validate_password(
                password
            )

            return password

        except ValidationError:

            continue


# =========================================================
# ESTADO DE CAMBIO DE CONTRASEÑA
# =========================================================

def marcar_cambio_password(
    usuario,
    requerido=True,
):

    estado, _ = (
        EstadoAcceso.objects.get_or_create(
            usuario=usuario
        )
    )

    estado.debe_cambiar_password = (
        requerido
    )

    estado.save(
        update_fields=[
            "debe_cambiar_password"
        ]
    )


def requiere_cambio_password(
    usuario
):

    if not usuario.is_authenticated:

        return False

    estado, _ = (
        EstadoAcceso.objects.get_or_create(
            usuario=usuario
        )
    )

    return (
        estado.debe_cambiar_password
    )


def cambio_password_obligatorio(
    view_func
):

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

def validar_comprobante(
    archivo
):

    if not archivo:

        return

    if archivo.size > MAX_COMPROBANTE_BYTES:

        raise ValidationError(
            "El comprobante no puede "
            "superar los 4 MB."
        )

    content_type = getattr(
        archivo,
        "content_type",
        "",
    )

    if content_type not in TIPOS_COMPROBANTE:

        raise ValidationError(
            "Solo se permiten imágenes "
            "JPG, PNG o WEBP."
        )


# =========================================================
# VALIDAR CONFIGURACIÓN VERCEL BLOB
# =========================================================

def validar_configuracion_blob():

    token = os.environ.get(
        "BLOB_READ_WRITE_TOKEN",
        "",
    )

    if not token:

        raise RuntimeError(
            "BLOB_READ_WRITE_TOKEN "
            "no está configurado."
        )


# =========================================================
# SUBIR ARCHIVO A VERCEL BLOB
# =========================================================

def subir_comprobante_blob(
    archivo,
    reserva_id,
):

    validar_configuracion_blob()

    validar_comprobante(
        archivo
    )

    extension = os.path.splitext(
        archivo.name
    )[1].lower()

    if extension not in [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    ]:

        raise ValidationError(
            "La extensión del archivo "
            "no está permitida."
        )

    pathname = (
        f"comprobantes/"
        f"reserva-{reserva_id}/"
        f"{uuid4().hex}"
        f"{extension}"
    )

    archivo.seek(0)

    contenido = archivo.read()

    with BlobClient() as client:

        resultado = client.put(
            pathname,
            contenido,
            access="private",
            content_type=(
                archivo.content_type
                or
                "application/octet-stream"
            ),
        )

    return resultado.url


# =========================================================
# LEER ARCHIVO DE VERCEL BLOB
# =========================================================

def leer_comprobante_blob(
    url
):

    validar_configuracion_blob()

    with BlobClient() as client:

        resultado = client.get(
            str(url)
        )

    # -----------------------------------------------------
    # SDK puede devolver directamente bytes
    # -----------------------------------------------------

    if isinstance(
        resultado,
        bytes,
    ):

        return resultado


    # -----------------------------------------------------
    # Algunas respuestas exponen content
    # -----------------------------------------------------

    contenido = getattr(
        resultado,
        "content",
        None,
    )

    if isinstance(
        contenido,
        bytes,
    ):

        return contenido


    # -----------------------------------------------------
    # Algunas respuestas exponen stream
    # -----------------------------------------------------

    stream = getattr(
        resultado,
        "stream",
        None,
    )

    if stream is not None:

        return b"".join(
            stream
        )


    raise RuntimeError(
        "Vercel Blob no devolvió "
        "contenido legible."
    )


# =========================================================
# ELIMINAR ARCHIVO DE VERCEL BLOB
# =========================================================

def eliminar_comprobante_blob(
    url
):

    if not url:

        return

    url = str(
        url
    )

    if not url.startswith(
        "https://"
    ):

        return

    validar_configuracion_blob()

    with BlobClient() as client:

        client.delete(
            [url]
        )


# =========================================================
# INICIO
# =========================================================

def index(
    request
):

    return render(
        request,
        "index.html",
    )


# =========================================================
# REGISTRAR CLIENTE
# =========================================================

def registrar_cliente(
    request
):

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

            usuario.set_password(
                password_temporal
            )

            usuario.save()


            PerfilCliente.objects.create(

                usuario=
                    usuario,

                tipo_documento=
                    form.cleaned_data[
                        "tipo_documento"
                    ],

                documento=
                    form.cleaned_data[
                        "documento"
                    ],

                celular=
                    form.cleaned_data[
                        "celular"
                    ],
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


            # -------------------------------------------------
            # ENVIAR CONTRASEÑA TEMPORAL POR CORREO
            # -------------------------------------------------

            if usuario.email:

                try:

                    send_mail(

                        subject=(
                            "Cuenta creada "
                            "- Futbol y Gol"
                        ),

                        message=(
                            f"Hola "
                            f"{usuario.first_name or usuario.username}."
                            f"\n\n"
                            f"Tu usuario es: "
                            f"{usuario.username}\n"
                            f"Tu contraseña temporal es: "
                            f"{password_temporal}\n\n"
                            f"Debes cambiarla "
                            f"en tu primer ingreso."
                        ),

                        from_email=(
                            settings.DEFAULT_FROM_EMAIL
                        ),

                        recipient_list=[
                            usuario.email
                        ],

                        fail_silently=False,
                    )

                except Exception as error:

                    print(
                        "ERROR ENVIANDO "
                        "CORREO CLIENTE:",
                        repr(error),
                    )


            return redirect(
                "registro_cliente_exitoso"
            )

    else:

        form = (
            RegistroClienteForm()
        )


    return render(
        request,
        "registro_cliente.html",
        {
            "form":
                form
        },
    )


# =========================================================
# REGISTRO CLIENTE EXITOSO
# =========================================================

def registro_cliente_exitoso(
    request
):

    usuario = request.session.get(
        "usuario_creado"
    )

    password_temporal = (
        request.session.get(
            "password_temporal"
        )
    )

    if (
        not usuario
        or not password_temporal
    ):

        return redirect(
            "login_cliente"
        )


    contexto = {

        "usuario":
            usuario,

        "password_temporal":
            password_temporal,
    }


    request.session.pop(
        "usuario_creado",
        None,
    )

    request.session.pop(
        "password_temporal",
        None,
    )


    return render(
        request,
        "registro_cliente_exitoso.html",
        contexto,
    )


# =========================================================
# LOGIN CLIENTE
# =========================================================

def login_cliente(
    request
):

    mensaje = ""


    if request.user.is_authenticated:

        if (
            request.user.is_staff
            or request.user.is_superuser
        ):

            return redirect(
                "reservas"
            )

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


        if (
            not usuario
            or not password
        ):

            mensaje = (
                "Debe ingresar usuario "
                "y contraseña."
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
                "Usuario o contraseña "
                "incorrectos."
            )


    return render(
        request,
        "login_cliente.html",
        {
            "mensaje":
                mensaje
        },
    )


# =========================================================
# LOGOUT CLIENTE
# =========================================================

def logout_cliente(
    request
):

    auth_logout(
        request
    )

    return redirect(
        "login_cliente"
    )


# =========================================================
# PERFIL CLIENTE
# =========================================================

@login_required(
    login_url="login_cliente"
)
@cambio_password_obligatorio
def perfil_cliente(
    request
):

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


    return render(
        request,
        "perfil_cliente.html",
        {
            "usuario":
                request.user,

            "perfil":
                perfil,
        },
    )


# =========================================================
# CAMBIO OBLIGATORIO DE CONTRASEÑA
# =========================================================

@login_required
def cambiar_password_inicial(
    request
):

    mensaje = ""


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


    if request.method == "POST":

        password1 = request.POST.get(
            "password1",
            "",
        )

        password2 = request.POST.get(
            "password2",
            "",
        )


        if (
            not password1
            or not password2
        ):

            mensaje = (
                "Debe diligenciar "
                "ambos campos."
            )

        elif password1 != password2:

            mensaje = (
                "Las contraseñas "
                "no coinciden."
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

                usuario_actual = (
                    request.user
                )

                usuario_actual.set_password(
                    password1
                )

                usuario_actual.save(
                    update_fields=[
                        "password"
                    ]
                )

                marcar_cambio_password(
                    usuario_actual,
                    False,
                )

                es_admin = (
                    usuario_actual.is_staff
                    or
                    usuario_actual.is_superuser
                )

                auth_logout(
                    request
                )

                if es_admin:

                    return redirect(
                        "login"
                    )

                return redirect(
                    "login_cliente"
                )


    return render(
        request,
        "cambiar_password_inicial.html",
        {
            "mensaje":
                mensaje
        },
    )


# =========================================================
# MIS RESERVAS
# =========================================================

@login_required(
    login_url="login_cliente"
)
@cambio_password_obligatorio
def mis_reservas(
    request
):

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

            reserva_id = (
                request.POST.get(
                    "reserva_id"
                )
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
                    "Debe seleccionar "
                    "un comprobante."
                )

                tipo_mensaje = "error"

            else:

                try:

                    validar_comprobante(
                        comprobante
                    )


                    url_anterior = (
                        str(
                            reserva.comprobante_pago
                        )
                        if reserva.comprobante_pago
                        else ""
                    )


                    nueva_url = (
                        subir_comprobante_blob(
                            comprobante,
                            reserva.id,
                        )
                    )


                    reserva.comprobante_pago = (
                        nueva_url
                    )

                    # Cada comprobante nuevo
                    # queda pendiente nuevamente.

                    reserva.pago = False


                    reserva.save(
                        update_fields=[
                            "comprobante_pago",
                            "pago",
                        ]
                    )


                    if url_anterior:

                        try:

                            eliminar_comprobante_blob(
                                url_anterior
                            )

                        except Exception as error:

                            print(
                                "ERROR ELIMINANDO "
                                "BLOB ANTERIOR:",
                                repr(error),
                            )


                except ValidationError as exc:

                    mensaje = " ".join(
                        exc.messages
                    )

                    tipo_mensaje = "error"


                except Exception as error:

                    print(
                        "ERROR SUBIENDO "
                        "COMPROBANTE:",
                        repr(error),
                    )

                    mensaje = (
                        "No fue posible "
                        "guardar el comprobante "
                        "en la nube."
                    )

                    tipo_mensaje = "error"


                else:

                    mensaje = (
                        "Comprobante cargado "
                        "correctamente. "
                        "Queda pendiente "
                        "de validación."
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
            "reservas":
                reservas_lista,

            "mensaje":
                mensaje,

            "tipo_mensaje":
                tipo_mensaje,
        },
    )


# =========================================================
# ESTADO DE RESERVAS - AJAX CLIENTE
# =========================================================

@login_required(
    login_url="login_cliente"
)
def estado_reservas_cliente(
    request
):

    if (
        request.user.is_staff
        or request.user.is_superuser
    ):

        return JsonResponse(
            {
                "reservas": []
            }
        )


    reservas_cliente = (
        Reservas.objects.filter(
            cliente=request.user
        )
        .values(
            "id",
            "pago",
        )
    )


    datos = []


    for reserva in reservas_cliente:

        datos.append({

            "id":
                reserva["id"],

            "pago":
                reserva["pago"],

            "estado":
                (
                    "Pagado"
                    if reserva["pago"]
                    else "Pendiente"
                ),
        })


    return JsonResponse(
        {
            "reservas":
                datos
        }
    )


# =========================================================
# VER COMPROBANTE PRIVADO
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


    url_comprobante = str(
        reserva.comprobante_pago
    )


    if not url_comprobante.startswith(
        "https://"
    ):

        raise Http404


    try:

        contenido = (
            leer_comprobante_blob(
                url_comprobante
            )
        )

    except Exception as error:

        print(
            "ERROR LEYENDO BLOB:",
            repr(error),
        )

        raise Http404


    content_type, _ = (
        mimetypes.guess_type(
            url_comprobante
        )
    )


    response = HttpResponse(
        contenido,
        content_type=(
            content_type
            or "application/octet-stream"
        ),
    )


    response[
        "Content-Disposition"
    ] = (
        'inline; filename="comprobante"'
    )


    response[
        "Cache-Control"
    ] = (
        "private, no-store"
    )


    return response


# =========================================================
# CREAR RESERVA
# =========================================================

@login_required(
    login_url="login_cliente"
)
@cambio_password_obligatorio
def reservar(
    request
):

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

            "mensaje":
                "",

            "tipo_mensaje":
                "error",
        }


        # -------------------------------------------------
        # CAMPOS OBLIGATORIOS
        # -------------------------------------------------

        if not all([
            cancha,
            fecha,
            hora,
            duracion,
        ]):

            contexto[
                "mensaje"
            ] = (
                "Debe completar todos "
                "los campos obligatorios."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )


        # -------------------------------------------------
        # DURACIÓN
        # -------------------------------------------------

        if duracion not in [
            "1",
            "2",
        ]:

            contexto[
                "mensaje"
            ] = (
                "La duración debe ser "
                "de 1 o 2 horas."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )


        duracion_int = int(
            duracion
        )


        # -------------------------------------------------
        # FECHA Y HORA
        # -------------------------------------------------

        try:

            fecha_obj = (
                datetime.strptime(
                    fecha,
                    "%Y-%m-%d",
                ).date()
            )


            hora_obj = (
                datetime.strptime(
                    hora,
                    "%H:%M",
                ).time()
            )


        except ValueError:

            contexto[
                "mensaje"
            ] = (
                "La fecha o la hora "
                "no son válidas."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )


        # -------------------------------------------------
        # NO RESERVAR EN EL PASADO
        # -------------------------------------------------

        inicio_nueva = (
            datetime.combine(
                fecha_obj,
                hora_obj,
            )
        )


        inicio_nueva = (
            timezone.make_aware(
                inicio_nueva,
                timezone.get_current_timezone(),
            )
        )


        if inicio_nueva <= timezone.now():

            contexto[
                "mensaje"
            ] = (
                "No puede reservar "
                "una fecha u hora pasada."
            )

            return render(
                request,
                "reservar.html",
                contexto,
            )


        fin_nueva = (
            inicio_nueva
            + timedelta(
                hours=duracion_int
            )
        )


        # -------------------------------------------------
        # VALIDAR CRUCE DE HORARIOS
        # -------------------------------------------------

        reservas_existentes = (
            Reservas.objects.filter(
                cancha=cancha,
                fecha=fecha_obj,
            )
        )


        for existente in (
            reservas_existentes
        ):

            inicio_existente = (
                datetime.combine(
                    existente.fecha,
                    existente.hora,
                )
            )


            inicio_existente = (
                timezone.make_aware(
                    inicio_existente,
                    timezone.get_current_timezone(),
                )
            )


            fin_existente = (
                inicio_existente
                + timedelta(
                    hours=
                        existente.duracion
                )
            )


            if (
                inicio_nueva
                < fin_existente
                and
                fin_nueva
                > inicio_existente
            ):

                contexto[
                    "mensaje"
                ] = (
                    "La cancha ya está "
                    "reservada en ese horario."
                )

                return render(
                    request,
                    "reservar.html",
                    contexto,
                )


        # -------------------------------------------------
        # VALIDAR COMPROBANTE
        # -------------------------------------------------

        if comprobante:

            try:

                validar_comprobante(
                    comprobante
                )

            except ValidationError as exc:

                contexto[
                    "mensaje"
                ] = " ".join(
                    exc.messages
                )

                return render(
                    request,
                    "reservar.html",
                    contexto,
                )


        # -------------------------------------------------
        # CREAR RESERVA SIN ARCHIVO LOCAL
        # -------------------------------------------------

        reserva = (
            Reservas.objects.create(

                cliente=
                    request.user,

                nombre=
                    request.user.first_name,

                apellido=
                    request.user.last_name,

                tipo_documento=
                    perfil.tipo_documento,

                documento=
                    perfil.documento,

                cancha=
                    cancha,

                fecha=
                    fecha_obj,

                hora=
                    hora_obj,

                duracion=
                    duracion_int,

                cel=
                    perfil.celular,

                comprobante_pago=
                    None,

                pago=
                    False,
            )
        )


        # -------------------------------------------------
        # SUBIR FOTO A VERCEL BLOB
        # -------------------------------------------------

        if comprobante:

            try:

                nueva_url = (
                    subir_comprobante_blob(
                        comprobante,
                        reserva.id,
                    )
                )


                reserva.comprobante_pago = (
                    nueva_url
                )


                reserva.save(
                    update_fields=[
                        "comprobante_pago"
                    ]
                )


            except Exception as error:

                print(
                    "ERROR SUBIENDO "
                    "BLOB:",
                    repr(error),
                )


                reserva.delete()


                contexto[
                    "mensaje"
                ] = (
                    "No fue posible guardar "
                    "el comprobante en la nube. "
                    "La reserva no fue creada."
                )


                return render(
                    request,
                    "reservar.html",
                    contexto,
                )


        contexto[
            "mensaje"
        ] = (
            "Reserva creada "
            "correctamente."
        )


        contexto[
            "tipo_mensaje"
        ] = "exito"


        return render(
            request,
            "reservar.html",
            contexto,
        )


    return render(
        request,
        "reservar.html",
        datos_cliente,
    )


# =========================================================
# REGISTRAR ADMINISTRADOR
# =========================================================

def registrar_administrador(
    request
):

    # Este registro queda público porque así
    # se requiere para la demostración académica.

    if request.user.is_authenticated:

        if (
            request.user.is_staff
            or request.user.is_superuser
        ):

            return redirect(
                "reservas"
            )


    if request.method == "POST":

        form = (
            RegistroAdministradorForm(
                request.POST
            )
        )


        if form.is_valid():

            password_temporal = (
                generar_password_temporal()
            )


            admin_user = form.save(
                commit=False
            )


            admin_user.first_name = (
                form.cleaned_data[
                    "first_name"
                ]
            )

            admin_user.last_name = (
                form.cleaned_data[
                    "last_name"
                ]
            )

            admin_user.email = (
                form.cleaned_data[
                    "email"
                ]
            )


            admin_user.is_staff = True

            admin_user.is_superuser = False


            admin_user.set_password(
                password_temporal
            )


            admin_user.save()


            PerfilAdministrador.objects.create(

                usuario=
                    admin_user,

                tipo_documento=
                    form.cleaned_data[
                        "tipo_documento"
                    ],

                documento=
                    form.cleaned_data[
                        "documento"
                    ],

                celular=
                    form.cleaned_data[
                        "celular"
                    ],
            )


            marcar_cambio_password(
                admin_user,
                True,
            )


            # -------------------------------------------------
            # CORREO ADMIN
            # -------------------------------------------------

            if admin_user.email:

                try:

                    send_mail(

                        subject=(
                            "Cuenta administrativa "
                            "- Futbol y Gol"
                        ),

                        message=(
                            f"Hola "
                            f"{admin_user.first_name or admin_user.username}."
                            f"\n\n"
                            f"Tu usuario administrador es: "
                            f"{admin_user.username}\n"
                            f"Tu contraseña temporal es: "
                            f"{password_temporal}\n\n"
                            f"Debes cambiarla "
                            f"en tu primer ingreso."
                        ),

                        from_email=(
                            settings.DEFAULT_FROM_EMAIL
                        ),

                        recipient_list=[
                            admin_user.email
                        ],

                        fail_silently=False,
                    )


                except Exception as error:

                    print(
                        "ERROR ENVIANDO "
                        "CORREO ADMIN:",
                        repr(error),
                    )


            return render(
                request,
                "registro_administrador_exitoso.html",
                {
                    "usuario":
                        admin_user.username,

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
            "form":
                form
        },
    )


# =========================================================
# LOGIN ADMINISTRADOR
# =========================================================

def login(
    request
):

    mensaje = ""


    if request.user.is_authenticated:

        if (
            request.user.is_staff
            or request.user.is_superuser
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

        # Si había sesión cliente,
        # se cierra antes de login admin.

        auth_logout(
            request
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


        if (
            not usuario
            or not password
        ):

            mensaje = (
                "Debe ingresar usuario "
                "y contraseña."
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
                    or
                    user.is_superuser
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
                "Credenciales "
                "administrativas inválidas."
            )


    return render(
        request,
        "login.html",
        {
            "mensaje":
                mensaje
        },
    )


# =========================================================
# LOGOUT ADMINISTRADOR
# =========================================================

def logout(
    request
):

    auth_logout(
        request
    )

    return redirect(
        "login"
    )


# =========================================================
# PANEL ADMINISTRADOR - RESERVAS
# =========================================================

@login_required(
    login_url="login"
)
@cambio_password_obligatorio
def reservas(
    request
):

    if not (
        request.user.is_staff
        or request.user.is_superuser
    ):

        return redirect(
            "login"
        )


    mensaje = ""

    tipo_mensaje = ""


    if request.method == "POST":

        accion = request.POST.get(
            "accion",
            "",
        )

        reserva_id = request.POST.get(
            "reserva_id"
        )


        # -------------------------------------------------
        # ACTUALIZAR PAGO
        # -------------------------------------------------

        if accion == "actualizar_pago":

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


            if (
                request.headers.get(
                    "X-Requested-With"
                )
                == "XMLHttpRequest"
            ):

                return JsonResponse(
                    {
                        "ok":
                            True,

                        "id":
                            reserva.id,

                        "pago":
                            reserva.pago,
                    }
                )


            mensaje = (
                f"Reserva #{reserva.id} "
                f"actualizada correctamente."
            )

            tipo_mensaje = (
                "exito"
            )


        # -------------------------------------------------
        # ELIMINAR SOLAMENTE COMPROBANTE
        # -------------------------------------------------

        elif accion == (
            "eliminar_comprobante"
        ):

            reserva = get_object_or_404(
                Reservas,
                id=reserva_id,
            )


            if not reserva.comprobante_pago:

                mensaje = (
                    "La reserva no tiene "
                    "comprobante."
                )

                tipo_mensaje = (
                    "error"
                )

            else:

                url = str(
                    reserva.comprobante_pago
                )


                try:

                    eliminar_comprobante_blob(
                        url
                    )


                except Exception as error:

                    print(
                        "ERROR ELIMINANDO "
                        "COMPROBANTE:",
                        repr(error),
                    )


                    mensaje = (
                        "No fue posible eliminar "
                        "el comprobante."
                    )

                    tipo_mensaje = (
                        "error"
                    )


                else:

                    reserva.comprobante_pago = (
                        None
                    )

                    reserva.pago = False


                    reserva.save(
                        update_fields=[
                            "comprobante_pago",
                            "pago",
                        ]
                    )


                    mensaje = (
                        f"Comprobante de la "
                        f"reserva #{reserva.id} "
                        f"eliminado correctamente."
                    )

                    tipo_mensaje = (
                        "exito"
                    )


        # -------------------------------------------------
        # ELIMINAR RESERVA COMPLETA
        # -------------------------------------------------

        elif accion == (
            "eliminar_reserva"
        ):

            reserva = get_object_or_404(
                Reservas,
                id=reserva_id,
            )


            numero_reserva = (
                reserva.id
            )


            url = (
                str(
                    reserva.comprobante_pago
                )
                if reserva.comprobante_pago
                else ""
            )


            if url:

                try:

                    eliminar_comprobante_blob(
                        url
                    )

                except Exception as error:

                    print(
                        "ERROR ELIMINANDO "
                        "BLOB DE RESERVA:",
                        repr(error),
                    )


                    mensaje = (
                        "No se eliminó la reserva "
                        "porque no fue posible "
                        "eliminar su comprobante."
                    )

                    tipo_mensaje = (
                        "error"
                    )

                else:

                    reserva.delete()

                    mensaje = (
                        f"Reserva "
                        f"#{numero_reserva} "
                        f"eliminada correctamente."
                    )

                    tipo_mensaje = (
                        "exito"
                    )


            else:

                reserva.delete()


                mensaje = (
                    f"Reserva "
                    f"#{numero_reserva} "
                    f"eliminada correctamente."
                )

                tipo_mensaje = (
                    "exito"
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

            "tipo_mensaje":
                tipo_mensaje,
        },
    )


# =========================================================
# GENERAR TOKEN DE RECUPERACIÓN
# =========================================================

def generar_token_recuperacion():

    return str(
        secrets.randbelow(
            900000
        )
        + 100000
    )


# =========================================================
# LIMPIAR RECUPERACIÓN DE SESIÓN
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
# GUARDAR RECUPERACIÓN
# =========================================================

def guardar_recuperacion(
    request,
    usuario,
    tipo,
    token,
):

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
    ] = (
        timezone.now()
        + timedelta(
            minutes=
                TOKEN_EXPIRACION_MINUTOS
        )
    ).timestamp()


    request.session[
        "recuperacion_intentos"
    ] = 0


    request.session[
        "recuperacion_token_validado"
    ] = False


    request.session.modified = True


# =========================================================
# VALIDAR VIGENCIA TOKEN
# =========================================================

def token_vigente(
    request
):

    valor = request.session.get(
        "recuperacion_expira"
    )


    if not valor:

        return False


    try:

        valor = float(
            valor
        )

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
# ENVIAR TOKEN POR GMAIL
# =========================================================

def enviar_token_recuperacion(
    usuario,
    token,
    tipo,
):

    if not settings.EMAIL_HOST_USER:

        raise RuntimeError(
            "EMAIL_HOST_USER "
            "no está configurado."
        )


    if not settings.EMAIL_HOST_PASSWORD:

        raise RuntimeError(
            "EMAIL_HOST_PASSWORD "
            "no está configurado."
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


    asunto = (
        "Código de recuperación "
        "- Futbol y Gol"
    )


    texto = (
        f"Hola {nombre}.\n\n"
        f"Recibimos una solicitud "
        f"para recuperar tu cuenta "
        f"de {tipo_cuenta}.\n\n"
        f"Tu código es: {token}\n\n"
        f"Este código vence en "
        f"{TOKEN_EXPIRACION_MINUTOS} "
        f"minutos."
    )


    html = f"""
    <div style="
        font-family: Arial, sans-serif;
        max-width: 600px;
        margin: auto;
        padding: 30px;
    ">

        <h2>
            Futbol y Gol
        </h2>

        <p>
            Hola
            <strong>
                {nombre}
            </strong>.
        </p>

        <p>
            Recibimos una solicitud
            para recuperar tu cuenta
            de {tipo_cuenta}.
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

        <p>
            Si no solicitaste
            este código,
            puedes ignorar este correo.
        </p>

    </div>
    """


    return send_mail(

        subject=
            asunto,

        message=
            texto,

        from_email=
            settings.DEFAULT_FROM_EMAIL,

        recipient_list=[
            usuario.email
        ],

        fail_silently=
            False,

        html_message=
            html,
    )


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


        if (
            not username
            or not correo
        ):

            mensaje = (
                "Debe ingresar usuario "
                "y correo electrónico."
            )

        else:

            usuario = (
                User.objects.filter(
                    username__iexact=
                        username,

                    email__iexact=
                        correo,

                    is_active=
                        True,
                )
                .first()
            )


            usuario_valido = (
                False
            )


            if usuario:

                if tipo == "admin":

                    usuario_valido = (
                        usuario.is_staff
                        or
                        usuario.is_superuser
                    )

                else:

                    usuario_valido = (
                        not usuario.is_staff
                        and
                        not usuario.is_superuser
                    )


            if not usuario_valido:

                mensaje = (
                    "El usuario y el correo "
                    "no corresponden a "
                    "una cuenta válida."
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

                    enviar_token_recuperacion(
                        usuario,
                        token,
                        tipo,
                    )


                except Exception as error:

                    print(
                        "ERROR CORREO "
                        "RECUPERACION:",
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
            "tipo":
                tipo,

            "mensaje":
                mensaje,
        },
    )


# =========================================================
# VALIDAR TOKEN
# =========================================================

def validar_token_recuperacion(
    request
):

    usuario_id = (
        request.session.get(
            "recuperacion_usuario_id"
        )
    )


    tipo = (
        request.session.get(
            "recuperacion_tipo"
        )
    )


    token_hash = (
        request.session.get(
            "recuperacion_token_hash"
        )
    )


    if (
        not usuario_id
        or
        tipo not in [
            "cliente",
            "admin",
        ]
        or
        not token_hash
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


            request.session.modified = (
                True
            )


            return redirect(
                "confirmar_recuperacion"
            )


        else:

            intentos += 1


            request.session[
                "recuperacion_intentos"
            ] = intentos


            request.session.modified = (
                True
            )


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
                f"Quedan "
                f"{restantes} intentos."
            )


    return render(
        request,
        "validar_token_recuperacion.html",
        {
            "mensaje":
                mensaje,

            "expirado":
                False,

            "tipo":
                tipo,
        },
    )


# =========================================================
# CONFIRMAR NUEVA CONTRASEÑA
# =========================================================

def confirmar_recuperacion(
    request
):

    usuario_id = (
        request.session.get(
            "recuperacion_usuario_id"
        )
    )


    tipo = (
        request.session.get(
            "recuperacion_tipo"
        )
    )


    validado = (
        request.session.get(
            "recuperacion_token_validado",
            False,
        )
    )


    if (
        not usuario_id
        or not validado
        or not token_vigente(
            request
        )
    ):

        limpiar_recuperacion_session(
            request
        )


        return render(
            request,
            "confirmar_recuperacion.html",
            {
                "valido":
                    False,

                "cambiada":
                    False,

                "tipo":
                    tipo or "cliente",

                "mensaje":
                    "La recuperación "
                    "no es válida o expiró.",
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


        if (
            not password1
            or not password2
        ):

            mensaje = (
                "Debe diligenciar "
                "ambos campos."
            )


        elif password1 != password2:

            mensaje = (
                "Las contraseñas "
                "no coinciden."
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
                        "valido":
                            True,

                        "cambiada":
                            True,

                        "tipo":
                            tipo_final,

                        "mensaje":
                            "",
                    },
                )


    return render(
        request,
        "confirmar_recuperacion.html",
        {
            "valido":
                True,

            "cambiada":
                False,

            "tipo":
                tipo,

            "mensaje":
                mensaje,
        },
    )


# =========================================================
# EXPORTAR RESERVAS A EXCEL
# =========================================================

@login_required(
    login_url="login"
)
@cambio_password_obligatorio
def exportar_excel(
    request
):

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
        'attachment; '
        'filename="reservas.xlsx"'
    )


    workbook = (
        openpyxl.Workbook()
    )


    worksheet = (
        workbook.active
    )


    worksheet.title = (
        "Reservas"
    )


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