import sys
import typing as _t


class OutOfBoundsLookupError(LookupError):
    def __new__(cls, *args, **kwargs) -> _t.Self:
        return super().__new__(cls)

    def __init__(self, **kwargs) -> _t.Self:
        self.info = kwargs
        self.info_repr = ", ".join(f"{k}={v}" for k, v in self.info.items())

    def __repr__(self) -> str:
        return f"{self.__module__}.{self.__class__.__name__}({self.info_repr})"

    def __str__(self) -> str:
        return self.info_repr


def add_exception_detail(exception: Exception, message: _t.Any) -> Exception:
    # https://stackoverflow.com/a/75549200 thx
    if sys.version_info < (3, 11):
        exception.args = (
            f"{exception.args[0]}\n{message}" if exception.args else message,
        ) + exception.args[1:]
        return exception
    exception.add_note(message)
    return exception
