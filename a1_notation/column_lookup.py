import functools as _functools
import itertools as _itertools
import string as _string
from collections.abc import Generator as _Generator, Iterator as _Iterator
from typing import Any, Self
import dataclasses as _dataclasses


def _concat(*args):
    return "".join(args)


@_functools.cache
class A1LookupGenerator:
    """Generates letter to number and number to letter lookups sequentially as-needed.
    i.e. if you don't need the number for column XFD (or 16384), the generator will
    never be iterated to that point.

    """

    @_dataclasses.dataclass
    class OutOfBoundsError(LookupError):
        min: int = None
        max: int = None

    __slots__ = ("_startidx", "_maxint", "_a1_gen", "_maxlen", "_mapping", "_sequence")
    _transtable = str.maketrans(
        _string.ascii_lowercase, _string.ascii_uppercase, _string.digits + "$"
    )

    def __init__(self, start: int = 1, max_rounds: int = 3) -> Self:
        self._mapping = {}
        self._sequence = []
        self._a1_gen = self._iter_pool(start, max_rounds)
        self._maxlen = max_rounds
        self._startidx = start
        self._maxint = self._calculate_maxint()

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
                yield (
                    skipped,
                    self.OutOfBoundsError(min=self._startidx),
                )
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

    def __iter__(self) -> _Iterator[Self]:
        return self

    def __next__(self) -> tuple[int, str]:
        index, notation = next(self._a1_gen)
        self._sequence.append(notation)
        if index >= self._startidx:
            self._mapping[notation] = index
        return index, notation

    def _get_range(self, value: str) -> tuple[int, int]:
        start, stop = value.split(":", 1)
        if ":" in stop:
            raise ValueError("Only one range can be specified")
        if stop in self._mapping:
            return self._mapping[start], self._mapping[stop]
        return self[start], self[stop]

    @_functools.singledispatchmethod
    def __getitem__(self, idx_or_key: int | str) -> str | int:
        pass

    @__getitem__.register(int)
    def __getidx(self, idx: int) -> str:
        try:
            return self._sequence[idx]
        except IndexError:
            return self.find_missing(idx)

    @__getitem__.register(slice)
    def __getidx(self, idx: slice) -> str:
        try:
            self._sequence[idx.stop - 1]
        except IndexError:
            self.find_missing(idx.stop - 1)
        return self._sequence[idx]

    @__getitem__.register(str)
    def __getkey(self, key: str) -> int:
        if key in self._mapping:
            return self._mapping[key]
        return self.find_missing(key)

    @_functools.singledispatchmethod
    def validate(self, value: str | int) -> None:
        ...

    @validate.register(str)
    def _(self, value: str) -> None:
        try:
            assert len(value) <= self._maxlen
        except AssertionError as e:
            raise self.OutOfBoundsError(dict(max_strlen=self._maxlen)) from e

    @validate.register(int)
    def _(self, value: int) -> None:
        try:
            assert self._startidx <= value <= self._maxint
        except AssertionError as e:
            raise self.OutOfBoundsError(
                dict(min=self._startidx, max=self._maxint)
            ) from e

    def __missing__(self, value: Any) -> str | int | None:
        return self.find_missing(value)

    @_functools.singledispatchmethod
    def find_missing(self, value: int | str) -> str | int:
        ...

    @find_missing.register(int)
    def _(self, idx: int) -> str:
        self.validate(idx)
        for _ in self:
            try:
                return self._sequence[idx]
            except IndexError:
                continue

    @find_missing.register(str)
    def _(self, key: str) -> int:
        key = key.translate(self._transtable)

        if key in self._mapping:
            return self._mapping[key]

        if ":" in key:
            return self._get_range(key)

        self.validate(key)

        for _ in self:
            if key in self._mapping:
                return self._mapping[key]


if __name__ == "__main__":
    x = A1LookupGenerator()
    print(x(39))
