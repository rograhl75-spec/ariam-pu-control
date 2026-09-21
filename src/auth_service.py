"""Serviço de autenticação com hash PBKDF2."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import secrets


@dataclass(frozen=True)
class AuthResult:
    """Resultado da autenticação."""

    authenticated: bool
    role: str = "operador"


class AuthService:
    """Autenticação de usuários com hash armazenado."""

    def __init__(self, users: dict[str, dict[str, str]]):
        self.users = users

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> str:
        """Gera hash determinístico no formato pbkdf2_sha256."""
        if salt is None:
            salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
        return f"pbkdf2_sha256$260000${salt}${digest}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Verifica senha contra hash PBKDF2."""
        try:
            algorithm, rounds, salt, digest = stored_hash.split("$", 3)
            rounds_int = int(rounds)
        except ValueError:
            return False

        if algorithm != "pbkdf2_sha256":
            return False

        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds_int).hex()
        return hmac.compare_digest(computed, digest)

    def authenticate(self, username: str, password: str) -> AuthResult:
        """Autentica usuário e retorna perfil."""
        user_data = self.users.get(username.strip())
        if not user_data:
            return AuthResult(authenticated=False)

        ok = self.verify_password(password, user_data.get("password_hash", ""))
        if not ok:
            return AuthResult(authenticated=False)
        return AuthResult(authenticated=True, role=user_data.get("role", "operador"))
