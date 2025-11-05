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
```

> **Nota:** Para Apple es necesario generar un `client_secret` firmado (JWT) desde el portal de desarrolladores de Apple.
> Puedes automatizar su creación y actualizar la variable de entorno periódicamente.

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

