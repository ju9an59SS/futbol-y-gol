from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from webapp.models import EstadoAcceso, Login


def generar_password_temporal():
    while True:
        password = get_random_string(
            12,
            allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789@#$%",
        )
        try:
            validate_password(password)
            return password
        except ValidationError:
            continue


class Command(BaseCommand):
    help = (
        "Migra administradores del modelo Login a Django, genera una contraseña "
        "temporal aleatoria y obliga a cambiarla en el primer ingreso."
    )

    def handle(self, *args, **options):
        if not Login.objects.exists():
            self.stdout.write(self.style.WARNING("No hay administradores en el modelo Login."))
            return

        self.stdout.write("IMPORTANTE: copie las contraseñas temporales ahora; no se guardan en texto plano.\n")

        for antiguo in Login.objects.all():
            user, creado = User.objects.get_or_create(
                username=antiguo.usuario,
                defaults={
                    "email": antiguo.correo,
                    "is_staff": True,
                },
            )
            user.is_staff = True
            if antiguo.correo:
                user.email = antiguo.correo

            password_temporal = generar_password_temporal()
            user.set_password(password_temporal)
            user.save()

            estado, _ = EstadoAcceso.objects.get_or_create(usuario=user)
            estado.debe_cambiar_password = True
            estado.save(update_fields=["debe_cambiar_password"])

            estado_usuario = "creado" if creado else "actualizado"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{antiguo.usuario}: {estado_usuario} | contraseña temporal: {password_temporal}"
                )
            )
