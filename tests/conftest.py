"""Shared fixtures that prevent tests from contacting a pySC server."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pySC2pyaml.deviceaccess import pySC_client


@pytest.fixture(autouse=True)
def client(monkeypatch):
    """Replace network reads and writes with isolated mocks for every test."""
    read = Mock(side_effect=AssertionError("Unexpected pySC read"))
    write = Mock()
    monkeypatch.setattr(pySC_client, "read", read)
    monkeypatch.setattr(pySC_client, "write", write)
    return SimpleNamespace(read=read, write=write)
