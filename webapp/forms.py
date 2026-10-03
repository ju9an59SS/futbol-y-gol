from django import forms



from django.contrib.auth.models import User



from django.core.exceptions import ValidationError



from django.db import (

    OperationalError,

    connections,

)



from .models import (

    INDICATIVOS_PAIS,

    PerfilAdministrador,

    PerfilCliente,

    TIPOS_DOCUMENTO,

)





# =========================================================

# LÍMITES FUNCIONALES

# =========================================================



MAX_USERNAME = 30



MAX_NOMBRE = 30



MAX_APELLIDO = 30



MAX_EMAIL = 254



MAX_DOCUMENTO = 20



MAX_CELULAR = 15





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

# NORMALIZAR ESPACIOS

# =========================================================



def normalizar_espacios(valor):



    return " ".join(

        (valor or "").strip().split()

    )





# =========================================================

# VALIDAR NOMBRE / APELLIDO

# =========================================================



def validar_parte_nombre(

    valor,

    etiqueta,

    obligatorio=True,

    permitir_espacios=False,

    max_length=30,

):



    valor = normalizar_espacios(

        valor

    )



    if not valor:



        if obligatorio:

            raise ValidationError(

                f"{etiqueta} es obligatorio."

            )



        return ""



    if len(valor) < 2:



        raise ValidationError(

            f"{etiqueta} debe contener "

            f"mínimo 2 caracteres."

        )



    if len(valor) > max_length:



        raise ValidationError(

            f"{etiqueta} no puede superar "

            f"los {max_length} caracteres."

        )



    if (

        not permitir_espacios

        and " " in valor

    ):



        raise ValidationError(

            f"{etiqueta} debe contener "

            f"un solo nombre. Utilice "

            f"el campo siguiente para "

            f"un segundo nombre."

        )



    caracteres_especiales = {

        "-",

        "'",

        " ",

    }



    for caracter in valor:



        if (

            not caracter.isalpha()

            and caracter

            not in caracteres_especiales

        ):



            raise ValidationError(

                f"{etiqueta} solo puede "

                f"contener letras, espacios, "

                f"guion o apóstrofe."

            )



    if (

        "--" in valor

        or "''" in valor

        or "-'" in valor

        or "'-" in valor

    ):



        raise ValidationError(

            f"{etiqueta} contiene "

            f"separadores inválidos."

        )



    return valor





# =========================================================

# VALIDAR DOCUMENTO SEGÚN TIPO

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

            "El tipo de documento "

            "seleccionado no es válido."

        )



    if not documento:



        raise ValidationError(

            "El número de documento "

            "es obligatorio."

        )



    if not documento.isdigit():



        raise ValidationError(

            "El número de documento "

            "debe contener únicamente "

            "dígitos, sin puntos, espacios "

            "ni guiones."

        )



    # =====================================================

    # CÉDULA DE CIUDADANÍA

    # EXACTAMENTE 10 DÍGITOS

    # =====================================================



    if tipo_documento == "CC":



        if len(documento) != 10:



            raise ValidationError(

                "La Cédula de Ciudadanía "

                "debe contener exactamente "

                "10 dígitos."

            )



    # =====================================================

    # TARJETA DE IDENTIDAD

    # EXACTAMENTE 10 DÍGITOS

    # =====================================================



    elif tipo_documento == "TI":



        if len(documento) != 10:



            raise ValidationError(

                "La Tarjeta de Identidad "

                "debe contener exactamente "

                "10 dígitos."

            )



    # =====================================================

    # CÉDULA DE EXTRANJERÍA

    # 6 O 7 DÍGITOS

    # =====================================================



    elif tipo_documento == "CE":



        if len(documento) not in [

            6,

            7,

        ]:



            raise ValidationError(

                "La Cédula de Extranjería "

                "debe contener 6 o 7 dígitos."

            )



    return documento





# =========================================================

# DOCUMENTO ÚNICO POR TIPO ENTRE CLIENTE Y ADMIN

# =========================================================



