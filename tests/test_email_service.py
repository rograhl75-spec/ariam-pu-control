from src.config import MailSettings
from src.services.email_service import EmailService


class DummySMTP:
    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged = None
        self.sent = None
        self.tls_called = False
        self.ehlo_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self, context=None):
        self.tls_called = True
        return None

    def ehlo(self):
        self.ehlo_calls += 1

    def login(self, username, password):
        self.logged = (username, password)

    def sendmail(self, from_addr, to_addrs, msg):
        self.sent = (from_addr, to_addrs, msg)


def test_email_service_send(monkeypatch):
    smtp_instance = DummySMTP("", 0, 0)

    def _factory(host, port, timeout):
        smtp_instance.host = host
        smtp_instance.port = port
        smtp_instance.timeout = timeout
        return smtp_instance

    monkeypatch.setattr("smtplib.SMTP", _factory)

    service = EmailService(
        MailSettings("smtp.example.com", 587, "u@example.com", "secret")
    )
    service.send_email("dest@example.com", "Assunto", "Corpo")

    assert smtp_instance.logged == ("u@example.com", "secret")
    assert smtp_instance.sent is not None
    assert smtp_instance.tls_called is True
    assert smtp_instance.ehlo_calls >= 2


def test_email_service_send_without_tls(monkeypatch):
    smtp_instance = DummySMTP("", 0, 0)

    def _factory(host, port, timeout):
        smtp_instance.host = host
        smtp_instance.port = port
        smtp_instance.timeout = timeout
        return smtp_instance

    monkeypatch.setattr("smtplib.SMTP", _factory)

    service = EmailService(
        MailSettings("smtp.example.com", 587, "u@example.com", "secret", False)
    )
    service.send_email("dest@example.com", "Assunto", "Corpo")

    assert smtp_instance.tls_called is False
    assert smtp_instance.ehlo_calls == 1
