import pytest

from lib.sec_helper import DictWithMissing


@pytest.mark.parametrize("d", [{}, {"a": 2, "b": "hello"}])
def test_DictWithMissing(d):
    d2 = DictWithMissing(d)
    for key, value in d2.items():
        assert d2[key] == value
    unknown_key = "thiskeyisnotinthedictionary"
    assert d2[unknown_key] == unknown_key


