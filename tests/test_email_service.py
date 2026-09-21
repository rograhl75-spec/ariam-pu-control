from src.config import MailSettings
from src.services.email_service import EmailService


class DummySMTP:
    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged = None
        self.sent = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        return None

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
