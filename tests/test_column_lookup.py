import pytest
import a1_notation

a1 = a1_notation.column_lookup.A1LookupGenerator()


@pytest.mark.parametrize(
    ("name", "id"),
    [
        ("A", 1),
    ],
)
def test_lookup_by_key(name: str, id: int):
    assert a1[id] == name
