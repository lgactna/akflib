"""
VirtualBox hypervisor bindings for AKF.
"""

from enum import Enum
from typing import Any, Optional

# import virtualbox as vbox
import virtualbox.library as vboxlib

from akf.action.hypervisor.base import HypervisorABC


# Create string enumeration
class VBoxFrontendEnum(str, Enum):
    """
    Available frontends for VirtualBox.

    This exists because there is no actual enumeration object for the frontends
    in the `virtualbox` library.
    """

    GUI = "gui"
    HEADLESS = "headless"
    SDL = "sdl"


class VBoxHypervisor(HypervisorABC):
    """
    Concrete implementation of an AKF hypervisor using the VirtualBox SDK.

    Instances of this class maintain a single "overall" session that is used when
    starting or stopping the VM. Where possible, temporary sessions using shared
    locks are used when performing actions on the VM. The same is true of the
    Guest Additions session.

    It is expected that the VM has already had Guest Additions installed. Many
    of these methods depend on Guest Additions to function properly. If an action
    requiring Guest Additions is attempted without them, a RuntimeError is raised.
    """

    def __init__(self, name_or_id: str) -> None:
        """
        Bind this hypervisor instance to a VirtualBox machine by name or UUID.
        """
        raise NotImplementedError

    def start_vm(
        self,
        frontend: VBoxFrontendEnum,
        environment_changes: Optional[list[str]] = None,
    ) -> bool:
        """
        Start the virtual machine, creating a new session if necessary.

        :param frontend: The frontend to use when starting the VM.
        :param environment_changes: A list of environment changes to apply to
            the VM. See the `virtualbox` library for more information. If `None`,
            an empty list is used.
        :return: True if the machine was started, False otherwise.
        """
        raise NotImplementedError

    def stop_vm(self, force: bool = False) -> bool:
        """
        Stop the virtual machine.

        :param force: If True, the machine is powered off (equivalent to pulling
            the plug). If False, an ACPI shutdown is attempted.
        :return: True if the machine was stopped, False otherwise.
        """
        raise NotImplementedError

    def send_keyboard_event(self, *args, **kwargs):
        raise NotImplementedError

    def send_mouse_event(self, *args, **kwargs):
        raise NotImplementedError

    def execute_process(
        self,
        executable: str,
        arguments: Optional[list[str]] = None,
        cwd: Optional[str] = None,
        environment_changes: Optional[list[str]] = None,
        flags: Optional[list[vboxlib.ProcessCreateFlag]] = None,
    ) -> Any:
        """
        Execute a process through VirtualBox's ProcessCreateEx.

        TODO: should we abstract away flags to permit this function to be blocking
        and non-blocking? Or should we just always block? What is this function
        supposed to return??

        The SDK limits guest processes through ProcessCreate/ProcessCreateEx to
        255 process at a time. If the maximnum number of processes is reached,
        this rasises an exception. (VBOX_E_MAXIMUM_REACHED)

        See https://www.virtualbox.org/sdkref/interface_i_guest_session.html#a463ec0f6748ce0f4009225b70ee6e4f3
        for more information.

        :param executable: The full path to the executable to run.
        :param arguments: A list of arguments to pass to the executable.
        :param cwd: The working directory to use when executing the process. If
            not set, the session user's default directory is used. If a relative
            path is used, it is interpreted relative to the default directory.
        :param environment_changes: A list of environment changes to apply. This
            is a list of strings in the format "key=value" for setting variables,
            and "key" when unsetting these variables. If not set, an empty
            list is passed.
        :param flags: A list of process creation flags. If not set, the default
            behavior is to wait until stderr and stdout are returned, ignoring
            orphan processes. See the following link:
            https://www.virtualbox.org/sdkref/_virtual_box_8idl.html#a98b478b2b9d4a01d8e6f290565b23806
        :param timeout: The time, in milliseconds, to wait before timing out the
            process. If not set, a default of 30 seconds is used.
        :param affinity: The number of guest CPUs the process is allowed to run on.

        """
        raise NotImplementedError

    def attach_drive(self, *args, **kwargs):
        raise NotImplementedError

    def detach_drive(self, *args, **kwargs):
        raise NotImplementedError

    def set_bios_time(self, *args, **kwargs):
        raise NotImplementedError

    def create_disk_image(self, *args, **kwargs):
        raise NotImplementedError

    def create_memory_dump(self, *args, **kwargs):
        raise NotImplementedError

    def start_network_capture(self, *args, **kwargs):
        raise NotImplementedError

    def stop_network_capture(self, *args, **kwargs):
        raise NotImplementedError
