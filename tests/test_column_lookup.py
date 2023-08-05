from enum import Enum
import functools
import inspect
from operator import itemgetter

import pytest

import a1_notation
from a1_notation.column_lookup import A1LookupGenerator

A1_EXPECTED = (
    (1, "A"),
    (2, "B"),
    (10, "J"),
    (11, "K"),
    (25, "Y"),
    (26, "Z"),
    (27, "AA"),
    (28, "AB"),
    (701, "ZY"),
    (702, "ZZ"),
    (703, "AAA"),
    (704, "AAB"),
    (18277, "ZZY"),
    (18278, "ZZZ"),
)


def decrement_id(kv: tuple[int, str], new_start: int) -> tuple[int, str]:
    decrement = 1 - new_start
    key, value = kv
    return key - decrement, value


@pytest.mark.parametrize("a1_pair", A1_EXPECTED)
@pytest.mark.parametrize(("new_start", "expected_diff"), ((0, 1), (1, 0), (2, -1)))
def test_decrement_id(a1_pair, new_start, expected_diff):
    assert decrement_id(a1_pair, new_start)[0] == a1_pair[0] - expected_diff


class LookupTypes(Enum):
    A0 = 0, 3, None
    A1 = 1, 3, None
    A2 = 2, 3, None

    def __init__(self, start_value: int, max_rounds: int, limit: int | None) -> None:
        self._value_ = A1LookupGenerator(
            start=start_value, max_rounds=max_rounds, limit=limit
        )
        self._pairs = tuple(
            map(functools.partial(decrement_id, new_start=start_value), A1_EXPECTED)
        )
        self._start = start_value
        self._maxrounds = max_rounds
        self._limit = limit

    @property
    def starts_at(self) -> int:
        return self._start

    @property
    def max_rounds(self) -> int:
        return self._maxrounds

    @property
    def expected_pairs(self) -> tuple[tuple[int, str]]:
        return self._pairs

    @property
    def limit(self) -> None | int:
        return self._limit


def all_lookup_type_objects():
    for lookup_obj in LookupTypes:
        yield lookup_obj.value


def make_basic_lookup_params(lookup: LookupTypes) -> tuple[A1LookupGenerator, int, str]:
    for id, key in lookup.expected_pairs:
        yield lookup.value, id, key


@pytest.mark.parametrize(
    ("lookup", "expected"),
    (
        (LookupTypes.A0, (A1LookupGenerator(start=0, limit=None), 0, "A")),
        (LookupTypes.A1, (A1LookupGenerator(start=1, limit=None), 1, "A")),
        (LookupTypes.A2, (A1LookupGenerator(start=2, limit=None), 2, "A")),
    ),
)
def test_make_params(lookup, expected):
    assert next(make_basic_lookup_params(lookup=lookup)) == expected


def make_basic_lookup_test_params():
    for lookup in LookupTypes:
        for params in make_basic_lookup_params(lookup):
            yield params


@pytest.mark.parametrize(
    ("lookup_obj", "number", "alpha"), make_basic_lookup_test_params()
)
def test_lookup_by_id(lookup_obj, number, alpha):
    assert lookup_obj[number] == alpha


@pytest.mark.parametrize(
    ("lookup_obj", "number", "alpha"), make_basic_lookup_test_params()
)
def test_lookup_by_key(lookup_obj, number, alpha):
    assert lookup_obj[alpha] == number


def make_oob_test_params():
    for lookup_type in LookupTypes:
        first_pair, last_pair = (
            lookup_type.expected_pairs[0],
            lookup_type.expected_pairs[-1],
        )

        oob_low_int = first_pair[0] - 1
        oob_high_int = last_pair[0] + 1
        oob_long_str = last_pair[1] + "A"

        yield lookup_type.value, oob_low_int
        yield lookup_type.value, oob_high_int
        yield lookup_type.value, oob_long_str

        same_type_but_more_rounds = A1LookupGenerator(
            start=lookup_type.starts_at,
            max_rounds=lookup_type.max_rounds + 1,
            limit=lookup_type.limit,
        )
        yield pytest.param(
            same_type_but_more_rounds,
            oob_high_int,
            marks=(pytest.mark.xfail),
        )
        yield pytest.param(
            same_type_but_more_rounds,
            oob_long_str,
            marks=(pytest.mark.xfail),
        )


@pytest.mark.parametrize(("lookup_obj", "value"), make_oob_test_params())
def test_out_of_bounds(lookup_obj, value):
    with pytest.raises(a1_notation.exceptions.OutOfBoundsLookupError):
        lookup_obj[value]


def test_singleton_assumes_defaults():
    sig = inspect.signature(A1LookupGenerator).bind()
    sig.apply_defaults()
    assert A1LookupGenerator() is A1LookupGenerator(*sig.args, **sig.kwargs)


@pytest.mark.parametrize("lookup_obj", all_lookup_type_objects())
def test_slice_lookup(lookup_obj: A1LookupGenerator):
    abc_idxes = itemgetter("A", "B", "C")(lookup_obj)
    assert (
        tuple(lookup_obj[0:3])
        == ("A", "B", "C")
        == tuple(lookup_obj[idx] for idx in abc_idxes)
    )


@pytest.mark.parametrize("obj", all_lookup_type_objects())
def test_string_slice_lookup(obj: A1LookupGenerator):
    assert (
        tuple(obj["A:C"])
        == (obj["A"], obj["B"], obj["C"])
        == tuple(range(obj._startidx, obj._startidx + 3))
    )


if __name__ == "__main__":
    pytest.main([__file__])
