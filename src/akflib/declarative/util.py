from textwrap import dedent
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


def align_text(text: str) -> str:
    """
    Dedent and strip the provided text.
    """
    return dedent(text).strip()


def indent_text(text: str, indentation: int, spaces: int = 4) -> str:
    """
    Indent text.

    :param text: The text to indent.
    :param indentation: The number of times to indent the text.
    :param spaces: The number of spaces to use for each indentation level.
    """
    return "\n".join(
        [f"{' ' * (spaces * indentation)}{line}" for line in text.split("\n")]
    )


def auto_format(text: str, state: dict[str, Any]) -> str:
    """
    Automatically format the provided text based on the global state machine.

    The `indentation` key is used to determine where to indent the text.
    """
    return indent_text(align_text(text), state.get("indentation", 0)) + "\n"
