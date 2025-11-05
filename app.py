import os
from typing import Dict

from authlib.integrations.flask_client import OAuth
from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_migrate import Migrate

from config import Config
from models import Property, User, db
from werkzeug.utils import secure_filename


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    oauth = OAuth(app)
    providers: Dict[str, Dict[str, str]] = {}

    google_client_id = app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    if google_client_id and google_client_secret:
        oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile', 'prompt': 'select_account'},
        )
        providers['google'] = {
            'label': 'Continuar con Google',
            'icon': 'fa-brands fa-google',
            'class': 'bg-white text-slate-700 hover:bg-slate-50',
        }

    apple_client_id = app.config.get('APPLE_CLIENT_ID')
    apple_client_secret = app.config.get('APPLE_CLIENT_SECRET')
    if apple_client_id and apple_client_secret:
        oauth.register(
            name='apple',
            client_id=apple_client_id,
            client_secret=apple_client_secret,
            server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'name email',
                'response_mode': 'form_post',
                'response_type': 'code id_token',
            },
        )
        providers['apple'] = {
            'label': 'Continuar con Apple',
            'icon': 'fa-brands fa-apple',
            'class': 'bg-black text-white hover:bg-slate-800',
        }

    app.oauth = oauth
    app.config['ENABLED_OAUTH_PROVIDERS'] = providers

    @app.before_request
    def create_tables() -> None:
        db.create_all()

    def get_oauth_client(provider: str):
        client = app.oauth.create_client(provider)
        if not client:
            abort(404)
        return client

    @app.route('/login')
    def login():
        providers_meta = app.config.get('ENABLED_OAUTH_PROVIDERS', {})
        if not providers_meta:
            flash(
                'El inicio de sesión con terceros no está configurado. '
                'Asegúrate de definir las claves de Google o Apple en las variables de entorno.'
            )
        return render_template('login.html', oauth_providers=providers_meta)

    @app.route('/login/<provider>')
    def oauth_login(provider: str):
        client = get_oauth_client(provider)
        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        nonce = os.urandom(16).hex()
        session['oauth_nonce'] = nonce
        if provider == 'apple':
            return client.authorize_redirect(redirect_uri, response_mode='form_post', nonce=nonce)
        return client.authorize_redirect(redirect_uri, nonce=nonce)

    @app.route('/auth/<provider>', methods=['GET', 'POST'])
    def oauth_callback(provider: str):
        client = get_oauth_client(provider)
        token = client.authorize_access_token()
        user_info = None

        nonce = session.pop('oauth_nonce', None)

        try:
            if provider == 'google':
                user_info = client.parse_id_token(token, nonce=nonce)
                if not user_info:
                    response = client.get('userinfo')
                    user_info = response.json() if response else None
            elif provider == 'apple':
                user_info = client.parse_id_token(token, nonce=nonce)
            else:
                user_info = client.parse_id_token(token, nonce=nonce)
        except Exception as exc:  # pragma: no cover - depends on provider response
            current_app.logger.exception('OAuth callback error for %s', provider, exc_info=exc)
            flash('Ocurrió un error al validar la respuesta de autenticación.')
            return redirect(url_for('login'))

        if not user_info:
            flash('No se pudo obtener la información del usuario. Intenta nuevamente.')
            return redirect(url_for('login'))

        provider_user_id = str(user_info.get('sub') or user_info.get('id'))
        email = user_info.get('email')
        raw_name = user_info.get('name')
        if isinstance(raw_name, dict):
            name = ' '.join(
                part
                for part in [raw_name.get('firstName'), raw_name.get('lastName')]
                if part
            ).strip()
        else:
            name = raw_name

        if not name:
            name = (
                user_info.get('given_name')
                or user_info.get('fullName')
                or user_info.get('preferred_username')
            )
        picture = user_info.get('picture')

        if not provider_user_id or not email:
            flash('El proveedor no envió datos suficientes para crear la cuenta.')
            return redirect(url_for('login'))

        user = User.query.filter_by(provider=provider, provider_user_id=provider_user_id).first()

        if not user and email:
            user = User.query.filter_by(email=email.lower()).first()
            if user:
                user.provider = provider
                user.provider_user_id = provider_user_id

        if not user:
            user = User(
                provider=provider,
                provider_user_id=provider_user_id,
                email=email.lower(),
                name=name,
                picture=picture,
            )
            db.session.add(user)
        else:
            user.email = email.lower()
            if name:
                user.name = name
            if picture:
                user.picture = picture

        db.session.commit()

        session['logged_in'] = True
        session['user_id'] = user.id
        session['user_name'] = user.name or user.email
        session['user_email'] = user.email
        session['user_picture'] = user.picture

        flash('Inicio de sesión exitoso.')
        return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        session_keys = [
            'logged_in',
            'user_id',
            'user_name',
            'user_email',
            'user_picture',
        ]
        for key in session_keys:
            session.pop(key, None)
        flash('Sesión cerrada correctamente.')
        return redirect(url_for('index'))

    @app.route('/adminis')
    def admin():
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return render_template('adminis.html')

    @app.route('/add_property', methods=['GET', 'POST'])
    def add_property():
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            location = request.form['location']
            price = float(request.form['price'])

            main_image_file = request.files.get('main_image')
            if main_image_file and main_image_file.filename != '':
                main_filename = secure_filename(main_image_file.filename)
                main_image_path = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                main_image_file.save(main_image_path)
                main_image_url = f'static/images/imagesProperty/{main_filename}'
            else:
                main_image_url = None

            repertory_files = request.files.getlist('repertory_images')
            repertory_urls = []
            if repertory_files:
                for file in repertory_files:
                    if file.filename != '':
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        if not os.path.exists(app.config['UPLOAD_FOLDER']):
                            os.makedirs(app.config['UPLOAD_FOLDER'])
                        file.save(file_path)
                        repertory_urls.append(f'static/images/imagesProperty/{filename}')

            repertory_images = ','.join(repertory_urls)

            new_property = Property(
                name=name,
                description=description,
                location=location,
                price=price,
                main_image=main_image_url,
                repertory_images=repertory_images if repertory_images else None,
            )

            db.session.add(new_property)
            db.session.commit()

            return redirect(url_for('admin'))

        return render_template('adminis.html')

    @app.route('/edit_property/<int:property_id>', methods=['GET', 'POST'])
    def edit_property(property_id):
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        property = Property.query.get_or_404(property_id)

        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            location = request.form['location']
            price = float(request.form['price'])

            main_image_file = request.files.get('main_image')
            if main_image_file and main_image_file.filename:
                main_filename = secure_filename(main_image_file.filename)
                main_image_path = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
                main_image_file.save(main_image_path)
                main_image_url = f'static/images/imagesProperty/{main_filename}'
            else:
                main_image_url = property.main_image

            repertory_files = request.files.getlist('repertory_images')
            repertory_urls = []
            if repertory_files:
                for file in repertory_files:
                    if file.filename:
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        repertory_urls.append(f'static/images/imagesProperty/{filename}')

            if property.repertory_images:
                repertory_urls = property.repertory_images.split(',') + repertory_urls

            property.name = name
            property.description = description
            property.location = location
            property.price = price
            property.main_image = main_image_url
            property.repertory_images = ','.join(repertory_urls)

            db.session.commit()
            return redirect(url_for('property_detail', property_id=property.id))

        return render_template('editProperty.html', property=property)

    @app.route('/')
    def index():
        featured_properties = Property.query.order_by(Property.id.desc()).limit(3).all()
        return render_template('index.html', featured_properties=featured_properties)

    @app.route('/catalogo')
    def catalogo():
        properties = Property.query.all()
        return render_template('catalogo.html', properties=properties)

    @app.route('/property/<int:property_id>')
    def property_detail(property_id):
        property = Property.query.get_or_404(property_id)
        return render_template('propertyDetail.html', property=property)

    @app.route('/delete_property/<int:property_id>', methods=['POST'])
    def delete_property(property_id):
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        property_to_delete = Property.query.get_or_404(property_id)
        db.session.delete(property_to_delete)
        db.session.commit()
        return redirect(url_for('catalogo'))

    @app.route('/remove_repertory_image', methods=['POST'])
    def remove_repertory_image():
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        data = request.get_json()
        image_to_remove = data.get('image')

        if image_to_remove:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_to_remove.split('/')[-1])
            if os.path.exists(image_path):
                os.remove(image_path)

            property = Property.query.filter(Property.repertory_images.like(f'%{image_to_remove}%')).first()
            if property:
                images = property.repertory_images.split(',')
                images = [img for img in images if img != image_to_remove]
                property.repertory_images = ','.join(images)
                db.session.commit()
                return {'success': True}

        return {'success': False}

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
