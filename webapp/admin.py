from django.contrib import admin

from .models import (
    EstadoAcceso,
    PerfilAdministrador,
    PerfilCliente,
    Reservas,
)


@admin.register(EstadoAcceso)
class EstadoAccesoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "usuario",
        "debe_cambiar_password",
    )


@admin.register(PerfilCliente)
class PerfilClienteAdmin(
    admin.ModelAdmin
):

    list_display = (
        "usuario",
        "tipo_documento",
        "documento",
        "celular",
    )

    search_fields = (
        "usuario__username",
        "documento",
    )


@admin.register(PerfilAdministrador)
class PerfilAdministradorAdmin(
    admin.ModelAdmin
):

    list_display = (
        "usuario",
        "tipo_documento",
        "documento",
        "celular",
    )

    search_fields = (
        "usuario__username",
        "documento",
    )


@admin.register(Reservas)
class ReservasAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "cliente",
        "cancha",
        "fecha",
        "hora",
        "duracion",
        "pago",
    )

    list_filter = (
        "pago",
        "cancha",
        "fecha",
    )

    search_fields = (
        "cliente__username",
        "nombre",
        "apellido",
        "documento",
    )