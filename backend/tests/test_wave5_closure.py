"""Wave 5 closure: regression tests for the two judgement call fixes.

The backend half is SEC7/PG-S1: /docs, /redoc and /openapi.json must not
be served outside dev mode. The docs routes are chosen when the FastAPI
app is constructed from the environment, so each environment is
exercised in a fresh subprocess whose only job is to build the app under
a chosen ENVIRONMENT and report the status of the docs paths. A
subprocess is used on purpose: rebuilding the app in this process would
mean clearing the settings cache and reloading modules, which desyncs
the module level settings singletons other tests rely on (rate_limit
binds its settings at import). U9 is a frontend fix; it is covered by
the scripted browser check kept with the wave 5 proofs.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DOC_PATHS = ("/docs", "/redoc", "/openapi.json")

_PROBE = """
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
paths = ("/docs", "/redoc", "/openapi.json", "/health")
print(json.dumps({path: client.get(path).status_code for path in paths}))
"""


def _statuses_under_environment(environment: str) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "ENVIRONMENT": environment,
            "DATABASE_URL": "sqlite:////tmp/pg_docs_probe.db",
            "EVENT_BUS": "memory",
            "RATE_LIMIT_ENABLED": "false",
            "JWT_SECRET": "test-secret-for-local-tests-0123456789",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_docs_paths_are_404_in_production():
    statuses = _statuses_under_environment("production")
    for path in DOC_PATHS:
        assert statuses[path] == 404, path
    # The API itself is unaffected by the docs being unmounted.
    assert statuses["/health"] == 200


def test_docs_paths_are_200_in_dev():
    statuses = _statuses_under_environment("dev")
    for path in DOC_PATHS:
        assert statuses[path] == 200, path


def test_docs_paths_are_404_on_the_default_app(client):
    # The suite default environment is production (conftest never sets
    # ENVIRONMENT), so the app every other test uses serves no docs.
    for path in DOC_PATHS:
        response = client.get(path)
        assert response.status_code == 404, path
