"""
Declarative modules for interacting with VirtualBox and a running VirtualBox VM.
"""

import logging
from typing import Any, ClassVar

from akflib.core.hypervisor.vbox import VBoxHypervisor
from akflib.declarative.core import AKFModule, AKFModuleArgs, NullConfig
from akflib.declarative.util import auto_format
from akflib.rendering.objs import AKFBundle

# from caselib.uco.core import Bundle

logger = logging.getLogger(__name__)


class VBoxStartModuleArgs(AKFModuleArgs):
    machine_name: str


class VBoxStartModule(AKFModule[VBoxStartModuleArgs, NullConfig]):
    """
    Instantiate a new VBoxHypervisor object and add it to the state dictionary.
    """

    aliases = ["vbox_start"]
    arg_model = VBoxStartModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {"akflib.core.hypervisor.vbox.VBoxHypervisor"}

    @classmethod
    def generate_code(
        cls,
        args: VBoxStartModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        if "akflib.hypervisor" in state:
            logger.warning(
                "A previous hypervisor has already been instantiated, it will be lost from state!"
            )

        state["akflib.hypervisor_var"] = "vbox_obj"

        # Check if an AKFBundle is available
        if "akflib.akf_bundle_var" in state:
            bundle_var = state["akflib.akf_bundle_var"]
            return auto_format(
                f"vbox_obj = VBoxHypervisor({args.machine_name}, {bundle_var})",
                state,
            )

        return auto_format(
            f'vbox_obj = VBoxHypervisor("{args.machine_name}")',
            state,
        )

    @classmethod
    def execute(
        cls,
        args: VBoxStartModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        if "akflib.hypervisor" in state:
            logger.warning(
                "A hypervisor object has already been instantiated, it will be lost from state!"
            )

        if "akflib.akf_bundle" in state:
            assert isinstance(state["akflib.akf_bundle"], AKFBundle)
            vbox_obj = VBoxHypervisor(args.machine_name, state["akflib.akf_bundle"])
        else:
            vbox_obj = VBoxHypervisor(args.machine_name)

        state["akflib.hypervisor"] = vbox_obj
