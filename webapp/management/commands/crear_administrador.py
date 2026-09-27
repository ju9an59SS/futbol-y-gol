from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string

from webapp.models import EstadoAcceso


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
    help = "Crea un administrador con contraseña temporal automática y cambio obligatorio al primer ingreso."

    def add_arguments(self, parser):
        parser.add_argument("usuario", type=str)
        parser.add_argument("correo", type=str)
        parser.add_argument("--nombre", default="")
        parser.add_argument("--apellido", default="")
        parser.add_argument(
            "--superusuario",
            action="store_true",
            help="También asigna permisos de superusuario.",
        )

    def handle(self, *args, **options):
        usuario = options["usuario"].strip()
        correo = options["correo"].strip().lower()

        if User.objects.filter(username=usuario).exists():
            raise CommandError("Ya existe un usuario con ese nombre.")
        if User.objects.filter(email__iexact=correo).exists():
            raise CommandError("Ya existe un usuario con ese correo.")

        password_temporal = generar_password_temporal()
        user = User(
            username=usuario,
            email=correo,
            first_name=options["nombre"],
            last_name=options["apellido"],
            is_staff=True,
            is_superuser=options["superusuario"],
        )
        user.set_password(password_temporal)
        user.save()

        EstadoAcceso.objects.create(
            usuario=user,
            debe_cambiar_password=True,
        )

        self.stdout.write(self.style.SUCCESS("Administrador creado correctamente."))
        self.stdout.write(f"Usuario: {usuario}")
        self.stdout.write(self.style.WARNING(f"Contraseña temporal: {password_temporal}"))
        self.stdout.write("Esta contraseña se muestra una sola vez. Debe cambiarse en el primer ingreso.")
