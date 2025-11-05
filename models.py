from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_user_id = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    picture = db.Column(db.String(512), nullable=True)
    confirmation_token = db.Column(db.String(255), nullable=True, unique=True)
    confirmation_sent_at = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, nullable=False, server_default='0')
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint('provider', 'provider_user_id', name='uq_users_provider_identity'),
        db.UniqueConstraint('email', name='uq_users_email'),
    )


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    main_image = db.Column(db.Text, nullable=True)
    repertory_images = db.Column(db.Text, nullable=True)
