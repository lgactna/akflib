"""
Entrypoint for the declarative translator.

From akflib, the following state variables can be expected:

- akflib.hypervisor: An active HypervisorABC object.
- akflib.hypervisor_var: The name of the currently active hypervisor object.
- akflib.akf_bundle: An AKFBundle object.
"""

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Iterable

import click
from pydantic import ValidationError
from pydantic_yaml import parse_yaml_file_as

from akflib.declarative.core import AKFModule, AKFScenario
from akflib.declarative.util import align_text

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


def get_akf_modules(
    module_paths: Iterable[str],
) -> dict[str, AKFModule[Any, Any]]:
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


def generate_code_from_module(
    module: AKFModule[Any, Any],
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
    scenario: AKFScenario, modules: dict[str, AKFModule[Any, Any]]
) -> None:
    """
    Entrypoint for the declarative translator.
    """
    # Global state variables
    state: dict[str, Any] = {}

    # Execute each action in sequence
    for action in scenario.actions:
        module = modules[action.module]
        logger.info(f"Executing action: {action.name}")
        execute_module(module, action.args, scenario.config | action.config, state)


def translation_entrypoint(
    scenario: AKFScenario, modules: dict[str, AKFModule[Any, Any]]
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
    dependencies = {"logging", "sys"}
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

    # Generate the code for each action
    for action in scenario.actions:
        module = modules[action.module]
        result += f"# {action.name}\n"
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

    # TODO: do something with the libraries key - currently unused

    # Collect a list of all individual actions declared, check if we
    # can import them and build a lookup list
    logger.info("Collecting declared modules")
    module_paths = {action.module for action in scenario.actions}
    modules = get_akf_modules(module_paths)

    logger.info("Successfully imported declared modules")
    logger.debug("Module dictionary:")
    for key, value in modules.items():
        logger.debug(f"  {key}: {value}")

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
