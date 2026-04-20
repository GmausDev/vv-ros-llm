import pathlib

import pytest


@pytest.fixture()
def test_data_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Provide a temporary directory pre-seeded for test data."""
    return tmp_path
