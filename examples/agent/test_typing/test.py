"""
See these:
- https://stackoverflow.com/questions/70861001/annotate-dataclass-class-variable-with-type-value
- https://stackoverflow.com/questions/77552328/how-to-type-hint-a-variable-whose-type-is-any-subclass-of-a-generic-base-class
"""

from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModuleABC(Generic[T]):
    # Note that T should be a subclass of BaseModel. There doesn't appear to be
    # a great way to annotate a generic with a type value; you can't use
    # ClassVar[Type[T]].
    x: ClassVar[type[BaseModel]]

    @staticmethod
    def test(arg1: T) -> None:
        print(arg1)


class Subtype(BaseModel):
    val1: int = 1
    val2: int = 2


class B(ModuleABC[Subtype]):
    x = Subtype

    @staticmethod
    def test(arg1: Subtype) -> None:
        print(arg1)


class Wrapper(Generic[T]):
    @staticmethod
    def call_it(module: type[ModuleABC[T]], args: T) -> None:
        module.test(args)


def call_it(module: type[ModuleABC[T]], args: T) -> None:
    module.test(args)


if __name__ == "__main__":
    # Wrapper.call_it(B)
    args = Subtype()
    call_it(B, args)
