"""
Declarative modules for interacting with VirtualBox and a running VirtualBox VM.
"""

import logging
from pathlib import Path
from typing import Any, ClassVar

from akflib.core.hypervisor.vbox import VBoxExportFormatEnum, VBoxHypervisor
from akflib.declarative.core import AKFModule, AKFModuleArgs, NullConfig
from akflib.declarative.util import auto_format

# from caselib.uco.core import Bundle

logger = logging.getLogger(__name__)


class VBoxCreateModuleArgs(AKFModuleArgs):
    machine_name: str


class VBoxCreateModule(AKFModule[VBoxCreateModuleArgs, NullConfig]):
    """
    Instantiate a new VBoxHypervisor object and add it to the state dictionary.
    """

    aliases = ["vbox_start"]
    arg_model = VBoxCreateModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {"akflib.core.hypervisor.vbox.VBoxHypervisor"}

    @classmethod
    def generate_code(
        cls,
        args: VBoxCreateModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        if cls.get_hypervisor_var(state):
            logger.warning(
                "A previous hypervisor has already been instantiated, it will be lost from state!"
            )

        state["akflib.hypervisor_var"] = "vbox_obj"

        # Check if an AKFBundle is available
        if akf_bundle_var := cls.get_akf_bundle_var(state):
            return auto_format(
                f'vbox_obj = VBoxHypervisor("{args.machine_name}", {akf_bundle_var})',
                state,
            )

        return auto_format(
            f'vbox_obj = VBoxHypervisor("{args.machine_name}")',
            state,
        )

    @classmethod
    def execute(
        cls,
        args: VBoxCreateModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        if cls.get_hypervisor(state):
            logger.warning(
                "A hypervisor object has already been instantiated, it will be lost from state!"
            )

        if akf_bundle := cls.get_akf_bundle(state):
            vbox_obj = VBoxHypervisor(args.machine_name, akf_bundle)
        else:
            vbox_obj = VBoxHypervisor(args.machine_name)

        state["akflib.hypervisor"] = vbox_obj


class VBoxStartMachineModuleArgs(AKFModuleArgs):
    wait_for_guest_additions: bool = True


class VBoxStartMachineModule(AKFModule[VBoxStartMachineModuleArgs, NullConfig]):
    """
    Start the virtual machine associated with the VBoxHypervisor object.
    """

    aliases = ["vbox_start_machine"]
    arg_model = VBoxStartMachineModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {"akflib.core.hypervisor.vbox.VBoxHypervisor"}

    @classmethod
    def generate_code(
        cls,
        args: VBoxStartMachineModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        hypervisor_var = cls.get_hypervisor_var(state)
        if not hypervisor_var:
            raise RuntimeError(
                "Hypervisor object not previously instantiated, can't start machine"
            )

        return auto_format(
            f"{hypervisor_var}.start_vm(wait_for_guest_additions={args.wait_for_guest_additions})",
            state,
        )

    @classmethod
    def execute(
        cls,
        args: VBoxStartMachineModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        hypervisor = cls.get_hypervisor(state)
        if not hypervisor:
            raise RuntimeError(
                "Hypervisor object not previously instantiated, can't start machine"
            )

        if not isinstance(hypervisor, VBoxHypervisor):
            raise RuntimeError("Hypervisor object is not a VBoxHypervisor object")

        hypervisor.start_vm(wait_for_guest_additions=args.wait_for_guest_additions)


class VBoxStopMachineModuleArgs(AKFModuleArgs):
    force: bool = False


class VBoxStopMachineModule(AKFModule[VBoxStopMachineModuleArgs, NullConfig]):
    """
    Stop the virtual machine associated with the VBoxHypervisor object.
    """

    aliases = ["vbox_stop_machine"]
    arg_model = VBoxStopMachineModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {"akflib.core.hypervisor.vbox.VBoxHypervisor"}

    @classmethod
    def generate_code(
        cls,
        args: VBoxStopMachineModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        hypervisor_var = cls.get_hypervisor_var(state)
        if not hypervisor_var:
            raise RuntimeError(
                "Hypervisor object not previously instantiated, can't stop machine"
            )

        return auto_format(
            f"{hypervisor_var}.stop_vm(force={args.force})",
            state,
        )

    @classmethod
    def execute(
        cls,
        args: VBoxStopMachineModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        hypervisor = cls.get_hypervisor(state)
        if not hypervisor:
            raise RuntimeError(
                "Hypervisor object not previously instantiated, can't stop machine"
            )

        if not isinstance(hypervisor, VBoxHypervisor):
            raise RuntimeError("Hypervisor object is not a VBoxHypervisor object")

        hypervisor.stop_vm(force=args.force)


class VBoxCreateDiskImageModuleArgs(AKFModuleArgs):
    output_path: Path
    image_format: VBoxExportFormatEnum

    # Note that we don't provide the ability to select a specific disk UUID.


class VBoxCreateDiskImageModule(AKFModule[VBoxCreateDiskImageModuleArgs, NullConfig]):
    """
    Create a disk image with the active virtual machine.
    """

    aliases = ["vbox_create_disk_image"]
    arg_model = VBoxCreateDiskImageModuleArgs
    config_model = NullConfig

    dependencies: ClassVar[set[str]] = {
        "akflib.core.hypervisor.vbox.VBoxHypervisor",
        "akflib.core.hypervisor.vbox.VBoxExportFormatEnum",
        "pathlib.Path",
    }

    @classmethod
    def generate_code(
        cls,
        args: VBoxCreateDiskImageModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> str:
        hypervisor_var = cls.get_hypervisor_var(state)
        if not hypervisor_var:
            raise RuntimeError(
                "Hypervisor object not previously instantiated, can't create disk image"
            )

        return auto_format(
            f"{hypervisor_var}.create_disk_image(\n"
            f'    Path("{args.output_path.as_posix()}"),\n'
            f"    VBoxExportFormatEnum.{args.image_format.name}\n"
            f")",
            state,
        )

    @classmethod
    def execute(
        cls,
        args: VBoxCreateDiskImageModuleArgs,
        config: NullConfig,
        state: dict[str, Any],
    ) -> None:
        hypervisor = cls.get_hypervisor(state)
        if not hypervisor:
            raise RuntimeError(
                "Hypervisor object not previously instantiated, can't create disk image"
            )

        if not isinstance(hypervisor, VBoxHypervisor):
            raise RuntimeError("Hypervisor object is not a VBoxHypervisor object")

        hypervisor.create_disk_image(args.output_path, args.image_format)
