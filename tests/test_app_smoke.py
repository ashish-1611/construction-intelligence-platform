from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_renders_without_exceptions():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
