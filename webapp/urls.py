from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.index,
        name="index",
    ),


    # CLIENTE

    path(
        "cliente/registro/",
        views.registrar_cliente,
        name="registrar_cliente",
    ),

    path(
        "cliente/registro/exitoso/",
        views.registro_cliente_exitoso,
        name="registro_cliente_exitoso",
    ),

    path(
        "cliente/login/",
        views.login_cliente,
        name="login_cliente",
    ),

    path(
        "cliente/logout/",
        views.logout_cliente,
        name="logout_cliente",
    ),

    path(
        "cliente/perfil/",
        views.perfil_cliente,
        name="perfil_cliente",
    ),

    path(
        "cliente/mis-reservas/",
        views.mis_reservas,
        name="mis_reservas",
    ),

    path(
        "cliente/estado-reservas/",
        views.estado_reservas_cliente,
        name="estado_reservas_cliente",
    ),


    # RESERVA

    path(
        "reservar/",
        views.reservar,
        name="reservar",
    ),


    # COMPROBANTE

    path(
        "reserva/<int:reserva_id>/comprobante/",
        views.ver_comprobante,
        name="ver_comprobante",
    ),


    # CAMBIO PASSWORD INICIAL

    path(
        "cambiar-password-inicial/",
        views.cambiar_password_inicial,
        name="cambiar_password_inicial",
    ),


    # ADMIN

    path(
        "login/",
        views.login,
        name="login",
    ),

    path(
        "logout/",
        views.logout,
        name="logout",
    ),

    path(
        "reservas/",
        views.reservas,
        name="reservas",
    ),

    path(
        "administrador/registro/",
        views.registrar_administrador,
        name="registrar_administrador",
    ),


    # RECUPERACIÓN CLIENTE

    path(
        "cliente/recuperar/",
        views.recuperar_password,
        {
            "tipo": "cliente",
        },
        name="recuperar_password_cliente",
    ),


    # RECUPERACIÓN ADMIN

    path(
        "administrador/recuperar/",
        views.recuperar_password,
        {
            "tipo": "admin",
        },
        name="recuperar_password_admin",
    ),


    # TOKEN

    path(
        "recuperar/validar-token/",
        views.validar_token_recuperacion,
        name="validar_token_recuperacion",
    ),

    path(
        "recuperar/nueva-password/",
        views.confirmar_recuperacion,
        name="confirmar_recuperacion",
    ),


    # EXCEL

    path(
        "exportar-excel/",
        views.exportar_excel,
        name="exportar_excel",
    ),
]