import os

class Config:
    SECRET_KEY = os.urandom(24)  # Para la seguridad de las sesiones
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'  # Ubicación de la base de datos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/images/imagesProperty')