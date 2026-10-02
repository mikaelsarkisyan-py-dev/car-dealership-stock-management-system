"""Accounts: sign-up / login rules and the users.json file (passwords are salted hashes)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import re
import secrets
import string
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
PBKDF2_ITERATIONS = 200_000


# ============================================================================
# User record
# ============================================================================

@dataclass(frozen=True)
class User:
    username: str
    first_name: str
    surname: str
    email: str
    salt: str = field(repr=False)
    password_hash: str = field(repr=False)
    iterations: int = field(repr=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.surname}"


# ============================================================================
# Storage (users.json)
# ============================================================================

class UserRepository:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _read(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as handle:
            return json.load(handle).get("users", [])

    def _write(self, records: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file first so a crash can't leave a half-written file.
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"users": records}, handle, indent=2, ensure_ascii=False)
        os.replace(tmp_name, self.path)

    def all(self) -> list[User]:
        return [User(**record) for record in self._read()]

    def get(self, username: str) -> User | None:
        wanted = username.strip().casefold()
        for user in self.all():
            if user.username.casefold() == wanted:
                return user
        return None

    def usernames(self) -> set[str]:
        return {user.username.casefold() for user in self.all()}

    def add(self, user: User) -> None:
        records = self._read()
        records.append(asdict(user))
        self._write(records)


# ============================================================================
# Rules and login service
# ============================================================================

_EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
_NAME_RE = re.compile(r"^[^\W\d_][^\W\d_ '\-]*([ '\-][^\W\d_]+)*$")  # letters, with inner space/'/-


class AuthError(Exception):
    """Carries one or more messages that are safe to show to the user."""

    def __init__(self, problems: str | list[str]):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("\n".join(self.problems))


# --------------------------------------------------------------- pure helpers
def password_problems(password: str) -> list[str]:
    """Everything wrong with a password (empty list means it is acceptable)."""
    problems = []
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        problems.append(
            f"be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters long"
        )
    if not any(c.islower() for c in password):
        problems.append("contain a lowercase letter")
    if not any(c.isupper() for c in password):
        problems.append("contain a capital letter")
    if not any(c.isdigit() for c in password):
        problems.append("contain a number")
    if not any(c in string.punctuation for c in password):
        problems.append("contain a special character")
    return problems


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def is_valid_name(name: str) -> bool:
    return bool(_NAME_RE.match(name))


def build_username(first_name: str, surname: str, number: int) -> str:
    """First letter of first name + surname + 4 digits, e.g. MLanner5671."""
    return f"{first_name[0].upper()}{''.join(surname.split())}{number:04d}"


def hash_password(password: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations).hex()


# -------------------------------------------------------------------- service
class AuthService:
    def __init__(self, users: UserRepository, rng: random.Random | None = None):
        self._users = users
        self._rng = rng or random.SystemRandom()

    def make_user(self, username: str, first_name: str, surname: str, email: str,
                  password: str) -> User:
        """Build a User with a freshly salted password hash (does not save it)."""
        salt = secrets.token_bytes(16)
        return User(
            username=username,
            first_name=first_name,
            surname=surname,
            email=email,
            salt=salt.hex(),
            password_hash=hash_password(password, salt, PBKDF2_ITERATIONS),
            iterations=PBKDF2_ITERATIONS,
        )

    def register(self, first_name: str, surname: str, email: str,
                 password: str, confirm_password: str) -> User:
        first_name, surname, email = first_name.strip(), surname.strip(), email.strip()

        errors = []
        if not is_valid_name(first_name):
            errors.append("Enter a valid first name.")
        if not is_valid_name(surname):
            errors.append("Enter a valid surname.")
        if not is_valid_email(email):
            errors.append("Enter a valid email address.")
        problems = password_problems(password)
        if problems:
            errors.append("Password must " + ", ".join(problems) + ".")
        elif password != confirm_password:
            errors.append("Passwords do not match.")
        if errors:
            raise AuthError(errors)

        taken = self._users.usernames()
        for _ in range(200):
            username = build_username(first_name, surname, self._rng.randint(1000, 9999))
            if username.casefold() not in taken:
                break
        else:
            raise AuthError("Could not generate a unique username. Please try again.")

        user = self.make_user(username, first_name, surname, email, password)
        self._users.add(user)
        return user

    def login(self, username: str, password: str) -> User:
        user = self._users.get(username)
        # Always hash, even for unknown users, so response time doesn't reveal which exist.
        salt = bytes.fromhex(user.salt) if user else b"\x00" * 16
        iterations = user.iterations if user else PBKDF2_ITERATIONS
        candidate = hash_password(password, salt, iterations)
        if user and hmac.compare_digest(candidate, user.password_hash):
            return user
        raise AuthError("Username or password is incorrect.")
