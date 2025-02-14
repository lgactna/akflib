from typing import Any, Type


def get_subclasses_recursive(type: Type[Any]) -> list[Type[Any]]:
    """
    Get all visible subclasses of `type`, recursive.

    From https://stackoverflow.com/questions/3862310
    """
    subclasses = set(type.__subclasses__()).union(
        [s for c in type.__subclasses__() for s in get_subclasses_recursive(c)]
    )

    return list(subclasses)


def get_full_qualname(type: Type[Any]) -> str:
    """
    Get the fully qualified class name of a provided class.

    From https://stackoverflow.com/questions/2020014
    """
    return ".".join([type.__module__, type.__name__])
