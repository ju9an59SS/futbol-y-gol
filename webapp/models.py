from django.contrib.auth.models import User
from django.db import models


# =========================================================
# TIPOS DE DOCUMENTO
# =========================================================

TIPOS_DOCUMENTO = [
    ("CC", "Cédula de Ciudadanía"),
    ("TI", "Tarjeta de Identidad"),
    ("CE", "Cédula de Extranjería"),
]


# =========================================================
# INDICATIVOS DE PAÍS
# =========================================================

INDICATIVOS_PAIS = [
    ("+57", "Colombia (+57)"),
    ("+1", "Estados Unidos / Canadá (+1)"),
    ("+52", "México (+52)"),
    ("+54", "Argentina (+54)"),
    ("+55", "Brasil (+55)"),
    ("+56", "Chile (+56)"),
    ("+51", "Perú (+51)"),
    ("+593", "Ecuador (+593)"),
    ("+58", "Venezuela (+58)"),
    ("+507", "Panamá (+507)"),
    ("+506", "Costa Rica (+506)"),
    ("+502", "Guatemala (+502)"),
    ("+503", "El Salvador (+503)"),
    ("+504", "Honduras (+504)"),
    ("+505", "Nicaragua (+505)"),
    ("+591", "Bolivia (+591)"),
    ("+595", "Paraguay (+595)"),
    ("+598", "Uruguay (+598)"),
    ("+34", "España (+34)"),
    ("+44", "Reino Unido (+44)"),
    ("+33", "Francia (+33)"),
    ("+49", "Alemania (+49)"),
    ("+39", "Italia (+39)"),
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

    primer_nombre = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    segundo_nombre = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    primer_apellido = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    segundo_apellido = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO,
    )

    documento = models.CharField(
        max_length=20,
    )

    indicativo_pais = models.CharField(
        max_length=6,
        choices=INDICATIVOS_PAIS,
        default="+57",
    )

    celular = models.CharField(
        max_length=15
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tipo_documento",
                    "documento",
                ],
                name="uq_cliente_tipo_documento",
            ),
        ]

    @property
    def nombres_completos(self):

        nombres = " ".join(
            valor
            for valor in [
                self.primer_nombre,
                self.segundo_nombre,
            ]
            if valor
        ).strip()

        # Compatibilidad con usuarios creados
        # antes de separar los nombres.
        if nombres:
            return nombres

        return (
            self.usuario.first_name
            or ""
        ).strip()

    @property
    def apellidos_completos(self):

        apellidos = " ".join(
            valor
            for valor in [
                self.primer_apellido,
                self.segundo_apellido,
            ]
            if valor
        ).strip()

        if apellidos:
            return apellidos

        return (
            self.usuario.last_name
            or ""
        ).strip()

    @property
    def nombre_completo(self):

        return (
            f"{self.nombres_completos} "
            f"{self.apellidos_completos}"
        ).strip()

    @property
    def telefono_completo(self):

        return (
            f"{self.indicativo_pais} "
            f"{self.celular}"
        ).strip()

    def __str__(self):

        return (
            f"{self.nombre_completo} - "
            f"{self.tipo_documento} "
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

    primer_nombre = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    segundo_nombre = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    primer_apellido = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    segundo_apellido = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO,
    )

    documento = models.CharField(
        max_length=20,
    )

    indicativo_pais = models.CharField(
        max_length=6,
        choices=INDICATIVOS_PAIS,
        default="+57",
    )

    celular = models.CharField(
        max_length=15
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tipo_documento",
                    "documento",
                ],
                name="uq_admin_tipo_documento",
            ),
        ]

    @property
    def nombres_completos(self):

        nombres = " ".join(
            valor
            for valor in [
                self.primer_nombre,
                self.segundo_nombre,
            ]
            if valor
        ).strip()

        if nombres:
            return nombres

        return (
            self.usuario.first_name
            or ""
        ).strip()

    @property
    def apellidos_completos(self):

        apellidos = " ".join(
            valor
            for valor in [
                self.primer_apellido,
                self.segundo_apellido,
            ]
            if valor
        ).strip()

        if apellidos:
            return apellidos

        return (
            self.usuario.last_name
            or ""
        ).strip()

    @property
    def nombre_completo(self):

        return (
            f"{self.nombres_completos} "
            f"{self.apellidos_completos}"
        ).strip()

    @property
    def telefono_completo(self):

        return (
            f"{self.indicativo_pais} "
            f"{self.celular}"
        ).strip()

    def __str__(self):

        return (
            f"{self.nombre_completo} - "
            f"{self.tipo_documento} "
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

    # Fotografía histórica de los datos
    # al momento de crear la reserva.
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

    indicativo_pais = models.CharField(
        max_length=6,
        choices=INDICATIVOS_PAIS,
        default="+57",
    )

    cel = models.CharField(
        max_length=15
    )

    # =====================================================
    # COMPROBANTE PRIVADO EN VERCEL BLOB
    # =====================================================

    comprobante_pago = models.URLField(
        max_length=1000,
        null=True,
        blank=True,
    )

    # =====================================================
    # ESTADO DE PAGO
    # =====================================================

    pago = models.BooleanField(
        default=False
    )

    @property
    def telefono_completo(self):

        return (
            f"{self.indicativo_pais} "
            f"{self.cel}"
        ).strip()

    def __str__(self):

        return (
            f"Reserva #{self.pk} - "
            f"{self.nombre} {self.apellido}"
        )