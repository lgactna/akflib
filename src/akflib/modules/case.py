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
from akflib.rendering.core import bundle_to_pdf, get_pandoc_path, get_renderer_classes
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


class RenderAKFBundleModuleArgs(AKFModuleArgs):
    """
    Arguments for the RenderAKFBundleModule.
    """

    renderers: list[str]

    output_folder: Path = Path("output")

    pandoc_path: Path | None = None

    group_renderers: bool = False


class RenderAKFBundleModule(AKFModule[RenderAKFBundleModuleArgs, NullConfig]):
    """
    Render an AKFBundle using a set of renderers.
    """

    aliases = ["render_akf_bundle"]
    arg_model = RenderAKFBundleModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {
        "akflib.rendering.core.bundle_to_pdf",
        "akflib.rendering.core.get_pandoc_path",
        "akflib.rendering.core.get_renderer_classes",
        "pathlib.Path",
    }

    @classmethod
    def generate_code(
        cls,
        args: RenderAKFBundleModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        akf_bundle_var = cls.get_akf_bundle_var(state)
        if akf_bundle_var is None:
            logger.warning("No AKFBundle object exists, skipping")
            return ""

        if not args.renderers:
            logger.warning("No renderers specified, skipping")
            return ""

        result = ""

        # Use get_renderer_classes to get the renderer classes from the provided
        # renderer paths. We *could* generate actual import statements, but this
        # is better from both a readability and runtime correctness perspective.
        #
        # The actual renderer classes are not validated here, which allows a
        # declarative script to be translated even if the renderer classes are not
        # available in the current environment.
        result += "renderer_classes = get_renderer_classes([\n"
        result += ",\n".join([f'    "{renderer}"' for renderer in args.renderers])
        result += "\n])\n"
        result += "\n"

        if args.pandoc_path:
            result += f"pandoc_path = Path({args.pandoc_path.as_posix()})\n"
        else:
            result += "pandoc_path = get_pandoc_path()\n"
            result += "if pandoc_path is None:\n"
            result += '    raise RuntimeError("Unable to find path to Pandoc executable (make sure it is on PATH)")\n'
        result += "\n"

        result += f'pandoc_output_folder = Path("{args.output_folder.as_posix()}")\n'
        result += "pandoc_output_folder.mkdir(parents=True, exist_ok=True)\n"
        result += "\n"

        result += "bundle_to_pdf(\n"
        result += f"    {akf_bundle_var},\n"
        result += "    renderer_classes,\n"
        result += "    pandoc_output_folder,\n"
        result += "    pandoc_path,\n"
        result += f"    group_renderers={args.group_renderers},\n"
        result += ")"

        return auto_format(
            result,
            state,
        )

    @classmethod
    def execute(
        cls,
        args: RenderAKFBundleModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        akf_bundle = cls.get_akf_bundle(state)
        if akf_bundle is None:
            logger.warning("No AKFBundle object exists, skipping")
            return

        logger.info(f"Rendering AKFBundle to {args.output_folder}")

        # Get renderer classes
        renderer_classes = get_renderer_classes(args.renderers)
        if not renderer_classes:
            logger.warning("No renderer classes found, skipping")
            return

        logger.info(f"Renderer classes: {renderer_classes}")

        # Get pandoc path
        if not args.pandoc_path:
            args.pandoc_path = get_pandoc_path()

        if not args.pandoc_path:
            logger.warning(
                "Unable to find path to Pandoc executable (make sure it is on PATH) - skipping"
            )
            return

        args.pandoc_path = args.pandoc_path.resolve()
        logger.info(f"Pandoc path: {args.pandoc_path}")

        args.output_folder.mkdir(parents=True, exist_ok=True)

        # Perform the actual rendering
        bundle_to_pdf(
            akf_bundle,
            renderer_classes,
            args.output_folder,
            args.pandoc_path,
            group_renderers=args.group_renderers,
        )
