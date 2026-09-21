import pytest

from src.validators import validate_required_columns


def test_validate_required_columns_ok():
    validate_required_columns(["A", "B"], {"A"})


def test_validate_required_columns_raises_for_missing():
    with pytest.raises(ValueError):
        validate_required_columns(["A"], {"A", "B"})
