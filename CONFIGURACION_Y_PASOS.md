# Actualización del proyecto Reservas - contraseña temporal automática

## Cambios incluidos

- `Reservas` incluye `tipo_documento`, `documento` y una relación opcional `cliente` con `django.contrib.auth.User`.
- El campo interno `cancha` se conserva; en pantalla se muestra como **Tipo de cancha**.
- Tipos de documento permitidos: **Tarjeta de Identidad (TI)** y **Cédula de Ciudadanía (CC)**.
- Perfil de cliente registrado (`PerfilCliente`).
- Registro, login, logout, perfil e historial de reservas para clientes.
- Un cliente puede tener múltiples reservas.
- Login administrativo con autenticación segura de Django.
- Recuperación de contraseña por token para cliente y administrador.
- Exportación Excel con tipo de documento, documento y usuario registrado/invitado.
- **Nueva política de contraseña temporal automática para clientes y administradores.**

## Nueva política de contraseña

### Cliente

Al registrar un cliente, el formulario **no solicita contraseña**. El sistema:

1. crea automáticamente una contraseña temporal aleatoria;
2. guarda únicamente el hash de esa contraseña mediante `set_password()`;
3. muestra la contraseña temporal una sola vez después del registro;
4. intenta enviarla también al correo si el backend de correo está configurado;
5. marca la cuenta con `debe_cambiar_password=True`;
6. al primer inicio de sesión obliga al cliente a crear una contraseña personal antes de acceder a Mi cuenta, Mis reservas o realizar una reserva autenticada.

### Administrador

Los administradores también utilizan contraseña temporal automática. Para administradores existentes use `migrar_admin_legacy`; para administradores nuevos use `crear_administrador`.

La contraseña temporal se muestra una sola vez en la consola y **no queda almacenada en texto plano**.

## 1. Reemplazar/añadir archivos

Copiar los archivos de `webapp/` a la aplicación `webapp` del proyecto y los HTML de `templates/` a la carpeta de templates.

Archivos nuevos importantes:

- `templates/registro_cliente_exitoso.html`
- `templates/cambiar_password_inicial.html`
- `webapp/management/commands/crear_administrador.py`

## 2. Conectar las URL de la aplicación

Si `Reservas/urls.py` todavía no incluye las URLs de `webapp`, debe quedar conceptualmente así:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('webapp.urls')),
]
```

## 3. Crear migraciones

```bash
python manage.py makemigrations webapp
python manage.py migrate
```

La migración creará también el modelo `EstadoAcceso`, utilizado para saber si una cuenta debe cambiar su contraseña temporal.

Los campos nuevos de las reservas aceptan vacío en registros antiguos para no obligar a inventar documentos históricos. Las nuevas reservas sí los validan como obligatorios.

## 4. Migrar administradores anteriores

Después de aplicar las migraciones:

```bash
python manage.py migrar_admin_legacy
```

El comando:

- copia o actualiza cada administrador del modelo antiguo `Login`;
- lo marca como `is_staff=True`;
- **descarta el uso de la contraseña antigua para el nuevo acceso**;
- genera una contraseña temporal aleatoria;
- guarda únicamente su hash;
- imprime la contraseña temporal una sola vez en consola;
- obliga al administrador a cambiarla en su primer login.

Ejemplo de salida:

```text
admin: actualizado | contraseña temporal: X7m#P8qR2@kL
```

Debe copiar esa contraseña y entregarla al administrador correspondiente.

## 5. Crear un administrador nuevo

No es necesario definir manualmente una contraseña. Use:

```bash
python manage.py crear_administrador admin admin@correo.com
```

Opcionalmente:

```bash
python manage.py crear_administrador admin admin@correo.com --nombre Henry --apellido Gil --superusuario
```

El comando mostrará la contraseña temporal una sola vez y la cuenta quedará obligada a cambiarla en el primer ingreso.

## 6. Configurar correo

### Desarrollo / pruebas

En `Reservas/settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@futbolygol.local'
```

Con el backend de consola:

- los enlaces de recuperación por token aparecen en la consola;
- el correo con la contraseña temporal del cliente también aparece en la consola;
- la contraseña igualmente se muestra una sola vez en la pantalla posterior al registro.

### Correo real

Para producción configure SMTP mediante variables de entorno. No guarde contraseñas de correo en el repositorio.

## 7. Ejecutar

```bash
python manage.py runserver
```

## Flujo resultante

### Invitado

Inicio -> Reservar -> datos personales + TI/CC + documento + Tipo de cancha -> reserva sin historial privado.

### Cliente registrado

Registro -> sistema genera contraseña temporal -> muestra/envía contraseña -> Login con contraseña temporal -> cambio obligatorio de contraseña -> Mi cuenta -> Nueva reserva / Mis reservas.

Si posteriormente olvida su contraseña: Recuperar contraseña -> correo -> token -> nueva contraseña.

### Administrador existente

`migrar_admin_legacy` -> sistema genera contraseña temporal -> Login administrador -> cambio obligatorio -> listado de reservas -> actualizar pago -> exportar Excel.

### Administrador nuevo

`crear_administrador` -> contraseña temporal automática -> Login -> cambio obligatorio -> módulo administrativo.

## Seguridad

- Las contraseñas temporales y definitivas se guardan mediante el sistema de hashing de Django.
- La contraseña temporal no se almacena en `EstadoAcceso`, `PerfilCliente` ni otro modelo propio.
- `EstadoAcceso` guarda únicamente un booleano que indica si el usuario debe cambiar la contraseña.
- La recuperación de contraseña continúa usando tokens de Django.

## Actualización V3 - registro administrador y validación de documento

### Documento
- Tarjeta de Identidad (TI): 10 a 11 dígitos.
- Cédula de Ciudadanía (CC): 6 a 10 dígitos.
- Solo se permiten números seguidos. No se aceptan puntos, comas, espacios, guiones ni letras.
- La misma validación se aplica al registro del cliente y al formulario de reserva.

### Registro de administrador
La URL `administrador/registro/` permite crear un nuevo administrador, pero por seguridad solo puede abrirla un administrador ya autenticado.
El sistema genera una contraseña temporal automáticamente y obliga al nuevo administrador a cambiarla en el primer acceso.
Para crear el primer administrador se conserva el comando:

```powershell
python manage.py crear_administrador admin admin@correo.com
```

### Error MySQL/MariaDB 2013: Lost connection to server during query
Este error significa que Django perdió la conexión con MySQL/MariaDB mientras consultaba la base de datos. Antes de probar el registro:
1. Verifique que MySQL esté iniciado en XAMPP.
2. Reinicie MySQL si estaba iniciado pero el error continúa.
3. Compruebe la conexión con `python manage.py check` y `python manage.py migrate`.
4. La V3 reintenta una vez las consultas cortas de validación de correo/documento y muestra un mensaje en el formulario si la conexión vuelve a fallar, en vez de generar un error 500.

En `Reservas/settings.py` se recomienda habilitar modo estricto:

```python
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["init_command"] = "SET sql_mode='STRICT_TRANS_TABLES'"
DATABASES["default"]["CONN_MAX_AGE"] = 0
```
