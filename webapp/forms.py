from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import (
    OperationalError,
    connections,
)

from .models import (
    PerfilAdministrador,
    PerfilCliente,
    TIPOS_DOCUMENTO,
)


# =========================================================
# CONSULTA CON REINTENTO
# =========================================================

def existe_con_reintento(queryset):

    try:
        return queryset.exists()

    except OperationalError:

        connections.close_all()

        return queryset.exists()


# =========================================================
# VALIDAR DOCUMENTO
# =========================================================

def validar_documento(
    tipo_documento,
    documento,
):

    documento = (
        documento
        or ""
    ).strip()

    if tipo_documento not in dict(
        TIPOS_DOCUMENTO
    ):

        raise ValidationError(
            "El tipo de documento seleccionado "
            "no es válido."
        )

    if not documento:

        raise ValidationError(
            "El documento es obligatorio."
        )

    if not documento.isdigit():

        raise ValidationError(
            "El documento debe contener "
            "únicamente números."
        )

    if (
        len(documento) < 6
        or len(documento) > 20
    ):

        raise ValidationError(
            "El documento debe tener "
            "entre 6 y 20 dígitos."
        )

    return documento


# =========================================================
# DOCUMENTO ÚNICO ENTRE CLIENTE Y ADMIN
# =========================================================

def documento_ya_registrado(
    documento,
):

    cliente_existe = (
        existe_con_reintento(
            PerfilCliente.objects.filter(
                documento=documento
            )
        )
    )

    administrador_existe = (
        existe_con_reintento(
            PerfilAdministrador.objects.filter(
                documento=documento
            )
        )
    )

    return (
        cliente_existe
        or administrador_existe
    )


# =========================================================
# FORMULARIO BASE
# =========================================================

class RegistroBaseForm(
    forms.ModelForm
):

    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
    )

    last_name = forms.CharField(
        label="Apellido",
        max_length=150,
        required=True,
    )

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )

    tipo_documento = (
        forms.ChoiceField(
            label="Tipo de documento",
            choices=TIPOS_DOCUMENTO,
            required=True,
        )
    )

    documento = forms.CharField(
        label="Documento",
        max_length=20,
        required=True,
    )

    celular = forms.CharField(
        label="Celular",
        max_length=10,
        required=True,
    )

    class Meta:

        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]

        labels = {
            "username": "Usuario",
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        for field in (
            self.fields.values()
        ):

            css = (
                field.widget.attrs.get(
                    "class",
                    "",
                )
            )

            field.widget.attrs[
                "class"
            ] = (
                f"{css} form-control"
            ).strip()

        self.fields[
            "tipo_documento"
        ].widget.attrs[
            "class"
        ] = "form-select"

        self.fields[
            "documento"
        ].widget.attrs.update(
            {
                "inputmode":
                    "numeric",

                "autocomplete":
                    "off",
            }
        )

        self.fields[
            "celular"
        ].widget.attrs.update(
            {
                "inputmode":
                    "numeric",

                "autocomplete":
                    "tel",
            }
        )

    # =====================================================
    # USUARIO
    # =====================================================

    def clean_username(
        self
    ):

        username = (
            self.cleaned_data.get(
                "username"
            )
            or ""
        ).strip()

        if not username:

            raise ValidationError(
                "El usuario es obligatorio."
            )

        if existe_con_reintento(
            User.objects.filter(
                username__iexact=username
            )
        ):

            raise ValidationError(
                "Ese nombre de usuario "
                "ya está registrado."
            )

        return username

    # =====================================================
    # NOMBRE
    # =====================================================

    def clean_first_name(
        self
    ):

        value = (
            self.cleaned_data.get(
                "first_name"
            )
            or ""
        ).strip()

        if not value:

            raise ValidationError(
                "El nombre es obligatorio."
            )

        return value

    # =====================================================
    # APELLIDO
    # =====================================================

    def clean_last_name(
        self
    ):

        value = (
            self.cleaned_data.get(
                "last_name"
            )
            or ""
        ).strip()

        if not value:

            raise ValidationError(
                "El apellido es obligatorio."
            )

        return value

    # =====================================================
    # CORREO
    # =====================================================

    def clean_email(
        self
    ):

        email = (
            self.cleaned_data.get(
                "email"
            )
            or ""
        ).strip().lower()

        if not email:

            raise ValidationError(
                "El correo electrónico "
                "es obligatorio."
            )

        if existe_con_reintento(
            User.objects.filter(
                email__iexact=email
            )
        ):

            raise ValidationError(
                "Ese correo electrónico "
                "ya está registrado."
            )

        return email

    # =====================================================
    # DOCUMENTO
    # =====================================================

    def clean_documento(
        self
    ):

        tipo_documento = (
            self.cleaned_data.get(
                "tipo_documento"
            )
        )

        documento = (
            validar_documento(
                tipo_documento,
                self.cleaned_data.get(
                    "documento"
                ),
            )
        )

        if documento_ya_registrado(
            documento
        ):

            raise ValidationError(
                "Ese documento ya está "
                "registrado en el sistema."
            )

        return documento

    # =====================================================
    # CELULAR
    # =====================================================

    def clean_celular(
        self
    ):

        celular = (
            self.cleaned_data.get(
                "celular"
            )
            or ""
        ).strip()

        if (
            not celular.isdigit()
            or len(celular) != 10
        ):

            raise ValidationError(
                "El celular debe contener "
                "exactamente 10 dígitos."
            )

        return celular


# =========================================================
# REGISTRO CLIENTE
# =========================================================

class RegistroClienteForm(
    RegistroBaseForm
):

    pass


# =========================================================
# REGISTRO ADMINISTRADOR
# =========================================================

class RegistroAdministradorForm(
    RegistroBaseForm
):

    pass