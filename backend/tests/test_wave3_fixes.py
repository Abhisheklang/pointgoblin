"""Wave 3 vibe audit fixes: regression tests for the confirmed findings."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_sec1_env_example_placeholder_is_rejected_outside_dev_mode():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="replace-with-a-long-random-value")


def test_sec1_replacement_placeholder_is_rejected_outside_dev_mode():
    with pytest.raises(ValidationError):
        Settings(jwt_secret="REPLACE_ME_generate_a_random_secret_locally_do_not_commit")


def test_sec1_placeholders_still_work_in_dev_mode():
    settings = Settings(
        jwt_secret="replace-with-a-long-random-value",
        environment="dev",
    )
    assert settings.environment == "dev"
