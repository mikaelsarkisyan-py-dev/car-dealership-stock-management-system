import random

import pytest

from auth import (AuthError, AuthService, build_username, is_valid_email, is_valid_name,
                  password_problems)


@pytest.fixture
def auth(user_repo):
    return AuthService(user_repo, rng=random.Random(1))


def register(auth, **overrides):
    data = dict(first_name="Max", surname="Lanner", email="max@example.com",
                password="Password123!", confirm_password="Password123!")
    data.update(overrides)
    return auth.register(**data)


def test_username_format():
    assert build_username("max", "Lanner", 5671) == "MLanner5671"
    assert build_username("Anna", "De Souza", 42) == "ADeSouza0042"


@pytest.mark.parametrize("password, expected_count", [
    ("Password123!", 0),
    ("short1!A", 0),
    ("short", 4),                 # length, capital, number, special
    ("alllowercase1!", 1),
    ("NoSpecial123", 1),
    ("NoNumber!!!", 1),
])
def test_password_rules(password, expected_count):
    assert len(password_problems(password)) == expected_count


def test_email_and_name_validation():
    assert is_valid_email("a.b+c@mail.co.uk") and not is_valid_email("nope@")
    assert is_valid_name("O'Brien") and is_valid_name("Anne-Marie") and not is_valid_name("R2D2")


def test_register_then_login(auth):
    user = register(auth)
    assert user.username.startswith("MLanner") and len(user.username) == len("MLanner") + 4
    assert auth.login(user.username, "Password123!") == user
    assert auth.login(user.username.lower(), "Password123!") == user  # case-insensitive ID


def test_password_is_not_stored_in_plain_text(auth, user_repo):
    register(auth)
    assert "Password123!" not in user_repo.path.read_text()


def test_wrong_password_and_unknown_user_give_same_error(auth):
    user = register(auth)
    with pytest.raises(AuthError) as wrong:
        auth.login(user.username, "Wrong123!")
    with pytest.raises(AuthError) as unknown:
        auth.login("Nobody0000", "Wrong123!")
    assert str(wrong.value) == str(unknown.value)


def test_register_reports_every_problem(auth):
    with pytest.raises(AuthError) as err:
        register(auth, first_name="", email="bad", password="weak", confirm_password="weak")
    assert len(err.value.problems) == 3  # name, email, password (rules combined)


def test_mismatched_confirmation(auth):
    with pytest.raises(AuthError, match="do not match"):
        register(auth, confirm_password="Different123!")


def test_usernames_are_unique(user_repo):
    class Stuck(random.Random):          # always returns the same 4 digits first
        calls = 0
        def randint(self, a, b):
            Stuck.calls += 1
            return 1234 if Stuck.calls == 1 else super().randint(a, b)

    auth = AuthService(user_repo, rng=Stuck(0))
    first, second = register(auth), register(auth)
    assert first.username == "MLanner1234"
    assert second.username != first.username
