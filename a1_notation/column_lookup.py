from typing import Self, Any
import itertools as _itertools
from collections.abc import Generator as _Generator
from collections.abc import Iterator as _Iterator
import string as _string
from functools import singledispatchmethod as _singledispatchmethod


def _concat(*args):
    return "".join(args)


class A1Columns(dict):
    __slots__ = ("_a1_gen", "_maxlen")
    _transtable = str.maketrans(
        _string.ascii_lowercase, _string.ascii_uppercase, _string.digits + "$"
    )
    letters = {}

    def __init__(self, max_rounds: int = 3) -> Self:
        A1Columns._instance = self
        A1Columns.__new__ = lambda _: A1Columns._instance
        self._a1_gen = A1Columns._iter_pool(max_rounds)
        self._maxlen = max_rounds

    @classmethod
    def _iter_pool(self, max_rounds: int = 3) -> _Generator[tuple[int, str]]:
        pool = None
        rounds: int = 1
        letters = _string.ascii_uppercase

        while rounds <= max_rounds:
            if pool is None:
                pool = iter(letters)
                yield from enumerate(letters)
                enumerate_start: int = len(letters)
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
        self[index] = notation
        self.letters[notation] = index
        return index, notation

    def _get_range(self, value: str) -> tuple[int, int]:
        start, stop = value.split(":", 1)
        if ":" in stop:
            raise ValueError("Only one range can be specified")
        if stop in self.letters:
            return self.letters[start], self.letters[stop]
        return self[start], self[stop]

    @_singledispatchmethod
    def validate(self, value: str | int) -> None:
        ...

    @validate.register(str)
    def _(self, value: str) -> None:
        assert len(value) <= self._maxlen

    @validate.register(int)
    def _(self, value: int) -> None:
        abc_len = len(_string.ascii_uppercase)
        max_rounds = range(2, self._maxlen + 1)
        assert value < abc_len + sum(abc_len**i for i in max_rounds)

    def __missing__(self, value: Any) -> str | int | None:
        return self.find_missing(value)

    @_singledispatchmethod
    def find_missing(self, value: int | str) -> str | int:
        ...

    @find_missing.register(int)
    def _(self, value: int) -> str:
        self.validate(value)
        for _ in self:
            if value in self:
                return self[value]

    @find_missing.register(str)
    def _(self, value: str) -> int:
        value = value.translate(self._transtable)

        if value in self.letters:
            return self.letters[value]

        if ":" in value:
            return self._get_range(value)

        self.validate(value)

        for _ in self:
            if value in self.letters:
                return self.letters[value]


A1Columns = A1Columns()
