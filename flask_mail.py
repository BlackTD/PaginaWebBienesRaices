from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional

from flask import current_app


class Message:
    def __init__(
        self,
        subject: str = "",
        recipients: Optional[Iterable[str]] = None,
        body: str = "",
        sender: Optional[str] = None,
    ) -> None:
        self.subject = subject
        self.recipients = list(recipients or [])
        self.body = body
        self.sender = sender


class Mail:
    def __init__(self, app=None) -> None:
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        self.app = app
        app.extensions['mail'] = self

    def send(self, message: Message) -> None:
        app = self.app or current_app
        if not message.recipients:
            raise ValueError('Se requiere al menos un destinatario para enviar un correo.')

        if app.config.get('MAIL_SUPPRESS_SEND'):
            return

        sender = message.sender or app.config.get('MAIL_DEFAULT_SENDER')
        if not sender:
            raise RuntimeError('MAIL_DEFAULT_SENDER no está configurado.')

        host = app.config.get('MAIL_SERVER', 'localhost')
        port = app.config.get('MAIL_PORT', 25)
        username = app.config.get('MAIL_USERNAME')
        password = app.config.get('MAIL_PASSWORD')
        use_tls = app.config.get('MAIL_USE_TLS', False)
        use_ssl = app.config.get('MAIL_USE_SSL', False)

        email_message = EmailMessage()
        email_message['Subject'] = message.subject
        email_message['From'] = sender
        email_message['To'] = ', '.join(message.recipients)
        email_message.set_content(message.body)

        if use_ssl:
            server = smtplib.SMTP_SSL(host, port)
        else:
            server = smtplib.SMTP(host, port)

        try:
            if use_tls and not use_ssl:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(email_message)
        finally:
            try:
                server.quit()
            except Exception:  # pragma: no cover - cierre de conexión defensivo
                pass
