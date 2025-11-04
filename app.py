from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, Property
from config import Config
import os
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar la base de datos
db.init_app(app)
migrate = Migrate(app, db)

@app.before_request
def create_tables():
    db.create_all()  # Crea las tablas si no existen

## Método para verificar si un usuario está bloqueado
def is_user_blocked(username):
    user = User.query.filter_by(name=username).first()
    if user and hasattr(user, 'is_blocked') and user.is_blocked:
        return True
    return False


# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(name=username).first()
        
        if user:
            # Revisar si el usuario está permanentemente bloqueado
            if user.is_permanently_blocked:
                flash("Tu cuenta está permanentemente bloqueada debido a múltiples intentos fallidos.")
                return render_template('login.html')
            
            # Revisar si el usuario está temporalmente bloqueado
            if user.is_blocked:
                lock_time = session.get(f'lock_time_{username}', 0)
                if lock_time and time.time() - lock_time < 30:
                    remaining_time = int(30 - (time.time() - lock_time))
                    flash(f"Usuario bloqueado temporalmente. Intenta nuevamente en {remaining_time} segundos.")
                    return render_template('login.html', username=username, remaining_time=remaining_time)
                else:
                    user.is_blocked = False
                    db.session.commit()  # Liberar el bloqueo temporal

            # Verificar la contraseña
            if user.password == password:
                session['logged_in'] = True
                session.pop(f'failed_attempts_{username}', None)  # Limpiar los intentos fallidos
                return redirect(url_for('index'))
            else:
                # Obtener los intentos fallidos almacenados en sesión
                failed_attempts = session.get(f'failed_attempts_{username}', 0)
                
                # Si ha fallado los primeros 3 intentos
                if failed_attempts < 3:
                    session[f'failed_attempts_{username}'] = failed_attempts + 1
                    remaining_attempts = 3 - (failed_attempts + 1)
                    flash(f"Credenciales incorrectas. Intentos restantes: {remaining_attempts}")
                    return render_template('login.html', username=username)

                # Después de los 3 primeros intentos, verificar si tiene intentos adicionales (1 o 2)
                if failed_attempts == 3:
                    session[f'lock_time_{username}'] = time.time()  # Registrar el tiempo de bloqueo temporal
                    user.is_blocked = True
                    db.session.commit()  # Guardar el cambio en el estado de bloqueo
                    session[f'failed_attempts_{username}'] = failed_attempts + 1
                    flash("Has fallado 4 veces. Ahora debes esperar 30 segundos para el siguiente intento.")
                    return render_template('login.html', username=username)

                # Después de los 4 intentos fallidos (3 iniciales + 1 adicional), permitir el último intento
                if failed_attempts == 4:
                    session[f'lock_time_{username}'] = time.time()  # Registrar el tiempo de bloqueo temporal
                    user.is_blocked = True
                    db.session.commit()  # Guardar el cambio en el estado de bloqueo
                    session[f'failed_attempts_{username}'] = failed_attempts + 1
                    flash("Has fallado 5 veces. Ahora debes esperar 30 segundos para el siguiente intento.")
                    return render_template('login.html', username=username)

                # Si el usuario falló el último intento (5 intentos en total)
                if failed_attempts >= 5:
                    user.is_permanently_blocked = True  # Bloquear permanentemente al usuario
                    db.session.commit()  # Guardar los cambios en la base de datos
                    flash("Has fallado todos los intentos. Tu cuenta está bloqueada permanentemente.")
                    return render_template('login.html')

        # Si el usuario no existe
        flash("Usuario no encontrado.")
        return render_template('login.html')

    return render_template('login.html')

# Ruta para el panel de administración, solo accesible si el usuario está logueado
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
        
        # Manejar la imagen principal
        main_image_file = request.files.get('main_image')
        if main_image_file and main_image_file.filename != '':  # Verificar que se haya seleccionado un archivo
            main_filename = secure_filename(main_image_file.filename)
            main_image_path = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            main_image_file.save(main_image_path)
            main_image_url = f'static/images/imagesProperty/{main_filename}'
        else:
            main_image_url = None
        
        # Manejar las imágenes de repertorio (ahora es opcional)
        repertory_files = request.files.getlist('repertory_images')
        repertory_urls = []
        if repertory_files:  # Solo procesar si se suben imágenes
            for file in repertory_files:
                if file.filename != '':  # Verificar que se haya seleccionado un archivo
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                    file.save(file_path)
                    repertory_urls.append(f'static/images/imagesProperty/{filename}')
        
        repertory_images = ",".join(repertory_urls)  # Convertir la lista a una cadena separada por comas
        
        # Crear la nueva propiedad
        new_property = Property(
            name=name,
            description=description,
            location=location,
            price=price,
            main_image=main_image_url,
            repertory_images=repertory_images if repertory_images else None  # Si no hay imágenes, se guarda None
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
        # Obtener los nuevos datos
        name = request.form['name']
        description = request.form['description']
        location = request.form['location']
        price = float(request.form['price'])
        
        # Manejar la imagen principal
        main_image_file = request.files.get('main_image')
        if main_image_file and main_image_file.filename:
            main_filename = secure_filename(main_image_file.filename)
            main_image_path = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
            main_image_file.save(main_image_path)
            main_image_url = f'static/images/imagesProperty/{main_filename}'
        else:
            main_image_url = property.main_image  # Mantener la imagen original si no se sube una nueva

        # Para agregar nuevas imágenes sin eliminar las anteriores
        repertory_files = request.files.getlist('repertory_images')
        repertory_urls = []
        if repertory_files:  # Solo procesar si se suben imágenes
            for file in repertory_files:
                if file.filename:  # Verificar si el archivo tiene un nombre (es decir, si se seleccionó un archivo)
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    repertory_urls.append(f'static/images/imagesProperty/{filename}')

        # Si ya existen imágenes de repertorio, agregamos las nuevas al final
        if property.repertory_images:
            repertory_urls = property.repertory_images.split(',') + repertory_urls

        # Guardar los cambios en la propiedad
        property.name = name
        property.description = description
        property.location = location
        property.price = price
        property.main_image = main_image_url
        property.repertory_images = ",".join(repertory_urls)  # Convertir lista en string separado por comas

        db.session.commit()
        return redirect(url_for('property_detail', property_id=property.id))
    
    return render_template('editProperty.html', property=property)
    
# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Eliminar la sesión
    return redirect(url_for('index'))

@app.route('/')
def index():
    featured_properties = Property.query.order_by(Property.id.desc()).limit(3).all()
    return render_template('index.html', featured_properties=featured_properties)

@app.route('/catalogo')
def catalogo():
    properties = Property.query.all()  # Obtener todas las propiedades
    return render_template('catalogo.html', properties=properties)

@app.route('/property/<int:property_id>')
def property_detail(property_id):
    # Obtener la propiedad específica por ID
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
        # Eliminar la imagen del sistema de archivos
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_to_remove.split('/')[-1])
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Eliminar la imagen de repertorio en la base de datos
        property = Property.query.filter(Property.repertory_images.like(f'%{image_to_remove}%')).first()
        if property:
            images = property.repertory_images.split(',')
            images = [img for img in images if img != image_to_remove]
            property.repertory_images = ','.join(images)
            db.session.commit()
            return {'success': True}
    
    return {'success': False}

if __name__ == '__main__':
    app.run(debug=True)
