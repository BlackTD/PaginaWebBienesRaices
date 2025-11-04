from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)  # Bloqueo temporal
    is_permanently_blocked = db.Column(db.Boolean, default=False)  # Bloqueo permanente

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    main_image = db.Column(db.Text, nullable=True)  # Imagen principal
    repertory_images = db.Column(db.Text, nullable=True)  # Imágenes de repertorio (coma separada)
