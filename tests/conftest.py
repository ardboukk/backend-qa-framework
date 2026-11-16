import pytest


def pytest_collection_modifyitems(items):
    """Markers from folders, so a new test file can't forget them."""
    for item in items:
        path = item.path.as_posix()
        if "/tests/booker/" in path:
            item.add_marker(pytest.mark.external)
        if "/tests/services/" in path:
            # share server-side state (rate-limit counter, mock fault behaviour)
            item.add_marker(pytest.mark.serial)
