import os

import secrets



from datetime import (

    datetime,

    timedelta,

)



from functools import wraps

from uuid import uuid4



import openpyxl



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



from django.contrib.auth.models import (

    User,

)



from django.contrib.auth.password_validation import (

    validate_password,

)



from django.core.exceptions import (

    ValidationError,

)



from django.core.mail import (

    send_mail,

)



from django.db import (

    transaction,

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



from django.utils import (

    timezone,

)



from django.utils.crypto import (

    get_random_string,

)



from vercel.blob import (

    BlobClient,

)



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

# CONSTANTES

# =========================================================



MAX_COMPROBANTE_BYTES = (

    4 * 1024 * 1024

)



TIPOS_COMPROBANTE = {

    "image/jpeg",

    "image/png",

    "image/webp",

}



TOKEN_EXPIRACION_MINUTOS = 10



MAX_INTENTOS_TOKEN = 5



CANCHAS_VALIDAS = {

    "futbol5": "Cancha Fútbol 5",

    "futbol7": "Cancha Fútbol 7",

    "futbol11": "Cancha Fútbol 11",

}





# =========================================================

# GENERAR CONTRASEÑA TEMPORAL

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

        EstadoAcceso.objects

        .get_or_create(

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





def requiere_cambio_password(usuario):



    if not usuario.is_authenticated:



        return False



    estado, _ = (

        EstadoAcceso.objects

        .get_or_create(

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

# NOMBRE DE CANCHA

# =========================================================



def nombre_cancha(valor):



    return CANCHAS_VALIDAS.get(

        valor,

        valor,

    )





# =========================================================

# VALIDAR COMPROBANTE

# =========================================================



def validar_comprobante(archivo):



    if not archivo:

        return



    if (

        archivo.size

        > MAX_COMPROBANTE_BYTES

    ):



        raise ValidationError(

            "El comprobante no puede "

            "superar los 4 MB."

        )



    tipo = getattr(

        archivo,

        "content_type",

        "",

    )



    if tipo not in TIPOS_COMPROBANTE:



        raise ValidationError(

            "Solo se permiten imágenes "

            "JPG, PNG o WEBP."

        )





# =========================================================

# VERCEL BLOB

# =========================================================



def obtener_blob_client():



    return BlobClient()





def subir_comprobante_blob(

    archivo,

    reserva_id,

):



    validar_comprobante(

        archivo

    )



    extension = (

        os.path.splitext(

            archivo.name

            or ""

        )[1]

        .lower()

    )



    if extension not in {

        ".jpg",

        ".jpeg",

        ".png",

        ".webp",

    }:



        extension = {

            "image/jpeg": ".jpg",

            "image/png": ".png",

            "image/webp": ".webp",

        }.get(

            getattr(

                archivo,

                "content_type",

                "",

            ),

            "",

        )



    pathname = (

        f"comprobantes/"

        f"{reserva_id}/"

        f"{uuid4().hex}"

        f"{extension}"

    )



    archivo.seek(0)



    contenido = archivo.read()



    resultado = (

        obtener_blob_client()

        .put(

            pathname,

            contenido,

            access="private",

            content_type=getattr(

                archivo,

                "content_type",

                "application/octet-stream",

            ),

        )

    )



    url = getattr(

        resultado,

        "url",

        None,

    )



    if (

        not url

        and isinstance(

            resultado,

            dict,

        )

    ):



        url = resultado.get(

            "url"

        )



    if not url:



        raise RuntimeError(

            "Vercel Blob no devolvió "

            "la URL del comprobante."

        )



    return url





def eliminar_blob_si_existe(url):



    if not url:

        return



    try:



        obtener_blob_client().delete(

            url

        )



    except Exception as error:



        print(

            "ERROR ELIMINANDO BLOB:",

            repr(error),

        )





def _valor_blob(

    resultado,

    nombre,

    default=None,

):



    valor = getattr(

        resultado,

        nombre,

        None,

    )



    if (

        valor is None

        and isinstance(

            resultado,

            dict,

        )

    ):



        valor = resultado.get(

            nombre

        )



    if valor is None:

        return default



    return valor





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



            primer_nombre = (

                form.cleaned_data[

                    "primer_nombre"

                ]

            )



            segundo_nombre = (

                form.cleaned_data[

                    "segundo_nombre"

                ]

            )



            primer_apellido = (

                form.cleaned_data[

                    "primer_apellido"

                ]

            )



            segundo_apellido = (

                form.cleaned_data[

                    "segundo_apellido"

                ]

            )



            with transaction.atomic():



                usuario = form.save(

                    commit=False

                )



                usuario.first_name = (

                    primer_nombre

                )



                usuario.last_name = (

                    primer_apellido

                )



                usuario.email = (

                    form.cleaned_data[

                        "email"

                    ]

                )



                usuario.set_password(

                    password_temporal

                )



                usuario.save()



                PerfilCliente.objects.create(

                    usuario=usuario,



                    primer_nombre=(

                        primer_nombre

                    ),



                    segundo_nombre=(

                        segundo_nombre

                    ),



                    primer_apellido=(

                        primer_apellido

                    ),



                    segundo_apellido=(

                        segundo_apellido

                    ),



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



                    indicativo_pais=(

                        form.cleaned_data[

                            "indicativo_pais"

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



            try:



                send_mail(

                    subject=(

                        "Contraseña temporal "

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

                        f"obligatoriamente en tu "

                        f"primer inicio de sesión."

                    ),



                    from_email=None,



                    recipient_list=[

                        usuario.email

                    ],



                    fail_silently=True,

                )



            except Exception:

                pass



            return redirect(

                "registro_cliente_exitoso"

            )



    else:



        form = RegistroClienteForm()



    return render(

        request,

        "registro_cliente.html",

        {

            "form": form

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



    password_temporal = (

        request.session.pop(

            "password_temporal",

            None,

        )

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

            "usuario":

                usuario,



            "password_temporal":

                password_temporal,

        },

    )





# =========================================================

# LOGIN CLIENTE

# =========================================================



def login_cliente(request):



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



        usuario = (

            request.POST.get(

                "usuario",

                "",

            ).strip()

        )



        password = request.POST.get(

            "password",

            "",

        )



        if (

            not usuario

            or not password

        ):



            mensaje = (

                "Debe ingresar el usuario "

                "y la contraseña."

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

                "Credenciales de cliente "

                "inválidas."

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



def logout_cliente(request):



    auth_logout(

        request

    )



    return redirect(

        "login_cliente"

    )





# =========================================================

# CAMBIO OBLIGATORIO DE CONTRASEÑA

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



        if (

            not password1

            or not password2

        ):



            mensaje = (

                "Debe diligenciar ambos "

                "campos de contraseña."

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



                username = (

                    request.user.username

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



    return render(

        request,

        "cambiar_password_inicial.html",

        {

            "mensaje":

                mensaje

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

            "perfil":

                perfil,



            "total_reservas":

                total_reservas,

        },

    )





# =========================================================

# REGISTRAR ADMINISTRADOR

# =========================================================



def registrar_administrador(request):



    if request.user.is_authenticated:



        if requiere_cambio_password(

            request.user

        ):



            return redirect(

                "cambiar_password_inicial"

            )



        if not (

            request.user.is_staff

            or request.user.is_superuser

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



            primer_nombre = (

                form.cleaned_data[

                    "primer_nombre"

                ]

            )



            segundo_nombre = (

                form.cleaned_data[

                    "segundo_nombre"

                ]

            )



            primer_apellido = (

                form.cleaned_data[

                    "primer_apellido"

                ]

            )



            segundo_apellido = (

                form.cleaned_data[

                    "segundo_apellido"

                ]

            )



            with transaction.atomic():



                admin_user = form.save(

                    commit=False

                )



                admin_user.first_name = (

                    primer_nombre

                )



                admin_user.last_name = (

                    primer_apellido

                )



                admin_user.email = (

                    form.cleaned_data[

                        "email"

                    ]

                )



                admin_user.is_staff = True



                admin_user.set_password(

                    password_temporal

                )



                admin_user.save()



                PerfilAdministrador.objects.create(

                    usuario=

                        admin_user,



                    primer_nombre=(

                        primer_nombre

                    ),



                    segundo_nombre=(

                        segundo_nombre

                    ),



                    primer_apellido=(

                        primer_apellido

                    ),



                    segundo_apellido=(

                        segundo_apellido

                    ),



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



                    indicativo_pais=(

                        form.cleaned_data[

                            "indicativo_pais"

                        ]

                    ),



                    celular=(

                        form.cleaned_data[

                            "celular"

                        ]

                    ),

                )



                marcar_cambio_password(

                    admin_user,

                    True,

                )



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

                        f"obligatoriamente en tu "

                        f"primer inicio de sesión."

                    ),



                    from_email=None,



                    recipient_list=[

                        admin_user.email

                    ],



                    fail_silently=True,

                )



            except Exception:

                pass



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



        form = RegistroAdministradorForm()



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



def login(request):



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



        return redirect(

            "perfil_cliente"

        )



    if request.method == "POST":



        usuario = (

            request.POST.get(

                "usuario",

                "",

            ).strip()

        )



        password = request.POST.get(

            "password",

            "",

        )



        if (

            not usuario

            or not password

        ):



            mensaje = (

                "Debe ingresar el usuario "

                "y la contraseña."

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

                "Credenciales administrativas "

                "inválidas."

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



def logout(request):



    auth_logout(

        request

    )



    return redirect(

        "login"

    )





# =========================================================

# RECUPERACIÓN

# =========================================================



def generar_token_recuperacion():



    return str(

        secrets.randbelow(

            900000

        )

        + 100000

    )





def limpiar_recuperacion_session(request):



    claves = [

        "recuperacion_usuario_id",

        "recuperacion_tipo",

        "recuperacion_token_hash",

        "recuperacion_creado",

        "recuperacion_intentos",

        "recuperacion_token_validado",

    ]



    for clave in claves:



        request.session.pop(

            clave,

            None,

        )



    request.session.modified = True





def token_vigente(request):



    creado = request.session.get(

        "recuperacion_creado"

    )



    if creado is None:

        return False



    try:



        creado = float(

            creado

        )



    except (

        TypeError,

        ValueError,

    ):



        return False



    transcurrido = (

        timezone.now().timestamp()

        - creado

    )



    return (

        transcurrido

        <= TOKEN_EXPIRACION_MINUTOS

        * 60

    )





def enviar_token_recuperacion(

    usuario,

    token,

    tipo,

):



    tipo_cuenta = (

        "administrador"

        if tipo == "admin"

        else "cliente"

    )



    send_mail(

        subject=(

            "Código de recuperación "

            "- Futbol y Gol"

        ),



        message=(

            f"Hola "

            f"{usuario.first_name or usuario.username}."

            f"\n\n"

            f"Tu código de recuperación "

            f"para la cuenta de "

            f"{tipo_cuenta} es: "

            f"{token}\n\n"

            f"El código vence en "

            f"{TOKEN_EXPIRACION_MINUTOS} "

            f"minutos.\n"

            f"Si no solicitaste este cambio, "

            f"ignora este mensaje."

        ),



        from_email=None,



        recipient_list=[

            usuario.email

        ],



        fail_silently=False,

    )





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



        username = (

            request.POST.get(

                "usuario",

                "",

            ).strip()

        )



        correo = (

            request.POST.get(

                "correo",

                "",

            )

            .strip()

            .lower()

        )



        if (

            not username

            or not correo

        ):



            mensaje = (

                "Debe ingresar el usuario "

                "y el correo registrado."

            )



        else:



            usuario = (

                User.objects.filter(

                    username__iexact=

                        username,



                    email__iexact=

                        correo,



                    is_active=True,

                ).first()

            )



            usuario_valido = False



            if usuario:



                if tipo == "admin":



                    usuario_valido = (

                        usuario.is_staff

                        or usuario.is_superuser

                    )



                else:



                    usuario_valido = not (

                        usuario.is_staff

                        or usuario.is_superuser

                    )



            if (

                not usuario

                or not usuario_valido

            ):



                mensaje = (

                    "El usuario y el correo "

                    "no corresponden a una "

                    "cuenta válida de este tipo."

                )



            else:



                token = (

                    generar_token_recuperacion()

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

                    "recuperacion_creado"

                ] = (

                    timezone.now().timestamp()

                )



                request.session[

                    "recuperacion_intentos"

                ] = 0



                request.session[

                    "recuperacion_token_validado"

                ] = False



                request.session.modified = True



                try:



                    enviar_token_recuperacion(

                        usuario,

                        token,

                        tipo,

                    )



                except Exception as error:



                    print(

                        "ERROR ENVIANDO TOKEN:",

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





def recuperar_password_cliente(request):



    return recuperar_password(

        request,

        "cliente",

    )





def recuperar_password_admin(request):



    return recuperar_password(

        request,

        "admin",

    )





# =========================================================

# VALIDAR CÓDIGO DE RECUPERACIÓN

# =========================================================



def validar_token_recuperacion(request):



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



        tipo_final = tipo



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

                    tipo_final,

            },

        )



    mensaje = ""



    if request.method == "POST":



        token = (

            request.POST.get(

                "token",

                "",

            ).strip()

        )



        intentos = int(

            request.session.get(

                "recuperacion_intentos",

                0,

            )

        )



        codigo_formato_valido = (

            len(token) == 6

            and token.isdigit()

        )



        codigo_correcto = (

            codigo_formato_valido

            and check_password(

                token,

                token_hash,

            )

        )



        if codigo_correcto:



            request.session[

                "recuperacion_token_validado"

            ] = True



            request.session.modified = True



            return redirect(

                "confirmar_recuperacion"

            )



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



            tipo_final = tipo



            limpiar_recuperacion_session(

                request

            )



            return render(

                request,

                "validar_token_recuperacion.html",

                {

                    "mensaje":

                        "Superaste el máximo "

                        "de intentos. Solicita "

                        "un nuevo código.",



                    "expirado":

                        True,



                    "tipo":

                        tipo_final,

                },

            )



        if not codigo_formato_valido:



            mensaje = (

                "El código debe contener "

                "exactamente 6 dígitos. "

                f"Quedan {restantes} intentos."

            )



        else:



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

# NUEVA CONTRASEÑA DE RECUPERACIÓN

# =========================================================



def confirmar_recuperacion(request):



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

        or not token_vigente(

            request

        )

    ):



        tipo_final = (

            tipo

            or "cliente"

        )



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

                    tipo_final,



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



        if (

            not password1

            or not password2

        ):



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

            perfil.nombres_completos,



        "apellido_cliente":

            perfil.apellidos_completos,



        "tipo_documento_cliente":

            perfil.tipo_documento,



        "documento_cliente":

            perfil.documento,



        "indicativo_pais_cliente":

            perfil.indicativo_pais,



        "cel_cliente":

            perfil.celular,

    }



    if request.method != "POST":



        return render(

            request,

            "reservar.html",

            datos_cliente,

        )



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



    comprobante = request.FILES.get(

        "comprobante_pago"

    )



    contexto = {

        **datos_cliente,



        "mensaje":

            "",



        "tipo_mensaje":

            "error",

    }



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



    if cancha not in CANCHAS_VALIDAS:



        contexto[

            "mensaje"

        ] = (

            "El tipo de cancha "

            "seleccionado no es válido."

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



    try:



        fecha_obj = datetime.strptime(

            fecha,

            "%Y-%m-%d",

        ).date()



        hora_obj = datetime.strptime(

            hora,

            "%H:%M",

        ).time()



    except ValueError:



        contexto[

            "mensaje"

        ] = (

            "La fecha o la hora "

            "seleccionada no es válida."

        )



        return render(

            request,

            "reservar.html",

            contexto,

        )



    duracion_int = int(

        duracion

    )



    inicio_nueva = datetime.combine(

        fecha_obj,

        hora_obj,

    )



    ahora_local = (

        timezone.localtime()

        .replace(

            tzinfo=None

        )

    )



    if inicio_nueva < ahora_local:



        contexto[

            "mensaje"

        ] = (

            "No puedes reservar una "

            "fecha u hora anterior "

            "a la actual."

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



    reservas_del_dia = (

        Reservas.objects.filter(

            cancha=cancha,

            fecha=fecha_obj,

        )

    )



    for reserva_existente in (

        reservas_del_dia

    ):



        inicio_existente = (

            datetime.combine(

                reserva_existente.fecha,

                reserva_existente.hora,

            )

        )



        fin_existente = (

            inicio_existente

            + timedelta(

                hours=(

                    reserva_existente

                    .duracion

                )

            )

        )



        if (

            inicio_nueva

            < fin_existente

            and fin_nueva

            > inicio_existente

        ):



            contexto[

                "mensaje"

            ] = (

                "Ese tipo de cancha "

                "ya está reservado "

                "en ese horario. "

                "Selecciona otra hora."

            )



            return render(

                request,

                "reservar.html",

                contexto,

            )



    reserva = Reservas.objects.create(

        cliente=

            request.user,



        nombre=

            perfil.nombres_completos,



        apellido=

            perfil.apellidos_completos,



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



        indicativo_pais=

            perfil.indicativo_pais,



        cel=

            perfil.celular,



        comprobante_pago=

            None,



        pago=

            False,

    )



    if comprobante:



        try:



            nueva_url = (

                subir_comprobante_blob(

                    comprobante,

                    reserva.id,

                )

            )



        except Exception as error:



            print(

                "ERROR SUBIENDO BLOB:",

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



        reserva.comprobante_pago = (

            nueva_url

        )



        reserva.save(

            update_fields=[

                "comprobante_pago"

            ]

        )



    contexto[

        "mensaje"

    ] = (

        "Reserva creada correctamente. "

        "El estado de pago queda "

        "pendiente de validación."

    )



    contexto[

        "tipo_mensaje"

    ] = "exito"



    return render(

        request,

        "reservar.html",

        contexto,

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



        if (

            accion

            == "subir_comprobante"

        ):



            reserva_id = request.POST.get(

                "reserva_id"

            )



            reserva = get_object_or_404(

                Reservas,

                id=reserva_id,

                cliente=request.user,

            )



            comprobante = request.FILES.get(

                "comprobante_pago"

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



                    nueva_url = (

                        subir_comprobante_blob(

                            comprobante,

                            reserva.id,

                        )

                    )



                except ValidationError as exc:



                    mensaje = " ".join(

                        exc.messages

                    )



                    tipo_mensaje = "error"



                except Exception as error:



                    print(

                        "ERROR SUBIENDO BLOB:",

                        repr(error),

                    )



                    mensaje = (

                        "No fue posible guardar "

                        "el comprobante. "

                        "Inténtalo nuevamente."

                    )



                    tipo_mensaje = "error"



                else:



                    url_anterior = (

                        reserva.comprobante_pago

                    )



                    reserva.comprobante_pago = (

                        nueva_url

                    )



                    reserva.pago = False



                    reserva.save(

                        update_fields=[

                            "comprobante_pago",

                            "pago",

                        ]

                    )



                    if (

                        url_anterior

                        and url_anterior

                        != nueva_url

                    ):



                        eliminar_blob_si_existe(

                            url_anterior

                        )



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

# ESTADO CLIENTE - JSON

# =========================================================



@login_required(

    login_url="login_cliente"

)

@cambio_password_obligatorio

def estado_reservas_cliente(request):



    if (

        request.user.is_staff

        or request.user.is_superuser

    ):



        return JsonResponse(

            {

                "ok":

                    False,



                "error":

                    "No autorizado.",

            },



            status=403,

        )



    reservas_cliente = (

        Reservas.objects.filter(

            cliente=request.user

        )

        .only(

            "id",

            "pago",

        )

    )



    datos = []



    for reserva in reservas_cliente:



        datos.append(

            {

                "id":

                    reserva.id,



                "pago":

                    reserva.pago,



                "estado":

                    (

                        "Pagado"

                        if reserva.pago

                        else "Pendiente"

                    ),

            }

        )



    return JsonResponse(

        {

            "ok":

                True,



            "reservas":

                datos,

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



    try:



        resultado = (

            obtener_blob_client()

            .get(

                reserva.comprobante_pago,

                access="private",

                use_cache=False,

            )

        )



    except Exception as error:



        print(

            "ERROR LEYENDO BLOB:",

            repr(error),

        )



        raise Http404 from error



    status_code = _valor_blob(

        resultado,

        "status_code",

        200,

    )



    if (

        status_code

        and int(

            status_code

        ) >= 400

    ):



        raise Http404



    contenido = _valor_blob(

        resultado,

        "content",

    )



    content_type = _valor_blob(

        resultado,

        "content_type",

        "application/octet-stream",

    )



    if contenido is None:

        raise Http404



    response = HttpResponse(

        contenido,

        content_type=

            content_type,

    )



    response[

        "Content-Disposition"

    ] = (

        f'inline; '

        f'filename="comprobante_'

        f'{reserva.id}"'

    )



    return response





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

    tipo_mensaje = ""



    if request.method == "POST":



        accion = request.POST.get(

            "accion",

            "",

        )



        reserva_id = request.POST.get(

            "reserva_id"

        )



        if reserva_id:



            reserva = get_object_or_404(

                Reservas,

                id=reserva_id,

            )



            # =============================================

            # ACTUALIZAR PAGO

            # =============================================



            if (

                accion

                == "actualizar_pago"

            ):



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



                            "estado":

                                (

                                    "Pagado"

                                    if reserva.pago

                                    else "Pendiente"

                                ),

                        }

                    )



                mensaje = (

                    f"Reserva "

                    f"#{reserva.id} "

                    f"actualizada "

                    f"correctamente."

                )



                tipo_mensaje = "exito"



            # =============================================

            # ELIMINAR COMPROBANTE DESHABILITADO

            # =============================================



            elif (

                accion

                == "eliminar_comprobante"

            ):



                mensaje = (

                    "La eliminación individual "

                    "del comprobante está "

                    "deshabilitada por ahora."

                )



                tipo_mensaje = "error"



            # =============================================

            # ELIMINAR RESERVA COMPLETA

            # =============================================



            elif (

                accion

                == "eliminar_reserva"

            ):



                id_eliminado = (

                    reserva.id

                )



                if reserva.comprobante_pago:



                    eliminar_blob_si_existe(

                        reserva.comprobante_pago

                    )



                reserva.delete()



                mensaje = (

                    f"Reserva "

                    f"#{id_eliminado} "

                    f"eliminada correctamente."

                )



                tipo_mensaje = "exito"



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

            "application/"

            "vnd.openxmlformats-"

            "officedocument."

            "spreadsheetml.sheet"

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



    worksheet.title = "Reservas"



    worksheet.append([

        "ID Reserva",

        "Usuario",

        "Nombre",

        "Apellido",

        "Tipo documento",

        "Número de documento",

        "Tipo de cancha",

        "Fecha reserva",

        "Hora de inicio",

        "Duración reserva",

        "Indicativo país",

        "Número de celular",

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

            nombre_cancha(

                reserva.cancha

            ),

            reserva.fecha,

            reserva.hora,

            reserva.duracion,

            reserva.indicativo_pais,

            reserva.cel,

            tiene_comprobante,

            estado_pago,

        ])



    workbook.save(

        response

    )



    return response