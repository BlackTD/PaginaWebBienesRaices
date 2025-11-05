import os

from flask import Flask, current_app, flash, redirect, render_template, request, session, url_for
from flask_migrate import Migrate

from config import Config
from forms import LoginForm, RegistrationForm
from models import Property, User, db
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm(request.form if request.method == 'POST' else None)
        captcha_enabled = bool(
            current_app.config.get('CAPTCHA_SITE_KEY')
            and current_app.config.get('CAPTCHA_SECRET_KEY')
        )

        if form.validate_on_submit():
            email = form.email.data.strip().lower()
            confirm_email = form.confirm_email.data.strip().lower()
            form.email.data = email
            form.confirm_email.data = confirm_email
            name = form.name.data.strip() if form.name.data else None
            password = form.password.data

            min_length = current_app.config.get('MIN_PASSWORD_LENGTH', 8)
            if len(password) < min_length:
                form.password.errors.append(
                    f'La contraseña debe tener al menos {min_length} caracteres.'
                )
            elif User.query.filter_by(email=email).first():
                form.email.errors.append('Ya existe una cuenta asociada a este correo.')
            else:
                password_hash = generate_password_hash(password)
                user = User(email=email, password_hash=password_hash, name=name)
                db.session.add(user)
                db.session.commit()
                flash('Cuenta creada correctamente. Ahora puedes iniciar sesión.')
                return redirect(url_for('login'))

        return render_template('register.html', form=form, captcha_enabled=captcha_enabled)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm(request.form if request.method == 'POST' else None)

        if form.validate_on_submit():
            email = form.email.data.strip().lower()
            form.email.data = email
            password = form.password.data
            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password_hash, password):
                form.password.errors.append('Correo o contraseña inválidos. Intenta nuevamente.')
            elif not user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador para reactivarla.', 'warning')
            else:
                session['logged_in'] = True
                session['user_id'] = user.id
                session['user_name'] = user.name or user.email
                session['user_email'] = user.email
                flash('Inicio de sesión exitoso.')
                return redirect(url_for('index'))

        return render_template('login.html', form=form)

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
