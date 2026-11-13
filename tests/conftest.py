import pytest


def pytest_collection_modifyitems(items):
    """Every test under tests/booker/ is external: a new file there can't forget the marker."""
    for item in items:
        if "/tests/booker/" in item.path.as_posix():
            item.add_marker(pytest.mark.external)
