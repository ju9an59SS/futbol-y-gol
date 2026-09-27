from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import (
    PerfilAdministrador,
    PerfilCliente,
    TIPOS_DOCUMENTO,
)


# =========================================================
# VALIDAR DOCUMENTO
# =========================================================

def validar_documento(
    tipo_documento,
    documento
):

    documento = str(
        documento or ""
    ).strip()


    if not documento:

        raise ValidationError(
            "El documento es obligatorio."
        )


    if tipo_documento in [
        "CC",
        "TI",
    ]:

        if not documento.isdigit():

            raise ValidationError(
                "El documento debe contener "
                "únicamente números."
            )


    return documento


# =========================================================
# FORMULARIO BASE
# =========================================================

class RegistroBaseForm(
    forms.ModelForm
):

    first_name = forms.CharField(
        label="Nombre",
        required=True,
    )

    last_name = forms.CharField(
        label="Apellido",
        required=True,
    )

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
    )

    tipo_documento = forms.ChoiceField(
        choices=TIPOS_DOCUMENTO,
        label="Tipo de documento",
        required=True,
    )

    documento = forms.CharField(
        label="Documento",
        required=True,
    )

    celular = forms.CharField(
        label="Celular",
        required=True,
        max_length=10,
    )


    class Meta:

        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]


    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )


        for campo in self.fields.values():

            campo.widget.attrs.update({
                "class": "form-control"
            })


        self.fields[
            "tipo_documento"
        ].widget.attrs.update({
            "class": "form-select"
        })


        self.fields[
            "username"
        ].label = "Nombre de usuario"

        self.fields[
            "username"
        ].help_text = ""


    # =====================================================
    # USUARIO ÚNICO
    # =====================================================

    def clean_username(self):

        username = (
            self.cleaned_data[
                "username"
            ]
            .strip()
        )


        if User.objects.filter(
            username__iexact=username
        ).exists():

            raise ValidationError(
                "Ese nombre de usuario "
                "ya está registrado."
            )


        return username


    # =====================================================
    # CORREO ÚNICO
    # =====================================================

    def clean_email(self):

        email = (
            self.cleaned_data[
                "email"
            ]
            .strip()
            .lower()
        )


        if User.objects.filter(
            email__iexact=email
        ).exists():

            raise ValidationError(
                "Ese correo ya está registrado."
            )


        return email


    # =====================================================
    # DOCUMENTO
    # =====================================================

    def clean_documento(self):

        tipo = (
            self.cleaned_data.get(
                "tipo_documento"
            )
        )

        documento = validar_documento(
            tipo,
            self.cleaned_data.get(
                "documento"
            )
        )


        if PerfilCliente.objects.filter(
            documento=documento
        ).exists():

            raise ValidationError(
                "Ese documento ya está registrado."
            )


        if PerfilAdministrador.objects.filter(
            documento=documento
        ).exists():

            raise ValidationError(
                "Ese documento ya está registrado."
            )


        return documento


    # =====================================================
    # CELULAR
    # =====================================================

    def clean_celular(self):

        celular = (
            self.cleaned_data[
                "celular"
            ]
            .strip()
        )


        if (
            len(celular) != 10
            or not celular.isdigit()
            or not celular.startswith("3")
        ):

            raise ValidationError(
                "El celular debe tener "
                "10 dígitos y comenzar por 3."
            )


        return celular


class RegistroClienteForm(
    RegistroBaseForm
):
    pass


class RegistroAdministradorForm(
    RegistroBaseForm
):
    pass