def documento_ya_registrado(

    tipo_documento,

    documento,

):



    cliente_existe = existe_con_reintento(

        PerfilCliente.objects.filter(

            tipo_documento=tipo_documento,

            documento=documento,

        )

    )



    administrador_existe = (

        existe_con_reintento(

            PerfilAdministrador.objects.filter(

                tipo_documento=tipo_documento,

                documento=documento,

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



    username = forms.RegexField(

        label="Usuario",

        regex=r"^[\w.@+-]+$",

        min_length=4,

        max_length=MAX_USERNAME,

        required=True,

        error_messages={

            "invalid": (

                "El usuario solo puede contener "

                "letras, números y los caracteres "

                "@ . + - _"

            )

        },

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_USERNAME),



                "autocomplete":

                    "username",



                "placeholder":

                    "Entre 4 y 30 caracteres",

            }

        ),

    )



    primer_nombre = forms.CharField(

        label="Primer nombre",

        min_length=2,

        max_length=MAX_NOMBRE,

        required=True,

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_NOMBRE),



                "autocomplete":

                    "given-name",



                "placeholder":

                    "Máximo 30 caracteres",

            }

        ),

    )



    segundo_nombre = forms.CharField(

        label="Segundo nombre",

        max_length=MAX_NOMBRE,

        required=False,

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_NOMBRE),



                "placeholder":

                    "Opcional - máximo 30",

            }

        ),

    )



    primer_apellido = forms.CharField(

        label="Primer apellido",

        min_length=2,

        max_length=MAX_APELLIDO,

        required=True,

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_APELLIDO),



                "autocomplete":

                    "family-name",



                "placeholder":

                    "Máximo 30 caracteres",

            }

        ),

    )



    segundo_apellido = forms.CharField(

        label="Segundo apellido",

        max_length=MAX_APELLIDO,

        required=False,

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_APELLIDO),



                "placeholder":

                    "Opcional - máximo 30",

            }

        ),

    )



    email = forms.EmailField(

        label="Correo electrónico",

        max_length=MAX_EMAIL,

        required=True,

        widget=forms.EmailInput(

            attrs={

                "maxlength":

                    str(MAX_EMAIL),



                "autocomplete":

                    "email",



                "placeholder":

                    "ejemplo@correo.com",

            }

        ),

    )



    tipo_documento = forms.ChoiceField(

        label="Tipo de documento",

        choices=TIPOS_DOCUMENTO,

        required=True,

    )



    documento = forms.CharField(

        label="Número de documento",

        max_length=MAX_DOCUMENTO,

        required=True,

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_DOCUMENTO),



                "inputmode":

                    "numeric",



                "autocomplete":

                    "off",



                "placeholder":

                    "Solo números",

            }

        ),

    )



    indicativo_pais = forms.ChoiceField(

        label="Indicativo del país",

        choices=INDICATIVOS_PAIS,

        required=True,

        initial="+57",

    )



    celular = forms.CharField(

        label="Número de celular",

        max_length=MAX_CELULAR,

        required=True,

        widget=forms.TextInput(

            attrs={

                "maxlength":

                    str(MAX_CELULAR),



                "inputmode":

                    "numeric",



                "autocomplete":

                    "tel",



                "placeholder":

                    "Número sin indicativo",

            }

        ),

    )



    class Meta:



        model = User



        fields = [

            "username",

            "email",

        ]



    def __init__(

        self,

        *args,

        **kwargs,

    ):



        super().__init__(

            *args,

            **kwargs,

        )



        self.order_fields([

            "username",

            "primer_nombre",

            "segundo_nombre",

            "primer_apellido",

            "segundo_apellido",

            "email",

            "tipo_documento",

            "documento",

            "indicativo_pais",

            "celular",

        ])



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

            "indicativo_pais"

        ].widget.attrs[

            "class"

        ] = "form-select"



    # =====================================================

    # USUARIO

    # =====================================================



    def clean_username(self):



        username = (

            self.cleaned_data.get(

                "username"

            )

            or ""

        ).strip()



        if len(username) < 4:



            raise ValidationError(

                "El usuario debe contener "

                "mínimo 4 caracteres."

            )



        if len(username) > MAX_USERNAME:



            raise ValidationError(

                "El usuario no puede superar "

                "los 30 caracteres."

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

    # PRIMER NOMBRE

    # =====================================================



    def clean_primer_nombre(self):



        return validar_parte_nombre(

            self.cleaned_data.get(

                "primer_nombre"

            ),

            "El primer nombre",

            obligatorio=True,

            permitir_espacios=False,

            max_length=MAX_NOMBRE,

        )



    # =====================================================

    # SEGUNDO NOMBRE

    # =====================================================



    def clean_segundo_nombre(self):



        return validar_parte_nombre(

            self.cleaned_data.get(

                "segundo_nombre"

            ),

            "El segundo nombre",

            obligatorio=False,

            permitir_espacios=False,

            max_length=MAX_NOMBRE,

        )



    # =====================================================

    # PRIMER APELLIDO

    # =====================================================



    def clean_primer_apellido(self):



        return validar_parte_nombre(

            self.cleaned_data.get(

                "primer_apellido"

            ),

            "El primer apellido",

            obligatorio=True,

            permitir_espacios=True,

            max_length=MAX_APELLIDO,

        )



    # =====================================================

    # SEGUNDO APELLIDO

    # =====================================================



    def clean_segundo_apellido(self):



        return validar_parte_nombre(

            self.cleaned_data.get(

                "segundo_apellido"

            ),

            "El segundo apellido",

            obligatorio=False,

            permitir_espacios=True,

            max_length=MAX_APELLIDO,

        )



    # =====================================================

    # CORREO

    # =====================================================



    def clean_email(self):



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



    def clean_documento(self):



        tipo_documento = (

            self.cleaned_data.get(

                "tipo_documento"

            )

        )



        documento = validar_documento(

            tipo_documento,

            self.cleaned_data.get(

                "documento"

            ),

        )



        if documento_ya_registrado(

            tipo_documento,

            documento,

        ):



            raise ValidationError(

                "Ya existe una cuenta con "

                "esa combinación de tipo "

                "y número de documento."

            )



        return documento



    # =====================================================

    # NÚMERO DE CELULAR

    # =====================================================



    def clean_celular(self):



        celular = (

            self.cleaned_data.get(

                "celular"

            )

            or ""

        ).strip()



        indicativo = (

            self.cleaned_data.get(

                "indicativo_pais"

            )

            or ""

        ).strip()



        if not celular:



            raise ValidationError(

                "El número de celular "

                "es obligatorio."

            )



        if not celular.isdigit():



            raise ValidationError(

                "El número de celular debe "

                "contener únicamente dígitos. "

                "No incluya +, espacios, "

                "guiones ni paréntesis."

            )



        if indicativo == "+57":



            if len(celular) != 10:



                raise ValidationError(

                    "Para Colombia (+57), "

                    "el número de celular debe "

                    "contener exactamente "

                    "10 dígitos."

                )



        else:



            if len(celular) < 6:



                raise ValidationError(

                    "El número internacional "

                    "debe contener mínimo "

                    "6 dígitos."

                )



            digitos_indicativo = (

                indicativo.replace(

                    "+",

                    "",

                )

            )



            if (

                len(digitos_indicativo)

                + len(celular)

                > 15

            ):



                raise ValidationError(

                    "La combinación del indicativo "

                    "y el número es demasiado larga."

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