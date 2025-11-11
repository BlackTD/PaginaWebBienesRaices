from __future__ import annotations

import copy
import re
import secrets
from collections import OrderedDict
from typing import Dict, Iterable, List, Optional as TypingOptional

import requests
from flask import current_app, request, session
from markupsafe import Markup, escape


class ValidationError(Exception):
    """Simple validation error used by the custom form system."""


class Label:
    def __init__(self, text: str) -> None:
        self.text = text


class Field:
    def __init__(
        self,
        label: str,
        *,
        validators: TypingOptional[Iterable] = None,
        input_type: str = 'text',
        placeholder: str = '',
    ) -> None:
        self.label = Label(label)
        self.validators = list(validators or [])
        self.input_type = input_type
        self.placeholder = placeholder
        self.name = ''
        self.id = ''
        self.data: TypingOptional[str] = None
        self.errors: List[str] = []
        self.form: TypingOptional['BaseForm'] = None
        self.flags: Dict[str, bool] = {}

    def bind(self, form: 'BaseForm', name: str) -> 'Field':
        bound = copy.copy(self)
        bound.label = Label(self.label.text)
        bound.validators = list(self.validators)
        bound.name = name
        bound.id = f'id_{name}'
        bound.form = form
        bound.errors = []
        bound.flags = {}
        return bound

    def process(self, formdata: TypingOptional[Dict[str, str]]) -> None:
        if formdata is not None and self.name in formdata:
            raw_value = formdata.get(self.name, '')
            if isinstance(raw_value, str):
                self.data = raw_value.strip()
            else:
                self.data = raw_value
        else:
            self.data = ''

    def _value(self) -> str:
        return str(self.data or '')

    def _should_include_value(self) -> bool:
        return self.input_type not in {'password', 'submit'}

    def __call__(self, **kwargs) -> Markup:
        attrs = {'type': self.input_type, 'name': self.name, 'id': self.id}
        if self.placeholder:
            attrs['placeholder'] = self.placeholder
        attrs.update(kwargs)
        if 'class_' in attrs:
            attrs['class'] = attrs.pop('class_')
        if self._should_include_value():
            attrs.setdefault('value', self._value())
        attr_html = ' '.join(f"{key}='{escape(str(value))}'" for key, value in attrs.items())
        return Markup(f'<input {attr_html}>')

    def __html__(self) -> str:
        return str(self())


class PasswordField(Field):
    def __init__(self, label: str, *, validators: TypingOptional[Iterable] = None) -> None:
        super().__init__(label, validators=validators, input_type='password')

    def process(self, formdata: TypingOptional[Dict[str, str]]) -> None:
        if formdata is not None and self.name in formdata:
            raw_value = formdata.get(self.name, '')
            self.data = raw_value if isinstance(raw_value, str) else raw_value
        else:
            self.data = ''

    def __call__(self, **kwargs) -> Markup:
        attrs = {'type': self.input_type, 'name': self.name, 'id': self.id}
        attrs.update(kwargs)
        if 'class_' in attrs:
            attrs['class'] = attrs.pop('class_')
        attr_html = ' '.join(f"{key}='{escape(str(value))}'" for key, value in attrs.items())
        return Markup(f'<input {attr_html}>')


class SubmitField(Field):
    def __init__(self, label: str) -> None:
        super().__init__(label, input_type='submit')

    def __call__(self, **kwargs) -> Markup:
        attrs = {'type': 'submit', 'name': self.name, 'id': self.id}
        attrs.update(kwargs)
        if 'class_' in attrs:
            attrs['class'] = attrs.pop('class_')
        attr_html = ' '.join(f"{key}='{escape(str(value))}'" for key, value in attrs.items())
        return Markup(f"<button {attr_html}>{escape(self.label.text)}</button>")


class CSRFTokenField(Field):
    def __init__(self) -> None:
        super().__init__('', input_type='hidden')


