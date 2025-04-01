"""
Entrypoint for the declarative translator.

From akflib, the following state variables can be expected:

- akflib.hypervisor: An active HypervisorABC object.
- akflib.hypervisor_var: The name of the currently active hypervisor object.
- akflib.akf_bundle: An AKFBundle object.
"""

import logging
import random
import sys
from pathlib import Path
from typing import Any, Iterable, Type

import click
from pydantic import ValidationError
from pydantic_yaml import parse_yaml_file_as

from akflib.declarative.core import AKFModule, AKFScenario
from akflib.declarative.util import (
    align_text,
    get_all_module_classes,
    get_full_qualname,
)
from akflib.utility.imports import get_objects_by_name

# Set up logging
logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    level=logging.INFO,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()


def generate_import_statements(import_paths: Iterable[str]) -> str:
    # Note that this doesn't group import statements together or do anything
    # fancy like that
    import_statements = []
    for path in import_paths:
        parts = path.split(".")
        if len(parts) == 1:
            import_statements.append(f"import {path}")
        else:
            module = ".".join(parts[:-1])
            name = parts[-1]
            import_statements.append(f"from {module} import {name}")

    # Remove duplicate import statements
    import_statements = list(set(import_statements))

    # Sort import statements alphabetically
    import_statements.sort()

    return "\n".join(import_statements)


def build_module_cache(libraries: list[str]) -> dict[str, Type[AKFModule[Any, Any]]]:
    """
    Build a cache of all AKFModules in the specified libraries.

    Where applicable, this also generates mappings for aliases.
    """

    def add_to_cache(
        name: str,
        obj: Type[AKFModule[Any, Any]],
        cache: dict[str, Type[AKFModule[Any, Any]]],
    ) -> None:
        if name in cache:
            logger.warning(
                f'Duplicate module "{name}" found for {obj} and {cache[name]}.'
                f" Only {cache[name]} will be available by name."
            )
            return

        cache[name] = obj

    # Start by getting all module classes from each library.
    module_classes = []
    for library in libraries:
        # Get all module classes in the library
        module_classes += get_all_module_classes(library)

    # Then, build a cache of their fully qualified names.
    module_cache: dict[str, Type[AKFModule[Any, Any]]] = {}
    for module_class in module_classes:
        # Get the fully qualified name of the module class
        module_name = get_full_qualname(module_class)

        # Add the module class to the cache
        add_to_cache(module_name, module_class, module_cache)

        # Also add aliases if they exist
        if hasattr(module_class, "aliases"):
            for alias in module_class.aliases:
                # Add the "base", unqualified alias
                add_to_cache(alias, module_class, module_cache)

                # Then, take the fully qualified name and substitute the final
                # component with the alias
                alias_parts = module_name.split(".")
                alias_parts[-1] = alias
                alias_name = ".".join(alias_parts)

                add_to_cache(alias_name, module_class, module_cache)

    return module_cache


def get_akf_modules(
    module_paths: Iterable[str],
    cache: dict[str, Type[AKFModule[Any, Any]]] | None = None,
) -> dict[str, Type[AKFModule[Any, Any]]]:
    """
    Attempt to import a set of AKFModules identified by their fully-qualified
    module paths.

    TODO: This doesn't support the `aliases` attribute of modules. It requires
    fully-qualified module paths. What *should* happen is that we accept the
    `library` key in the scenario file, preload a bunch of modules and their
    aliases, and check if a module that can't be found using a fully-qualified name
    exists in the preloaded modules.
    """
    # If a cache exists, check if a module is already in the cache. If it is,
    # exclude it from the explicit import process.
    if cache is None:
        cache = {}

    needs_import = set(module_paths) - set(cache.keys())

    if needs_import:
        logger.info(
            f"The following modules were not found in the cache: {needs_import}"
        )

        result = get_objects_by_name(needs_import)

        for obj in result.values():
            if not issubclass(obj, AKFModule):
                raise TypeError(f"{obj} is not a subclass of AKFModule")

        return result

    logger.info("All declared modules were found in the cache")
    return cache


