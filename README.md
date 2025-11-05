# PaginaWebBienesRaices

Aplicación web desarrollada con Flask para la gestión de propiedades inmobiliarias.

## Autenticación moderna con proveedores externos

El panel administrativo ahora utiliza un flujo de inicio de sesión basado en OAuth 2.0.
Las cuentas se crean automáticamente al iniciar sesión con proveedores como Google o Apple.

### Variables de entorno necesarias

Crea un archivo `.env` o exporta las siguientes variables antes de ejecutar la aplicación:

```bash
export SECRET_KEY="clave-secreta-super-segura"
export GOOGLE_CLIENT_ID="tu-id-de-cliente.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="tu-clave-secreta"
# Opcional: solo si configuras Sign in with Apple
export APPLE_CLIENT_ID="com.tuempresa.app"
export APPLE_CLIENT_SECRET="clave-JWT-generada"
# Configuración SMTP para los correos de confirmación
export MAIL_SERVER="smtp.tudominio.com"
export MAIL_PORT=587
export MAIL_USERNAME="no-reply@tudominio.com"
export MAIL_PASSWORD="clave-del-correo"
export MAIL_USE_TLS=true
```

> **Nota:** Para Apple es necesario generar un `client_secret` firmado (JWT) desde el portal de desarrolladores de Apple.
> Puedes automatizar su creación y actualizar la variable de entorno periódicamente.

### Confirmación de correo electrónico

- Los administradores pueden registrarse con correo y contraseña desde `/register`.
- Se envía un enlace de verificación que expira a las 48 horas; hasta entonces el acceso estará bloqueado.
- Al confirmar el correo, la cuenta se activa y se inicia sesión de forma automática.
- El inicio de sesión en `/login` permite usar tanto credenciales locales como proveedores OAuth configurados.

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

