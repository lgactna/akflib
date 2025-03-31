"""
Utilities for locating and importing modules and packages.
"""

from typing import Any, Iterable
import importlib


def get_objects_by_name(
    object_paths: Iterable[str],
) -> dict[str, Any]:
    """
    Attempt to import a set of AKFModules identified by their fully-qualified
    module paths.

    TODO: This doesn't support the `aliases` attribute of modules. It requires
    fully-qualified module paths. What *should* happen is that we accept the
    `library` key in the scenario file, preload a bunch of modules and their
    aliases, and check if a module that can't be found using a fully-qualified name
    exists in the preloaded modules.
    """
    imported_objects = {}
    for path in object_paths:
        parts = path.split(".")
        module_path = ".".join(parts[:-1])
        object_name = parts[-1]

        try:
            module = importlib.import_module(module_path)
        except ImportError:
            raise ImportError(f"Could not import module {module_path}")

        try:
            akf_module = getattr(module, object_name)
        except AttributeError:
            raise ImportError(
                f"Could not import object {object_name} from module {module_path}"
            )

        imported_objects[path] = akf_module
    return imported_objects