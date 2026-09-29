from django.urls import path

from . import views


urlpatterns = [

    # =====================================================
    # INICIO
    # =====================================================

    path(
        "",
        views.index,
        name="index",
    ),


    # =====================================================
    # CLIENTE - REGISTRO
    # =====================================================

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


    # =====================================================
    # CLIENTE - LOGIN / LOGOUT
    # =====================================================

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


    # =====================================================
    # CLIENTE - PERFIL
    # =====================================================

    path(
        "cliente/perfil/",
        views.perfil_cliente,
        name="perfil_cliente",
    ),


    # =====================================================
    # CLIENTE - RESERVAS
    # =====================================================

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


    # =====================================================
    # CREAR RESERVA
    # =====================================================

    path(
        "reservar/",
        views.reservar,
        name="reservar",
    ),


    # =====================================================
    # COMPROBANTE PRIVADO
    # =====================================================

    path(
        "reserva/<int:reserva_id>/comprobante/",
        views.ver_comprobante,
        name="ver_comprobante",
    ),


    # =====================================================
    # CAMBIO OBLIGATORIO DE CONTRASEÑA
    # =====================================================

    path(
        "cambiar-password-inicial/",
        views.cambiar_password_inicial,
        name="cambiar_password_inicial",
    ),


    # =====================================================
    # ADMINISTRADOR - LOGIN / LOGOUT
    # =====================================================

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


    # =====================================================
    # ADMINISTRADOR - RESERVAS
    # =====================================================

    path(
        "reservas/",
        views.reservas,
        name="reservas",
    ),


    # =====================================================
    # ADMINISTRADOR - REGISTRO
    # =====================================================

    path(
        "administrador/registro/",
        views.registrar_administrador,
        name="registrar_administrador",
    ),


    # =====================================================
    # RECUPERACIÓN CLIENTE
    # =====================================================

    path(
        "cliente/recuperar/",
        views.recuperar_password,
        {
            "tipo": "cliente"
        },
        name="recuperar_password_cliente",
    ),


    # =====================================================
    # RECUPERACIÓN ADMIN
    # =====================================================

    path(
        "administrador/recuperar/",
        views.recuperar_password,
        {
            "tipo": "admin"
        },
        name="recuperar_password_admin",
    ),


    # =====================================================
    # VALIDAR TOKEN
    # =====================================================

    path(
        "recuperar/validar-token/",
        views.validar_token_recuperacion,
        name="validar_token_recuperacion",
    ),


    # =====================================================
    # NUEVA CONTRASEÑA
    # =====================================================

    path(
        "recuperar/nueva-password/",
        views.confirmar_recuperacion,
        name="confirmar_recuperacion",
    ),


    # =====================================================
    # EXPORTAR EXCEL
    # =====================================================

    path(
        "exportar-excel/",
        views.exportar_excel,
        name="exportar_excel",
    ),
]