class HiddenField(Field):
    def __init__(self, label: str = '', *, validators: TypingOptional[Iterable] = None) -> None:
        super().__init__(label, validators=validators, input_type='hidden')

    def _should_include_value(self) -> bool:
        return False


class BaseFormMeta(type):
    def __new__(mcls, name, bases, attrs):
        declared_fields = OrderedDict()
        for base in reversed(bases):
            if hasattr(base, '_declared_fields'):
                declared_fields.update(base._declared_fields)
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                declared_fields[key] = value
                attrs.pop(key)
        attrs['_declared_fields'] = declared_fields
        return super().__new__(mcls, name, bases, attrs)


class BaseForm(metaclass=BaseFormMeta):
    def __init__(self, formdata: TypingOptional[Dict[str, str]] = None) -> None:
        self._fields: OrderedDict[str, Field] = OrderedDict()
        for name, unbound in self._declared_fields.items():
            bound = unbound.bind(self, name)
            bound.process(formdata)
            setattr(self, name, bound)
            self._fields[name] = bound
        self.csrf_token = CSRFTokenField().bind(self, 'csrf_token')
        if request.method == 'POST':
            self.csrf_token.process(formdata)
        else:
            self.csrf_token.data = self._ensure_csrf_token()
        self.csrf_token.errors = []
        self._fields['csrf_token'] = self.csrf_token

    def _ensure_csrf_token(self) -> str:
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(16)
            session['_csrf_token'] = token
        return token

    def __getitem__(self, name: str) -> Field:
        return self._fields[name]

    @property
    def data(self) -> Dict[str, str]:
        return {
            name: field.data or ''
            for name, field in self._fields.items()
            if not isinstance(field, (SubmitField, CSRFTokenField))
        }

    def validate_on_submit(self) -> bool:
        if request.method != 'POST':
            return False
        return self.validate()

    def validate(self) -> bool:
        valid = True
        for field in self._fields.values():
            if isinstance(field, (SubmitField, CSRFTokenField)):
                continue
            field.errors = []
            optional_empty = False
            for validator in field.validators:
                if isinstance(validator, OptionalValidator):
                    optional_empty = validator(self, field)
                    continue
                if optional_empty and not field.data:
                    continue
                try:
                    validator(self, field)
                except ValidationError as exc:
                    field.errors.append(str(exc))
            if field.errors:
                valid = False
        if request.method == 'POST':
            submitted = self.csrf_token.data or ''
            expected = session.get('_csrf_token') or self._ensure_csrf_token()
            self.csrf_token.errors = []
            if not submitted or submitted != expected:
                self.csrf_token.errors.append(
                    'Token CSRF inválido. Recarga la página e inténtalo nuevamente.'
                )
                valid = False
        return valid


class OptionalValidator:
    def __call__(self, form: BaseForm, field: Field) -> bool:
        is_empty = not field.data
        if isinstance(field.data, str):
            is_empty = not field.data.strip()
        if is_empty:
            field.data = ''
        return is_empty


class DataRequired:
    def __init__(self, message: str | None = None) -> None:
        self.message = message or 'Este campo es obligatorio.'

    def __call__(self, form: BaseForm, field: Field) -> None:
        value = field.data
        if isinstance(value, str):
            value = value.strip()
            field.data = value
        if not value:
            raise ValidationError(self.message)


class Email:
    def __init__(self, message: str | None = None) -> None:
        self.message = message or 'Introduce un correo electrónico válido.'
        self.pattern = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

    def __call__(self, form: BaseForm, field: Field) -> None:
        value = field.data or ''
        if not self.pattern.match(value):
            raise ValidationError(self.message)


class Length:
    def __init__(self, min: int | None = None, max: int | None = None, message: str | None = None) -> None:
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form: BaseForm, field: Field) -> None:
        value = field.data or ''
        length = len(value)
        if self.min is not None and length < self.min:
            message = self.message or f'Debe tener al menos {self.min} caracteres.'
            raise ValidationError(message)
        if self.max is not None and length > self.max:
            message = self.message or f'No puede superar los {self.max} caracteres.'
            raise ValidationError(message)


