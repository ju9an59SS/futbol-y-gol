from django.urls import path

from . import views


urlpatterns = [

    # =====================================================
    # HOME
    # =====================================================

    path(
        "",
        views.index,
        name="index",
    ),

    # =====================================================
    # CLIENTE
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
        "cliente/mis-reservas/estado/",
        views.estado_reservas_cliente,
        name="estado_reservas_cliente",
    ),

    # =====================================================
    # RESERVAR
    # =====================================================

    path(
        "reservar/",
        views.reservar,
        name="reservar",
    ),

    # =====================================================
    # ADMINISTRADOR
    # =====================================================

    path(
        "administrador/registro/",
        views.registrar_administrador,
        name="registrar_administrador",
    ),

    path(
        "administrador/login/",
        views.login,
        name="login",
    ),

    path(
        "administrador/logout/",
        views.logout,
        name="logout",
    ),

    path(
        "administrador/reservas/",
        views.reservas,
        name="reservas",
    ),

    path(
        "administrador/exportar-excel/",
        views.exportar_excel,
        name="exportar_excel",
    ),

    # =====================================================
    # COMPROBANTES
    # =====================================================

    path(
        "comprobante/<int:reserva_id>/",
        views.ver_comprobante,
        name="ver_comprobante",
    ),

    # =====================================================
    # CAMBIO PASSWORD PRIMER INGRESO
    # =====================================================

    path(
        "cambiar-password-inicial/",
        views.cambiar_password_inicial,
        name="cambiar_password_inicial",
    ),

    # =====================================================
    # RECUPERACIÓN
    # =====================================================

    path(
        "cliente/recuperar-password/",
        views.recuperar_password_cliente,
        name="recuperar_password_cliente",
    ),

    path(
        "administrador/recuperar-password/",
        views.recuperar_password_admin,
        name="recuperar_password_admin",
    ),

    path(
        "recuperar/validar-codigo/",
        views.validar_token_recuperacion,
        name="validar_token_recuperacion",
    ),

    path(
        "recuperar/nueva-password/",
        views.confirmar_recuperacion,
        name="confirmar_recuperacion",
    ),
]