"""Serviço seguro de envio de e-mails."""

from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText

from src.config import MailSettings


class EmailService:
    """Encapsula envio SMTP usando configuração segura."""

    def __init__(self, settings: MailSettings):
        self.settings = settings

    def send_email(self, to_email: str, subject: str, body: str) -> None:
        """Envia e-mail de texto simples via SMTP autenticado."""
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self.settings.username
        msg["To"] = to_email

        with smtplib.SMTP(self.settings.host, self.settings.port, timeout=15) as server:
            if self.settings.use_tls:
                server.starttls(context=ssl.create_default_context())
            server.login(self.settings.username, self.settings.password)
            server.sendmail(self.settings.username, [to_email], msg.as_string())