class EqualTo:
    def __init__(self, fieldname: str, message: str | None = None) -> None:
        self.fieldname = fieldname
        self.message = message or 'Los valores deben coincidir.'

    def __call__(self, form: BaseForm, field: Field) -> None:
        other = form[self.fieldname]
        if (other.data or '') != (field.data or ''):
            raise ValidationError(self.message)


class Optional(OptionalValidator):
    """Marker for optional fields."""


class StringField(Field):
    def __init__(
        self,
        label: str,
        *,
        validators: TypingOptional[Iterable] = None,
        placeholder: str = '',
    ) -> None:
        super().__init__(label, validators=validators, input_type='text', placeholder=placeholder)
class GmailValidator:
    def __init__(self, message: str | None = None) -> None:
        self.message = message or 'Debes proporcionar una cuenta de Gmail válida.'

    def __call__(self, form: BaseForm, field: Field) -> None:
        value = (field.data or '').lower()
        if not value.endswith('@gmail.com'):
            raise ValidationError(self.message)


class UsernameValidator:
    def __init__(self, message: str | None = None) -> None:
        self.message = message or 'El nombre de usuario solo puede contener letras, números, puntos o guiones bajos.'
        self.pattern = re.compile(r'^[a-zA-Z0-9._-]+$')

    def __call__(self, form: BaseForm, field: Field) -> None:
        value = field.data or ''
        if not self.pattern.match(value):
            raise ValidationError(self.message)


class ReCaptchaValidator:
    VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

    def __init__(self, message: str | None = None) -> None:
        self.message = message or 'Debes completar el captcha.'

    def __call__(self, form: BaseForm, field: Field) -> None:
        site_key = current_app.config.get('CAPTCHA_SITE_KEY')
        secret_key = current_app.config.get('CAPTCHA_SECRET_KEY')
        if not (site_key and secret_key):
            field.flags['captcha_disabled'] = True
            field.data = ''
            return

        token = field.data or ''
        if not token:
            raise ValidationError(self.message)

        try:
            response = requests.post(
                self.VERIFY_URL,
                data={
                    'secret': secret_key,
                    'response': token,
                    'remoteip': request.remote_addr,
                },
                timeout=5,
            )
            payload = response.json()
        except Exception as exc:  # pragma: no cover - network failure path
            raise ValidationError('No se pudo verificar el captcha. Intenta nuevamente.') from exc

        if not payload.get('success'):
            raise ValidationError('Verificación de captcha inválida. Intenta nuevamente.')


class ReCaptchaField(HiddenField):
    def __init__(self) -> None:
        super().__init__('', validators=[ReCaptchaValidator()])

    def bind(self, form: 'BaseForm', name: str) -> 'Field':
        bound = super().bind(form, name)
        bound.name = 'g-recaptcha-response'
        bound.id = 'g-recaptcha-response'
        return bound

    def __call__(self, **kwargs) -> Markup:
        return Markup('')


class RegistrationForm(BaseForm):
    gmail = StringField(
        'Gmail',
        validators=[DataRequired(), Email(), GmailValidator(), Length(max=255)],
        placeholder='tuusuario@gmail.com',
    )
    username = StringField(
        'Nombre de usuario',
        validators=[DataRequired(), UsernameValidator(), Length(min=3, max=150)],
        placeholder='tuusuario',
    )
    password = PasswordField('Contraseña', validators=[DataRequired()])
    captcha = ReCaptchaField()
    submit = SubmitField('Crear cuenta')


class LoginForm(BaseForm):
    identifier = StringField(
        'Gmail o nombre de usuario',
        validators=[DataRequired(), Length(min=3, max=255)],
        placeholder='tuusuario@gmail.com o tuusuario',
    )
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')
