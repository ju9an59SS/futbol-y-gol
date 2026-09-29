from django.contrib.auth.models import User
from django.db import models


# =========================================================
# TIPOS DE DOCUMENTO
# =========================================================

TIPOS_DOCUMENTO = [
    ("CC", "Cédula de Ciudadanía"),
    ("TI", "Tarjeta de Identidad"),
    ("CE", "Cédula de Extranjería"),
    ("PA", "Pasaporte"),
]


# =========================================================
# ESTADO DE ACCESO
# =========================================================

class EstadoAcceso(models.Model):

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="estado_acceso",
    )

    debe_cambiar_password = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.usuario.username


# =========================================================
# PERFIL CLIENTE
# =========================================================

class PerfilCliente(models.Model):

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_cliente",
    )

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO,
    )

    documento = models.CharField(
        max_length=20,
        unique=True,
    )

    celular = models.CharField(
        max_length=10
    )

    def __str__(self):
        return (
            f"{self.usuario.username} - "
            f"{self.documento}"
        )


# =========================================================
# PERFIL ADMINISTRADOR
# =========================================================

class PerfilAdministrador(models.Model):

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_administrador",
    )

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO,
    )

    documento = models.CharField(
        max_length=20,
        unique=True,
    )

    celular = models.CharField(
        max_length=10
    )

    def __str__(self):
        return (
            f"{self.usuario.username} - "
            f"{self.documento}"
        )


# =========================================================
# RESERVAS
# =========================================================

class Reservas(models.Model):

    cliente = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservas_cliente",
    )

    nombre = models.CharField(
        max_length=100
    )

    apellido = models.CharField(
        max_length=100
    )

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO,
    )

    documento = models.CharField(
        max_length=20
    )

    cancha = models.CharField(
        max_length=50
    )

    fecha = models.DateField()

    hora = models.TimeField()

    duracion = models.PositiveIntegerField()

    cel = models.CharField(
        max_length=10
    )


    # =====================================================
    # COMPROBANTE
    # =====================================================
    # Ahora NO se guarda el archivo físicamente en Django.
    # Aquí se guarda la URL privada de Vercel Blob.
    # =====================================================

    comprobante_pago = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
    )


    # =====================================================
    # ESTADO DE PAGO
    # SOLO ADMINISTRADOR LO CAMBIA
    # =====================================================

    pago = models.BooleanField(
        default=False
    )


    def __str__(self):

        return (
            f"Reserva #{self.pk} - "
            f"{self.nombre} {self.apellido}"
        )