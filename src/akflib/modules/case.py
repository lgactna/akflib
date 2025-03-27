"""
CASE-related declarative modules.

This covers the following functionality:
- Adding and managing CASE bundles in the declarative execution context
- Rendering a finished CASE bundle through a specified set of renderers
"""

import logging
from typing import Any, ClassVar

from akflib.declarative.core import AKFModule, NullArgs, NullConfig
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


# TODO: RenderAKFBundleModule
