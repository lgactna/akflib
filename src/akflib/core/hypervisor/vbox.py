"""
VirtualBox hypervisor bindings for AKF.
"""

import datetime
import logging
from enum import Enum
from typing import Any

import virtualbox
import virtualbox.library as vboxlib
from caselib.uco.core import Bundle

from akflib.core.hypervisor.base import HypervisorABC

logger = logging.getLogger(__name__)


class VBoxFrontendEnum(str, Enum):
    """
    Available frontends for VirtualBox.

    This exists because there is no actual enumeration object for the frontends
    in the `virtualbox` library.
    """

    GUI = "gui"
    HEADLESS = "headless"
    SDL = "sdl"


class VBoxMouseClickEnum(int, Enum):
    """
    VirtualBox's enumeration for mouse clicks.
    """

    RELEASE = 0x00
    LEFT_CLICK = 0x01
    RIGHT_CLICK = 0x02
    MIDDLE_CLICK = 0x04


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

    def __init__(self, name_or_id: str, case_bundle: Bundle | None = None) -> None:
        """
        Bind this hypervisor instance to a VirtualBox machine by name or UUID.

        Optionally, also bind this hypervisor instance to a CASE bundle.

        This *does not* lock the session.
        """
        # Assign CASE bundle
        self.case_bundle = case_bundle

        # Get handle to machine, create new session
        vbox = virtualbox.VirtualBox()
        self.session = virtualbox.Session()
        self.machine = vbox.find_machine(name_or_id)

    def _lock(self, lock_type: vboxlib.LockType = vboxlib.LockType.Shared) -> None:
        """
        Get a lock to the machine associated with this session.

        Do not call this if you have started the VM through this session. The
        session will already hold a write lock, and therefore a new session/lock
        is not necessary.

        By default, this obtains a shared lock.
        """
        self.machine.lock_machine(self.session, lock_type)

    def _unlock(self) -> None:
        """
        Release the lock to the machine associated with this session.
        """
        self.session.unlock_machine()

    def _is_running(self) -> bool:
        """
        Check if the VM is currently running.

        This is *not* equivalent to checking if the VM is at the desktop and is
        ready to accept application-specific commands.
        """
        return bool(self.machine.state == vboxlib.MachineState.Running)

    def _guest_additions_installed(self) -> bool:
        """
        Check if Guest Additions are installed on the VM.
        """
        return bool(
            self.session.console.guest.additions_state
            != vboxlib.AdditionsRunLevelType.none
        )

    def _is_ready(self) -> bool:
        """
        Check if the VM is ready to accept application-specific commands.

        This is equivalent to checking if the VM is at the desktop.
        """
        if not self._is_running():
            return False

        return bool(
            self.session.console.guest.additions_status
            == vboxlib.AdditionsRunLevelType.Desktop
        )

    def start_vm(
        self,
        frontend: VBoxFrontendEnum,
        environment_changes: list[str] | None = None,
    ) -> bool:
        """
        Start the virtual machine.

        :param frontend: The frontend to use when starting the VM.
        :param environment_changes: A list of environment changes to apply to
            the VM. See the `virtualbox` library for more information. If `None`,
            an empty list is used.
        :return: True if the machine was started, False otherwise.
        """
        # launch_vm_process unconditionally expects a list
        if environment_changes is None:
            environment_changes = []

        future = self.machine.launch_vm_process(
            self.session, frontend.value, environment_changes
        )
        future.wait_for_completion()
        return True

    def stop_vm(self, force: bool = False) -> bool:
        """
        Stop the virtual machine.

        If `force` is False, this method blocks until VirtualBox reports that
        the machine state is PoweredOff. If `force` is True, this method returns
        immediately.

        :param force: If True, the machine is powered off (equivalent to pulling
            the plug). If False, an ACPI shutdown is attempted.
        :return: True if the machine was stopped, False otherwise.
        """

        if force:
            # Pull the plug
            self.session.console.power_down()
        else:
            # ACPI shutdown
            self.session.console.power_button()
            while self.machine.state != vboxlib.MachineState.PoweredOff:
                pass

        return True

    def send_keyboard_event(self, *args, **kwargs):
        """
        Issue keyboard events to the VM.
        """
        raise NotImplementedError
        # self.session.console.keyboard.put_keys()

    def send_mouse_event(self, x: int, y: int, event: VBoxMouseClickEnum) -> bool:
        """
        Issue mouse events to the VM.

        :param x: The absolute x-coordinate of the mouse event.
        :param y: The absolute y-coordinate of the mouse event.
        :param event: The type of mouse event to issue.
        """
        self.session.console.mouse.put_mouse_event_absolute(x, y, 0, 0, event.value)

        return True

    def execute_process(
        self,
        executable: str,
        arguments: list[str] | None = None,
        cwd: str | None = None,
        environment_changes: list[str] | None = None,
        flags: list[vboxlib.ProcessCreateFlag] | None = None,
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

    def attach_drive(self, *args, **kwargs) -> bool:
        # ~ attach_usb_device
        raise NotImplementedError

    def detach_drive(self, *args, **kwargs) -> bool:
        # ~ detach_usb_device
        raise NotImplementedError

    def mount_shared_directory(self, *args, **kwargs) -> bool:
        # ~create_shared_directory
        raise NotImplementedError

    def verify_shared_directory(self, *args, **kwargs) -> bool:
        # ~validate_shared_directory
        raise NotImplementedError

    def unmount_shared_directory(self, *args, **kwargs) -> bool:
        # ~remove_shared_directory
        raise NotImplementedError

    def set_bios_time(self, time: datetime.datetime) -> bool:
        """
        Set the BIOS time of the machine to the provided time
        """
        raise NotImplementedError

    def create_disk_image(self, *args, **kwargs) -> bool:
        raise NotImplementedError

    def create_memory_dump(self, *args, **kwargs) -> bool:
        raise NotImplementedError

    def start_network_capture(self, *args, **kwargs) -> bool:
        raise NotImplementedError

    def stop_network_capture(self, *args, **kwargs) -> bool:
        raise NotImplementedError
