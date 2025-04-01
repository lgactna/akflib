import importlib
import inspect
import logging
import pkgutil
from textwrap import dedent
from typing import Any, List, Type

from akflib.declarative.core import AKFModule

logger = logging.getLogger(__name__)


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
    return indent_text(align_text(text), state.get("indentation_level", 0)) + "\n"


def import_all_modules(base_package: str) -> List[Type[AKFModule[Any, Any]]]:
    """
    Recursively import all subclasses of AKFModule under a specified package path.

    Args:
        base_package: The base package path (e.g., 'akflib.modules')

    Returns:
        A list of all AKFModule subclasses found in the package and its subpackages
    """
    modules = []

    def _import_recursive(package_name: str) -> None:
        """Recursively import all submodules of a package."""
        try:
            # Import the package
            package = importlib.import_module(package_name)

            # Get the package path for file operations
            if hasattr(package, "__path__"):
                # It's a package with submodules
                for _, name, is_pkg in pkgutil.iter_modules(
                    package.__path__, package_name + "."
                ):
                    try:
                        # Import the submodule
                        submodule = importlib.import_module(name)

                        # If it's a package, recurse into it
                        if is_pkg:
                            _import_recursive(name)

                        # Find all AKFModule subclasses in this module
                        for _, obj in inspect.getmembers(submodule, inspect.isclass):
                            if (
                                issubclass(obj, AKFModule)
                                and obj.__module__ == name
                                and obj is not AKFModule
                            ):

                                # Check if the class is already in the list to avoid duplicates
                                if obj not in modules:
                                    # logger.debug(f"Found AKFModule subclass: {obj.__module__}.{obj.__name__}")
                                    modules.append(obj)

                    except (ImportError, AttributeError) as e:
                        logger.warning(f"Error importing {name}: {e}")
                        continue

        except ImportError as e:
            logger.warning(f"Error importing {package_name}: {e}")
            return

    # Start the recursive import
    _import_recursive(base_package)

    return modules


def get_all_module_classes(
    base_path: str = "akflib.modules",
) -> List[Type[AKFModule[Any, Any]]]:
    """
    Convenience function to import all AKFModule subclasses from akflib.modules.

    Returns:
        A list of all AKFModule subclasses found in akflib.modules and its subpackages
    """
    return import_all_modules(base_path)


if __name__ == "__main__":
    # Import all modules from akflib.modules
    all_modules = get_all_module_classes()

    # Print information about found modules
    print(f"Found {len(all_modules)} AKFModule subclasses:")
    for module_class in all_modules:
        alias_str = (
            ", ".join(module_class.aliases)
            if hasattr(module_class, "aliases")
            else "No aliases"
        )
        print(f"  - {module_class.__module__}.{module_class.__name__} ({alias_str})")
