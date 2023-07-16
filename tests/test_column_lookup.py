import pytest
import a1_notation

a1 = a1_notation.A1Columns

print(a1[1], a1["A"])


@pytest.mark.parametrize(
    ("name", "id"),
    [
        ("A", 1),
    ],
)
def test_lookup_by_key(name: str, id: int):
    print(a1[id], name)
    assert a1[id] == name
