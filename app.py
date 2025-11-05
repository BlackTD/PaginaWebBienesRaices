import os
import smtplib
from email.message import EmailMessage

from flask import (
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_migrate import Migrate
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import Config
from models import Property, User, db
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    # Garantiza que las tablas existan al iniciar la aplicación en lugar de
    # evaluarlo en cada solicitud mediante un before_request costoso.
    with app.app_context():
        db.create_all()

    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    def send_email(subject: str, recipient: str, body: str) -> bool:
        mail_username = app.config.get('MAIL_USERNAME')
        mail_password = app.config.get('MAIL_PASSWORD')
        mail_sender = app.config.get('MAIL_SENDER') or mail_username
        mail_server = app.config.get('MAIL_SERVER')
        mail_port = app.config.get('MAIL_PORT')
        use_tls = app.config.get('MAIL_USE_TLS', True)
        subject_prefix = app.config.get('MAIL_SUBJECT_PREFIX', '').strip()

        if not mail_username or not mail_password or not mail_sender:
            app.logger.warning('El correo no se envió: configuración SMTP incompleta.')
            return False

        message = EmailMessage()
        formatted_subject = f"{subject_prefix} {subject}".strip()
        message['Subject'] = formatted_subject
        message['From'] = mail_sender
        message['To'] = recipient
        message.set_content(body)

        try:
            with smtplib.SMTP(mail_server, mail_port) as server:
                if use_tls:
                    server.starttls()
                server.login(mail_username, mail_password)
                server.send_message(message)
        except Exception as exc:  # pragma: no cover - depende del servidor SMTP
            app.logger.exception('Error enviando correo a %s', recipient, exc_info=exc)
            return False
        return True

    def send_confirmation_email(user: User) -> bool:
        token = serializer.dumps(user.email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        greeting = user.name or 'Hola'
        subject = 'Confirma tu correo electrónico'
        body = (
            f"{greeting},\n\n"
            "Gracias por registrarte en Bienes Raíces Boutique. Para activar tu cuenta, "
            f"haz clic en el siguiente enlace:\n{confirm_url}\n\n"
            "Si no solicitaste esta cuenta, puedes ignorar este mensaje.\n\n"
            "Saludos,\nEl equipo de Bienes Raíces Boutique"
        )
        return send_email(subject, user.email, body)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if session.get('logged_in'):
            return redirect(url_for('admin'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip() or None
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not email or '@' not in email:
                flash('Ingresa un correo electrónico válido.')
                return redirect(url_for('register'))

            if len(password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres.')
                return redirect(url_for('register'))

            if password != confirm_password:
                flash('Las contraseñas no coinciden.')
                return redirect(url_for('register'))

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                if existing_user.email_confirmed:
                    flash('Ya existe una cuenta registrada con ese correo. Inicia sesión.')
                    return redirect(url_for('login'))
                if send_confirmation_email(existing_user):
                    flash('Ya existe una cuenta sin confirmar. Te reenviamos el correo de activación.')
                else:
                    flash('Ya existe una cuenta pendiente de confirmar, pero no se pudo enviar el correo. Contacta al administrador.')
                return redirect(url_for('login'))

            password_hash = generate_password_hash(password)
            user = User(email=email, password_hash=password_hash, name=name)
            db.session.add(user)
            db.session.commit()

            if send_confirmation_email(user):
                flash('Registro exitoso. Revisa tu bandeja de entrada para confirmar tu correo.')
            else:
                flash('Tu cuenta fue creada, pero no se pudo enviar el correo de confirmación. Contacta al administrador.')

            return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/confirm/<token>')
    def confirm_email(token: str):
        max_age = current_app.config.get('MAIL_TOKEN_MAX_AGE', 60 * 60 * 24)
        try:
            email = serializer.loads(token, salt='email-confirm', max_age=max_age)
        except SignatureExpired:
            flash('El enlace de confirmación ha expirado. Solicita uno nuevo registrándote nuevamente.')
            return redirect(url_for('register'))
        except BadSignature:
            flash('El enlace de confirmación no es válido.')
            return redirect(url_for('register'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No se encontró una cuenta asociada a ese correo.')
            return redirect(url_for('register'))

        if user.email_confirmed:
            flash('Tu correo ya estaba confirmado. Puedes iniciar sesión.')
            return redirect(url_for('login'))

        user.email_confirmed = True
        db.session.commit()
        flash('¡Listo! Tu correo ha sido confirmado. Ya puedes iniciar sesión.')
        return redirect(url_for('login'))

    @app.route('/resend-confirmation', methods=['POST'])
    def resend_confirmation():
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Ingresa un correo válido para reenviar la confirmación.')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Si existe una cuenta asociada, recibirás un correo con instrucciones.')
            return redirect(url_for('login'))

        if user.email_confirmed:
            flash('Tu correo ya está confirmado. Puedes iniciar sesión directamente.')
            return redirect(url_for('login'))

        if send_confirmation_email(user):
            flash('Te enviamos un nuevo correo de confirmación.')
        else:
            flash('No se pudo enviar el correo de confirmación. Contacta al administrador.')
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if session.get('logged_in'):
            return redirect(url_for('admin'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password_hash, password):
                flash('Correo o contraseña incorrectos.')
                return redirect(url_for('login'))

            if not user.email_confirmed:
                flash('Debes confirmar tu correo electrónico antes de iniciar sesión.')
                return redirect(url_for('login'))

            session['logged_in'] = True
            session['user_id'] = user.id
            session['user_name'] = user.name or user.email
            session['user_email'] = user.email

            flash('Inicio de sesión exitoso.')
            return redirect(url_for('admin'))

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session_keys = [
            'logged_in',
            'user_id',
            'user_name',
            'user_email',
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