def execute_module(
    module: Type[AKFModule[Any, Any]],
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


def generate_code_from_module(
    module: Type[AKFModule[Any, Any]],
    args: dict[str, Any],
    config: dict[str, Any],
    state: dict[str, Any],
) -> str:
    """
    Generate code for a module with the given arguments and configuration.
    """
    # Build the module's arguments and configuration
    args_model = module.arg_model.model_validate(args)
    config_model = module.config_model.model_validate(config)

    # Generate code
    return module.generate_code(args_model, config_model, state)


def execution_entrypoint(
    scenario: AKFScenario, modules: dict[str, Type[AKFModule[Any, Any]]]
) -> None:
    """
    Entrypoint for the declarative translator.
    """
    # Global state variables
    state: dict[str, Any] = {}

    # Set global random seed
    random.seed(scenario.seed)

    # Execute each action in sequence
    for action in scenario.actions:
        module = modules[action.module]
        logger.info(f"Executing action: {action.name}")
        execute_module(module, action.args, scenario.config | action.config, state)


def translation_entrypoint(
    scenario: AKFScenario, modules: dict[str, Type[AKFModule[Any, Any]]]
) -> str:
    # State variables
    state = {"indentation_level": 0}

    # fmt: off
    result = align_text('''
        """
        This file was automatically generated by akf-translate.
        
        Verify that the generated code is correct before running it.
        """
    ''') + "\n\n"
    # fmt: on

    # Generate the import statements by collecting the dependencies declared
    # by each resolved module.
    #
    # `logging` and `sys` are always required to set up the log handler.
    dependencies = {"logging", "random", "sys"}
    for action in scenario.actions:
        module = modules[action.module]
        dependencies.update(module.dependencies)

    result += generate_import_statements(dependencies) + "\n\n"

    # fmt: off
    result += align_text('''
        # Set up logging
        logging.basicConfig(
            handlers=[logging.StreamHandler(sys.stdout)],
            level=logging.INFO,
            format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logger = logging.getLogger()
    ''') + "\n\n"
    # fmt: on

    # Set raandom seed
    result += f"random.seed({scenario.seed})\n\n"

    # Generate the code for each action
    for action in scenario.actions:
        module = modules[action.module]
        result += f"# {action.name}\n"
        result += f"logger.info(r'Executing action: {action.name}')\n"
        result += generate_code_from_module(
            module, action.args, scenario.config | action.config, state
        )

        # One full newline between each action, at minimum
        result += "\n"
    return result + "\n"


@click.command(help="Translate or execute declarative AKF scenario files.")
@click.argument(
    "input-file",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
)
@click.option(
    "--execute",
    is_flag=True,
    help="Execute the scenario on a virtual machine.",
)
@click.option(
    "--translate",
    is_flag=True,
    help="Translate the scenario to Python code.",
)
@click.option(
    "--output-file",
    type=click.Path(dir_okay=False, writable=True),
    help="Output file for generated code. Does nothing when --execute is set.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Set the logging level.",
)
def main(
    input_file: str,
    translate: bool,
    execute: bool,
    output_file: str,
    log_level: str,
) -> None:
    logger.setLevel(log_level)
    logger.info(f"Log level set to {log_level}")

    # Exactly one of translate or execute must be set
    if not (translate ^ execute):
        raise RuntimeError("Exactly one of --translate or --execute must be set.")

    # Load sample.yaml
    try:
        scenario = parse_yaml_file_as(AKFScenario, input_file)
    except ValidationError as e:
        raise RuntimeError("Invalid AKF scenario file!") from e

    logger.info("Collecting modules from declared libraries")
    cache = build_module_cache(scenario.libraries)

    logger.debug("Preloaded modules:")
    for key, value in cache.items():
        logger.debug(f"  {key}: {value}")

    # Collect a list of all individual actions declared, check if we
    # can import them and build a lookup list
    logger.info("Collecting explicitly declared modules")
    module_paths = {action.module for action in scenario.actions}
    explicit_modules = get_akf_modules(module_paths, cache)

    logger.debug("Newly imported modules:")
    for key, value in explicit_modules.items():
        logger.debug(f"  {key}: {value}")

    # Combine the cache and the explicitly imported modules
    modules = cache | explicit_modules

    if execute:
        execution_entrypoint(scenario, modules)
    elif translate:
        if output_file is None:
            logger.info("Translating scenario to stdout")
        else:
            logger.info(f"Translating scenario to {output_file=}")

        result = translation_entrypoint(scenario, modules)

        # If no output file specified, write to stdout
        if output_file is not None:
            Path(output_file).write_text(result)
        else:
            print("\n" + result)
    else:
        raise AssertionError
