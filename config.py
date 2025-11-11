import os


class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images', 'imagesProperty')

    MIN_PASSWORD_LENGTH = int(os.environ.get('MIN_PASSWORD_LENGTH', 8))
    CAPTCHA_SITE_KEY = os.environ.get('CAPTCHA_SITE_KEY')
    CAPTCHA_SECRET_KEY = os.environ.get('CAPTCHA_SECRET_KEY')
