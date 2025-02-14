"""
Entrypoint for the declarative translator.
"""

import importlib
from typing import Any, Iterable

from pydantic_yaml import parse_yaml_file_as

from akflib.translation.core import AKFModule, AKFScenario


def generate_import_statements(import_paths: Iterable[str]) -> str:
    import_statements = []
    for path in import_paths:
        parts = path.split(".")
        if len(parts) == 1:
            import_statements.append(f"import {path}")
        else:
            module = ".".join(parts[:-1])
            name = parts[-1]
            import_statements.append(f"from {module} import {name}")
    return "\n".join(import_statements)


def get_akf_modules(
    module_paths: Iterable[str],
) -> dict[str, AKFModule[Any, Any]]:
    """
    Attempt to import a set of AKFModules identified by their fully-qualified
    module paths.
    """
    imported_objects = {}
    for path in module_paths:
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

        assert issubclass(
            akf_module, AKFModule
        ), f"Module {akf_module} is not a subclass of AKFModule"

        imported_objects[path] = akf_module
    return imported_objects


def execute_module(
    module: AKFModule[Any, Any],
    args: dict[str, Any],
    config: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """
    Execute a module with the given arguments and configuration.
    """
    # Build the module's arguments and configuration
    args_model = module.arg_model.model_validate(args)
    config_model = module.config_model.model_validate(config)

    # Execute the module
    module.execute(args_model, config_model, state)


if __name__ == "__main__":
    # Load sample.yaml
    scenario = parse_yaml_file_as(AKFScenario, "scenarios/sample.yaml")

    # TODO: do something with the libraries key - currently unused

    # Collect a list of all individual actions declared, check if we
    # can import them and build a lookup list
    module_paths = {action.module for action in scenario.actions}
    modules = get_akf_modules(module_paths)

    # When executing modules...
    for action in scenario.actions:
        module = modules[action.module]
        execute_module(module, action.args, scenario.config | action.config, {})
