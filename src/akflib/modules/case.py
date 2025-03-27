"""
CASE-related declarative modules.

This covers the following functionality:
- Adding and managing CASE bundles in the declarative execution context
- Rendering a finished CASE bundle through a specified set of renderers
"""

import logging
from pathlib import Path
from typing import Any, ClassVar

from akflib.declarative.core import AKFModule, AKFModuleArgs, NullArgs, NullConfig
from akflib.declarative.util import auto_format
from akflib.rendering.objs import AKFBundle

# from caselib.uco.core import Bundle

logger = logging.getLogger(__name__)


class AKFBundleModule(AKFModule[NullArgs, NullConfig]):
    """
    Create a new AKFBundle object and add it to the state dictionary.
    """

    aliases = ["akf_bundle"]
    arg_model = NullArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {"akflib.rendering.objs.AKFBundle"}

    @classmethod
    def generate_code(
        cls,
        args: NullArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        if "akflib.akf_bundle_var" in state:
            logger.warning(
                "A previous AKFBundle has already been instantiated, it will be lost from state!"
            )

        state["akflib.akf_bundle_var"] = "akf_bundle"

        return auto_format(
            "akf_bundle = AKFBundle()",
            state,
        )

    @classmethod
    def execute(
        cls,
        args: NullArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        if "akflib.akf_bundle" in state:
            logger.warning(
                "A previous AKFBundle has already been instantiated, it will be lost from state!"
            )

        state["akflib.akf_bundle"] = AKFBundle()


class WriteAKFBundleModuleArgs(AKFModuleArgs):
    output_path: Path = Path("bundle.jsonld")
    indent: int = 2


class WriteAKFBundleModule(AKFModule[WriteAKFBundleModuleArgs, NullConfig]):
    """
    Write an AKF bundle to a file (in the JSON-LD format).
    """

    aliases = ["write_akf_bundle"]
    arg_model = WriteAKFBundleModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {"pathlib.Path"}

    @classmethod
    def generate_code(
        cls,
        args: WriteAKFBundleModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        akf_bundle_var = cls.get_akf_bundle_var(state)
        if akf_bundle_var is None:
            logger.warning("No AKFBundle object exists, skipping")
            return ""

        return auto_format(
            f"{akf_bundle_var}.write_to_jsonld(\n"
            f'    Path("{args.output_path.as_posix()}"),\n'
            f"    indent={args.indent}\n"
            ")",
            state,
        )

    @classmethod
    def execute(
        cls,
        args: WriteAKFBundleModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        akf_bundle = cls.get_akf_bundle(state)
        if akf_bundle is None:
            logger.warning("No AKFBundle object exists, skipping")
            return

        logger.info(f"Writing AKFBundle to {args.output_path}")
        akf_bundle.write_to_jsonld(args.output_path, indent=args.indent)


# TODO: RenderAKFBundleModule
