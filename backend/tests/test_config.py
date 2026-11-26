"""JWT secret startup validation."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_config_default_secret_is_rejected_outside_dev_mode():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="change-me-in-production")


def test_compose_default_secret_is_rejected_outside_dev_mode():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="local-development-secret-change-me")


def test_known_default_secret_is_allowed_in_dev_mode():
    settings = Settings(jwt_secret="change-me-in-production", environment="dev")
    assert settings.jwt_secret == "change-me-in-production"


def test_known_default_secret_is_allowed_with_explicit_opt_in():
    settings = Settings(jwt_secret="change-me-in-production", allow_insecure_jwt_secret=True)
    assert settings.allow_insecure_jwt_secret is True


def test_a_real_secret_is_accepted():
    settings = Settings(jwt_secret="a-strong-random-secret-for-tests")
    assert settings.environment == "production"
