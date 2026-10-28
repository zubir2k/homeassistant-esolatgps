"""Fixtures for eSolat GPS tests."""
import json
from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


@pytest.fixture(autouse=True)
def no_http_server():
    """The card needs the http and frontend components; don't open a real port."""
    with patch("homeassistant.components.http.HomeAssistantHTTP.start"):
        yield


@pytest.fixture(autouse=True)
def no_aiodns():
    """Mocked sessions still build a connector; keep aiodns from leaving a pycares thread."""
    with patch("aiohttp.connector.DefaultResolver", aiohttp.ThreadedResolver):
        yield


@pytest.fixture(autouse=True)
def mock_http(aioclient_mock):
    """Every web request goes to aioclient_mock; tests register the responses they need."""
    return aioclient_mock
