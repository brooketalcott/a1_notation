import functools as _functools
import inspect as _inspect
import itertools as _itertools
import re as _re
import string as _string
import typing as _t
from collections.abc import Generator as _Generator, Iterator as _Iterator

from a1_notation import exceptions as _exc


def _concat(*args):
    return "".join(args)


def _cache(f):
    """not sure why vscode is not showing my docstring so.."""

    @_functools.wraps(f)
    @_functools.cache
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


def _with_defaults(f):
    @_functools.wraps(f)
    def wrapper(*args, **kwargs):
        sig = _inspect.signature(f.__wrapped__).bind(*args, **kwargs)
        sig.apply_defaults()
        return f(*sig.args, **sig.kwargs)

    return wrapper


def _cache_with_defaults(f):
    @_with_defaults
    @_functools.wraps(f)
    @_cache
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


EXCEL_MAX_COLS: int = 16384


@_cache_with_defaults
class A1LookupGenerator:
    """
    ---
    Generates letter to number and number to letter lookups sequentially as-needed.

    i.e. if you don't need the number for column XFD (or 16384), the generator will
    never be iterated to that point.

    args:
        start (int): default=1 for typical Excel-like column-letter-numbers
        max_rounds (int): default=3 max rounds of letter permutations
        limit (None | int): default=16384 (excel max column range),
        if None, will calculate the limit based on the max_rounds argument
    """

    __slots__ = ("_mapping", "_startidx", "_maxint", "_maxlen", "_a1_gen")
    _valid_transtable = str.maketrans(
        _string.ascii_lowercase, _string.ascii_uppercase, _string.digits + "$"
    )
    _valid_regex = _re.compile("[a-zA-Z]")

    def __init__(
        self, start: int = 1, max_rounds: int = 3, limit: None | int = EXCEL_MAX_COLS
    ) -> _t.Self:
        self._mapping = {}
        self._a1_gen = self._iter_pool(start, max_rounds)
        self._maxlen = max_rounds
        self._startidx = start
        self._maxint = self._calculate_maxint() if limit is None else limit

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"start={self._startidx}, max_rounds={self._maxlen})"
        )

    @property
    def _range(self):
        return range(self._startidx, self._maxint)

    def _calculate_maxint(self) -> int:
        abc_len = len(_string.ascii_uppercase)
        max_rounds = range(2, self._maxlen + 1)
        return abc_len + sum(abc_len**i for i in max_rounds) + self._startidx

    def __call__(self, idx_or_key: int | str) -> str | int:
        return self[idx_or_key]

    def _iter_pool(self, start: int, max_rounds: int) -> _Generator[tuple[int, str]]:
        pool = None
        rounds: int = 1
        letters = _string.ascii_uppercase
        if start > 0:
            for skipped in range(start):
                yield (skipped, None)
        while rounds <= max_rounds:
            if pool is None:
                pool = iter(letters)
                yield from enumerate(letters, start)
                enumerate_start: int = len(letters) + start
            else:
                pool, new_round = _itertools.tee(
                    _itertools.starmap(_concat, _itertools.product(pool, letters)), 2
                )
                yield from enumerate(new_round, enumerate_start)
                enumerate_start += len(letters) ** rounds
            rounds += 1

    def __iter__(self) -> _Iterator[_t.Self]:
        return self

    def __next__(self) -> tuple[int, str]:
        index, notation = next(self._a1_gen)
        if index >= self._startidx:
            self._mapping.update({index: notation, notation: index})
            return index, notation
        else:
            return next(self)

    def _get_str_slice(self, value: str) -> _t.Generator[int, None, None]:
        """
        ---
        Returns column index generator object for inclusive letter range
        ex: 'A:C' -> (i for i in (1,2,3))
        """
        start, stop = value.split(":", 1)
        if ":" in stop:
            raise _exc.add_exception_detail(
                ValueError(),
                f"Only one string range can be specified but was called with '{value}'",
            )

        start_idx = self._mapping[start] if start in self._mapping else self[start]
        stop_idx = self._mapping[stop] if stop in self._mapping else self[stop]
        return range(start_idx, stop_idx + 1)

    def __getitem__(self, idx_or_key: int | str | slice) -> str | int:
        if not isinstance(idx_or_key, slice) and idx_or_key in self._mapping:
            return self._mapping[idx_or_key]
        return self.find_missing(idx_or_key)

    @_functools.singledispatchmethod
    def validate(self, value: str | int) -> None:
        ...

    @validate.register(str)
    def _(self, value: str) -> None:
        if len(value) > self._maxlen:
            raise _exc.add_exception_detail(
                _exc.OutOfBoundsLookupError(max_strlen=self._maxlen, src=repr(self)),
                message=(
                    f"Lookup not possible for value '{value}'. Create a new "
                    f"instance with max_rounds > {self._maxlen} or correct the"
                    " lookup value."
                ),
            )
        oob_chars = self._valid_regex.sub("", value)
        if oob_chars:
            raise _exc.add_exception_detail(
                ValueError(f"{oob_chars} not in {_string.ascii_letters}"),
                message=f"Invalid characters: {oob_chars}",
            )

    @validate.register(int)
    def _(self, value: int) -> None:
        if not self._startidx <= value <= self._maxint:
            raise _exc.add_exception_detail(
                _exc.OutOfBoundsLookupError(
                    min=self._startidx, max=self._maxint, src=repr(self)
                ),
                f"Lookup not possible for value '{value}'",
            )

    @_functools.singledispatchmethod
    def find_missing(self, value: int | str) -> str | int:
        ...

    @find_missing.register(int)
    def _(self, idx: int) -> str:
        if idx in self._mapping:
            return self._mapping[idx]

        self.validate(idx)

        for _ in self:
            if idx in self._mapping:
                return self._mapping[idx]
        else:
            self._fallback_exception(idx)

    @find_missing.register(str)
    def _(self, key: str) -> int:
        key = key.translate(self._valid_transtable)

        if key in self._mapping:
            return self._mapping[key]

        if ":" in key:
            return self._get_str_slice(key)

        self.validate(key)

        for _ in self:
            if key in self._mapping:
                return self._mapping[key]
        else:
            self._fallback_exception(key)

    @find_missing.register(slice)
    def _(self, slice_: slice) -> _t.Generator[str, None, None]:
        indexes = self._range[slice_]
        for idx in indexes:
            if idx in self._mapping:
                yield self._mapping[idx]
            else:
                for _ in self:
                    if idx in self._mapping:
                        yield self._mapping[idx]
                        break
                else:
                    self._fallback_exception(idx)

    def _fallback_exception(self, idx_or_key):
        raise _exc.add_exception_detail(
            _exc.OutOfBoundsLookupError(src=repr(self)),
            message=f"{idx_or_key} is out of valid range and {self.__class__.__name__} "
            "is exhausted",
        )


if __name__ == "__main__":
    ...
