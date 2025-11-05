# PaginaWebBienesRaices

Aplicación web desarrollada con Flask para la gestión de propiedades inmobiliarias.

## Registro con correo y confirmación por email

El panel administrativo utiliza un sistema propio de usuarios y contraseñas. Cada cuenta debe
confirmar su correo electrónico antes de poder iniciar sesión.

### Variables de entorno necesarias

Crea un archivo `.env` o exporta las siguientes variables antes de ejecutar la aplicación:

```bash
export SECRET_KEY="clave-secreta-super-segura"
export MAIL_USERNAME="tu-correo@gmail.com"
export MAIL_PASSWORD="clave-o-token-de-aplicacion"
# Opcionales: personaliza la entrega del correo
export MAIL_SERVER="smtp.gmail.com"
export MAIL_PORT=587
export MAIL_USE_TLS=true
export MAIL_SENDER="Bienes Raíces <tu-correo@gmail.com>"
export MAIL_SUBJECT_PREFIX="[Bienes Raíces Boutique]"
```

> **Importante:** Si utilizas Gmail habilita la verificación en dos pasos y genera una contraseña
> de aplicación para `MAIL_PASSWORD`. Sin credenciales válidas la aplicación no podrá enviar el
> correo de confirmación.

### Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

La base de datos SQLite se crea automáticamente en `instance/site.db`.

## Dependencias

Consulta `requirements.txt` para ver el listado completo de librerías necesarias.

