# Bienes Raíces Boutique

Aplicación web construida con Flask para administrar el catálogo digital de la inmobiliaria **Carina Becerra Bienes Raíces**. La página combina un sitio público de marketing con un panel administrativo protegido que permite crear, actualizar y eliminar propiedades en la base de datos.

## Panorama técnico

- **Framework backend:** Flask con patrón application factory (`create_app`).
- **Persistencia:** SQLAlchemy + Flask-Migrate sobre SQLite por defecto (configurable vía `DATABASE_URL`).
- **Autenticación:** Registro e inicio de sesión tradicionales con contraseñas encriptadas (`werkzeug.security`). El inicio de sesión habilita sesiones seguras en Flask.
- **Seguridad adicional:**
  - CSRF token manual en el sistema de formularios.
  - Validación opcional con Google reCAPTCHA v2 en el registro (controlada por variables de entorno).
  - Política de longitud mínima de contraseña configurable (`MIN_PASSWORD_LENGTH`).
- **Frontend:** Plantillas Jinja2 con TailwindCSS desde CDN, tipografía de Google Fonts y componentes animados con IntersectionObserver.
- **Gestión de archivos:** Carga de imágenes al directorio `static/images/imagesProperty/` utilizando nombres saneados (`secure_filename`).

## Arquitectura de la aplicación

```
PaginaWebBienesRaices/
├── app.py               # Rutas HTTP, inicialización de Flask y lógica principal
├── models.py            # Modelos SQLAlchemy (User, Property)
├── forms.py             # Sistema de formularios personalizado con validadores y captcha
├── templates/           # Vistas HTML (sitio público + panel admin)
├── static/              # Recursos estáticos y carpeta de imágenes subidas
├── migrations/          # Scripts de migración de base de datos (Flask-Migrate)
├── config.py            # Configuración centralizada y variables de entorno
└── requirements.txt     # Dependencias de Python
```

## Funcionalidades clave

### Sitio público

- **Landing page** (`/`): hero animado, propuesta de valor, CTA a catálogo y formulario de contacto estilizado.
- **Catálogo dinámico** (`/catalogo`): grilla que muestra todas las propiedades registradas, con precio formateado y enlaces al detalle.
- **Detalle de propiedad** (`/property/<id>`): ficha completa que reutiliza la galería principal y el repertorio de imágenes.
- **Componentes responsivos:** navegación con menú hamburguesa, animaciones de entrada con IntersectionObserver, estilos “glassmorphism”.

### Autenticación y panel

- **Registro** (`/register`): campos de Gmail, usuario y contraseña validados manualmente. Opcionalmente exige reCAPTCHA.
- **Inicio de sesión** (`/login`): permite autenticación por Gmail o usuario. Almacena datos relevantes en sesión y respeta el estado `is_active` del usuario.
- **Panel administrativo** (`/adminis`): formulario protegido para crear nuevas propiedades con imagen principal obligatoria y galería múltiple opcional.
- **Edición de propiedades** (`/edit_property/<id>`): actualización de campos, reemplazo de imagen principal y combinación de galerías existentes con nuevas.
- **Eliminación** (`/delete_property/<id>`): endpoint POST protegido para remover registros.
- **Gestión de galería** (`/remove_repertory_image`): servicio JSON que permite borrar imágenes individuales tanto del disco como del registro SQL.

## Variables de entorno

Configura estas variables antes de iniciar la aplicación (por ejemplo en un archivo `.env` o exportándolas en tu shell):

```bash
export SECRET_KEY="clave-super-secreta"                  # Requerido
export DATABASE_URL="sqlite:///site.db"                 # Opcional, por defecto SQLite local
export MIN_PASSWORD_LENGTH="10"                         # Opcional, mínimo 8 caracteres si no se define
export CAPTCHA_SITE_KEY="tu-site-key"                   # Opcional, activa reCAPTCHA en registro
export CAPTCHA_SECRET_KEY="tu-secret-key"               # Opcional, valida reCAPTCHA en backend
```

> Si `CAPTCHA_SITE_KEY` y `CAPTCHA_SECRET_KEY` no están presentes, el formulario de registro omite el captcha automáticamente.

## Puesta en marcha local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app db upgrade   # Aplica migraciones y crea la base de datos
flask --app app run --debug
```

- Las imágenes cargadas desde el panel se guardan en `static/images/imagesProperty/` (se crea al vuelo si no existe).
- La base SQLite por defecto se genera en `instance/site.db`.

## Migraciones y mantenimiento

- Crear una nueva migración: `flask --app app db migrate -m "mensaje"`
- Aplicar migraciones pendientes: `flask --app app db upgrade`
- Revertir la última migración: `flask --app app db downgrade`

## Tests manuales sugeridos

1. Crear usuario mediante `/register` y validar correo duplicado, usuario duplicado y longitud de contraseña.
2. Iniciar sesión y verificar aparición del menú admin y flash messages.
3. Cargar una propiedad con varias imágenes y confirmar visualización en `/catalogo` y `/property/<id>`.
4. Editar la misma propiedad reemplazando la imagen principal y sumando nuevas imágenes al repertorio.
5. Eliminar una imagen desde el modal de galería (consumiendo `/remove_repertory_image`).

## Créditos

Proyecto creado como demostración de un flujo completo de gestión inmobiliaria con Flask, SQLAlchemy y un frontend responsivo moderno.
