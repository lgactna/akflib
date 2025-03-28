"""
VirtualBox hypervisor bindings for AKF.
"""

import datetime
import logging
import platform
import shutil
import subprocess
import time
from enum import Enum
from pathlib import Path
from types import TracebackType
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


class VBoxExportFormatEnum(str, Enum):
    """
    Supported disk image export formats for the VBoxManage `clonemedium` command.
    """

    RAW = "raw"
    VDI = "vdi"
    VMDK = "vmdk"
    VHD = "vhd"


class TemporarySession:
    """
    A context manager for creating temporary sessions with shared locks.
    """

    def __init__(self, machine: vboxlib.IMachine) -> None:
        self.session = virtualbox.Session()
        self.machine = machine

        self.machine.lock_machine(self.session, vboxlib.LockType.shared)

    def __enter__(self) -> virtualbox.Session:
        return self.session

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.unlock_machine()


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

    def __init__(
        self,
        name_or_id: str,
        case_bundle: Bundle | None = None,
    ) -> None:
        """
        Bind this hypervisor instance to a VirtualBox machine by name or UUID.

        Optionally, also bind this hypervisor instance to a CASE bundle.

        This *does not* lock the generated VirtualBox session.
        """
        # Assign CASE bundle, can be used as needed
        self.case_bundle = case_bundle

        # Get handle to machine, create new session
        self.vbox = virtualbox.VirtualBox()
        self.session = virtualbox.Session()
        self.machine = self.vbox.find_machine(name_or_id)

        # Attempt to locate VBoxManage
        self.vboxmanage = self._locate_vboxmanage()
        if self.vboxmanage is None:
            logger.warning("VBoxManage could not be located.")

        # Other attributes not set until runtime.
        self.guest_session: vboxlib.IGuestSession | None = None

        # A dictionary of logical names to remote paths
        self.shared_folders: dict[str, str] = {}

    def _locate_vboxmanage(self) -> Path | None:
        """
        Find the absolute path to VBoxManage.
        """
        if platform.system() == "Windows":
            # Find VBoxManage in the default install locations
            for path in (
                Path("C:/Program Files/Oracle/VirtualBox/VBoxManage.exe"),
                Path("C:/Program Files (x86)/Oracle/VirtualBox/VBoxManage.exe"),
            ):
                if path.exists():
                    return path.resolve()

        if vbox_path := shutil.which("VBoxManage"):
            return Path(vbox_path).resolve()
        return None

    def _call_vboxmanage(
        self, args: list[str], vboxmanage_path: Path | None = None
    ) -> bool:
        """
        Call VBoxManage with the provided arguments (blocking).

        :param args: A list of arguments to pass to VBoxManage.
        :param vboxmanage_path: The path to VBoxManage. If not set, the path
            determined at initialization time is used.
        :return: True if VBoxManage returns 0, False otherwise.
        """
        if vboxmanage_path is None:
            vboxmanage_path = self.vboxmanage

        if vboxmanage_path is None:
            raise RuntimeError("Path to VBoxManage is not set.")

        # Call VBoxManage
        args = [str(vboxmanage_path)] + args
        s = subprocess.run(args, capture_output=True)

        # Log output
        if s.stdout:
            logger.debug(f"VBoxManage output: {s.stdout.decode()}")
        if s.stderr:
            logger.error(f"VBoxManage error: {s.stderr.decode()}")

        return s.returncode == 0

    def _lock(self, lock_type: vboxlib.LockType = vboxlib.LockType.shared) -> None:
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

        NOTE: In theory, this method should be accurate. However, my own testing
        seems to report nothing but "paused" when the machine is actually running,
        though the intermediate states (powered off, saving, etc.) seem to be
        accurately reported.
        """
        raise RuntimeError("_is_running() is not accurate. Use _is_ready().")

        return bool(self.machine.state == vboxlib.MachineState.running)

    def _poll_guest_additions(
        self, level: vboxlib.AdditionsRunLevelType, timeout: int = 15
    ) -> bool:
        """
        Check if Guest Additions are installed on the VM.

        additions_run_level is not actually reflective of them being installed,
        it's reflective of whether the drivers have been loaded. The drivers
        don't load instantly on startup, so it will gradually transition from
        "system" to "userland" to "desktop".

        :param timeout: The time, in seconds, to poll the Guest Additions
            status.
        :param level: The level to check for. This is one of the values in the
            `AdditionsRunLevelType` enumeration.
        :return: True if the specified level is reached within wait_period,
            False otherwise.
        """        
        # Instant check
        # mypy doesn't have access to the vboxapi library, so it doesn't know
        # this bool compare is correct
        if timeout <= 0:
            return self.session.console.guest.additions_run_level == level  # type: ignore[no-any-return]

        # Delayed check
        while timeout > 0:
            if self.session.console.guest.additions_run_level == level:
                return True

            time.sleep(1)
            timeout -= 1

        return False

    def _start_guest_session(
        self, username: str, password: str = "", session_name: str = ""
    ) -> None:
        """
        Set the username and password for the guest session.
        """
        self.guest_session = self.session.console.guest.create_session(
            username,
            password,
            "",  # Refers to the unsupported "domain" parameter
            session_name,
        )

    def _is_ready(self) -> bool:
        """
        Check if the VM is ready to accept application-specific commands.

        This is equivalent to checking if the VM is at the desktop (note that
        it might take a little longer than when the desktop first appears).
        """

        return bool(
            self.session.console.guest.additions_run_level
            == vboxlib.AdditionsRunLevelType.desktop
        )

    def start_vm(
        self,
        frontend: VBoxFrontendEnum = VBoxFrontendEnum.GUI,
        environment_changes: list[str] | None = None,
        wait_for_guest_additions: bool = True,
        guest_additions_timeout: int = 30,
    ) -> bool:
        """
        Start the virtual machine.

        :param frontend: The frontend to use when starting the VM.
        :param environment_changes: A list of environment changes to apply to
            the VM. See the `virtualbox` library for more information. If `None`,
            an empty list is used.
        :param wait_for_guest_additions: If True, this method blocks until the
            VM reports that Guest Additions is at the "desktop" state.
        :param guest_additions_timeout: The time, in seconds, to wait for Guest
            Additions to be at the "desktop" state. If not set, a default of 30
            seconds is used.
        :return: True if the machine was started, False otherwise.
        """
        # launch_vm_process unconditionally expects a list
        if environment_changes is None:
            environment_changes = []

        future = self.machine.launch_vm_process(
            self.session, frontend.value, environment_changes
        )
        future.wait_for_completion()

        if wait_for_guest_additions:
            logger.info(
                f"Waiting up to {guest_additions_timeout} seconds for the machine to be ready"
            )

            self._poll_guest_additions(
                vboxlib.AdditionsRunLevelType.desktop, guest_additions_timeout
            )

            logger.info("Machine is ready, unblocking")

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

    def clone_vm(
        self,
        target_vm_name: str,
        output_folder: Path | None = None,
    ) -> bool:
        """
        Clone the VM referred to by this instance.

        This *does not* create a new VBoxHypervisor instance for the newly-created VM.
        It does, however, automatically register the new VM with VirtualBox (the
        default is to simply create the VM files and exit).

        :param target_vm_name: The name of the new VM to create.
        :param output_folder: The folder to save the new VM to. If not set,
            VBoxManage's default VM folder is used.
        :return: True if the VM was cloned, False otherwise.
        """
        # IMachine.clone_to() exists, but it's considerably more effort than simply
        # calling VBoxManage

        logger.info(f"Cloning VM {self.machine.id_p} and creating {target_vm_name}.")
        logger.info("This will take a while.")

        args = [
            "clonevm",
            self.machine.id_p,
            f"--name={target_vm_name}",
            "--register",
        ]

        if output_folder is not None:
            args.append(f"--basefolder={output_folder.resolve().as_posix()}")

        result = self._call_vboxmanage(args)
        logger.info(f"VM clone operation for {target_vm_name} finished. ({result=})")

        return result

    def send_keyboard_event(self, *args: Any, **kwargs: Any) -> bool:
        """
        Issue keyboard events to the VM.
        """
        # TODO: Preferring agent-based methods for now since the VirtualBox
        # API for issuing keyboard events is clunky

        raise NotImplementedError
        # self.session.console.keyboard.put_keys()

    def send_mouse_event(self, x: int, y: int, event: VBoxMouseClickEnum) -> bool:
        """
        Issue mouse events to the VM.

        :param x: The absolute x-coordinate of the mouse event.
        :param y: The absolute y-coordinate of the mouse event.
        :param event: The type of mouse event to issue.
        """
        if not self._is_ready():
            logger.info("Attempted to send mouse event, but VM is not yet ready")
            return False

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
        # TODO: for now, preferring agent-based methods for executing processes
        # because of how clunky this is
        raise NotImplementedError

        if not self._is_ready():
            logger.info("Attempted to execute process, but VM is not yet ready")
            return False

    def attach_drive(self, *args: Any, **kwargs: Any) -> bool:
        # ~ attach_usb_device
        raise NotImplementedError

    def detach_drive(self, *args: Any, **kwargs: Any) -> bool:
        # ~ detach_usb_device
        raise NotImplementedError

    def mount_shared_directory(
        self,
        host_path: Path,
        remote_path: str,
        writable: bool = True,
        automount: bool = True,
        logical_name: str = "shared_folder",
        wait_until_folder_exists: bool = True,
    ) -> bool:
        """
        Mount a directory on the host machine to a drive letter on the guest
        machine. On Windows, this appears as a network drive.

        Equivalent to VMPOP's create_shared_directory() function. This, in turn,
        depends on the IMachine.createSharedFolder() function in the VirtualBox
        SDK. See the linked page below for full details.

        https://www.virtualbox.org/sdkref/interface_i_machine.html#a56d8797225812968b96f0663a02bd4ff

        :param host_path: The path to the directory on the host machine.
        :param remote_path: The path to the directory on the guest machine. Must
            be a drive letter on Windows, or an absolute path on other operating
            systems.
        :param writable: If True, the shared folder is writable. If False, it is
            read-only.
        :param automount: If True, the shared folder is automatically mounted
            as soon as this command finishes. Otherwise, it must be mounted
            manually.
        :param logical_name: The logical name of the shared folder. This is used
            to identify the shared folder through the VirtualBox API.
        :param wait_until_folder_exists: If True, this method will block until
            the shared folder is observed to exist on the guest machine.
        :return: True if the shared folder was created, False otherwise.

        """
        if not self._is_ready():
            logger.info("Attempted to add shared folder, but VM is not yet ready")
            return False

        self.session.machine.create_shared_folder(
            logical_name,
            host_path.resolve().as_posix(),
            writable,
            automount,
            remote_path,
        )
        self.session.machine.save_settings()

        if wait_until_folder_exists:
            if self.guest_session is None:
                raise RuntimeError("Guest session is not set.")

            while not self.guest_session.directory_exists(remote_path, True):
                pass

        self.shared_folders[logical_name] = remote_path

        return True

    def verify_shared_directory(self, name_or_path: str) -> bool:
        """
        Check that a shared directory exists on the guest machine.

        If `name` is a logical name, this method checks that the shared directory
        with that logical name exists. If `name` is a path, this method checks
        that the shared directory at that path exists.

        This is equivalent to the VMPOP function `validate_shared_directory()`.

        :param name_or_path: The logical name or path of the shared directory to
            verify.
        :return: True if the shared directory exists, False otherwise.
        """
        if not self._is_ready():
            logger.info("Attempted to check for shared folder, but VM is not yet ready")
            return False

        if self.guest_session is None:
            raise RuntimeError("Guest session is not set.")

        if name_or_path in self.shared_folders:
            result = self.guest_session.directory_exists(
                self.shared_folders[name_or_path]
            )
            assert isinstance(result, bool)
            return result

        result = self.guest_session.directory_exists(name_or_path)
        assert isinstance(result, bool)
        return result

    def unmount_shared_directory(self, name_or_path: str) -> bool:
        """
        Unmount a shared directory from the guest machine.

        If `name` is determined to be a logical name, this method unmounts the
        shared directory with that logical name. If `name` is a path, this method
        unmounts the shared directory at that path, if it can be mapped in reverse
        to a logical name. Once unmounted, the shared directory is removed from
        the internal dictionary of shared directories.

        A warning is raised if a shared directory with the provided name or path
        does not appear to exist.

        This is equivalent to the VMPOP function `remove_shared_directory()`.

        :param name_or_path: The logical name or path of the shared directory to
            unmount.
        :return: True if the shared directory was unmounted, False otherwise.
        """
        # TODO: this might not require that the VM is ready, I believe this goes
        # through VirtualBox itself

        # Check if the shared directory exists as a path by reversing the
        # shared_folders dictionary
        inverse_shared_folders = {v: k for k, v in self.shared_folders.items()}
        if name_or_path in inverse_shared_folders:
            logical_name = inverse_shared_folders[name_or_path]
        else:
            logical_name = name_or_path

        self.session.machine.remove_shared_folder(logical_name)
        self.session.machine.save_settings()

        return True

    def set_bios_time(self, time: datetime.datetime) -> bool:
        """
        Set the BIOS time of the machine to the provided time.

        Internally, this method sets the time offset of the machine to the
        difference between the provided time and the host time, in milliseconds.
        """
        # Create and lock temporary shared session
        with TemporarySession(self.machine) as session:
            # Calculate millisecond offset between host and guest time, set offset
            time_offset = (time - datetime.datetime.now()).total_seconds() * 1000
            session.machine.bios_settings.time_offset = time_offset
            session.machine.save_settings()

        return True

    def create_disk_image(
        self,
        output_path: Path,
        image_format: VBoxExportFormatEnum,
        disk_uuid: str | None = None,
    ) -> bool:
        """
        Use VBoxManage to create a disk image from the VM's disk.

        After the disk is created, it is removed from the list of registered
        disks in VirtualBox. This is consistent with the behavior of VMPOP's
        `export_disk()` function.

        If no disk is specified by `disk_uuid`, the largest attached disk to the
        current machine is assumed to be the primary disk, and is exported and
        cloned.

        Note that in many cases, it is sufficient to simply copy the virtual
        hard drive from the VM's directory as-is for typical analysis purposes.

        Also, note that Windows 11 has disk encryption enabled by default as of
        version 24H2. If the basic disk partition appears to be "unreadable" after
        exporting it to a raw disk image, this is likely the cause. If you plan
        to perform actions such as manual carving on the disk image, you should
        plan on disabling encryption.

        :param output_path: The path to save the disk image to.
        :param image_format: The format of the disk image to create.
        :param disk_uuid: The UUID of the disk to export. If not set, the largest
            disk attached to the machine is assumed to be the primary disk.
        :return: True if the disk image was created, False otherwise.
        """
        # Determine disk to export
        if disk_uuid is None:
            # Iterate through all medium attachments, find largest disk
            largest_disk_size = 0
            for attachment in self.machine.medium_attachments:
                if attachment.medium is None:
                    continue

                # if attachment.medium.type_p == vboxlib.MediumType.Normal:
                if attachment.medium.size > largest_disk_size:
                    disk_uuid = attachment.medium.id_p
                    largest_disk_size = attachment.medium.size

            logger.info(
                f"Exporting disk {disk_uuid} (size: {largest_disk_size}) as primary disk."
            )

        logger.info(
            f"Exporting disk {disk_uuid} to {output_path}. This may take some time."
        )

        assert disk_uuid is not None

        # Export disk using VBoxManage
        # https://www.virtualbox.org/manual/ch08.html#vboxmanage-clonemedium
        result = self._call_vboxmanage(
            [
                "clonemedium",
                disk_uuid,
                output_path.resolve().as_posix(),
                f"--format={image_format.value}",
            ]
        )

        logger.info(f"Disk export command finished. ({result=})")

        # Attempt to close the newly created disk (which removes it from the
        # list of registered disks in VirtualBox)
        for disk in reversed(self.vbox.hard_disks):
            if Path(disk.location).resolve() == output_path.resolve():
                logger.info(
                    f"Closing/unregistering disk {disk.id_p=} ({disk.location=})"
                )
                disk.close()
                break

        return result

    def create_memory_dump(self, output_path: Path) -> bool:
        """
        Create a memory dump of the VM.

        This method is equivalent to the VMPOP function `dump_physical_memory()`.

        :param output_path: The path to save the memory dump to.
        :return: True if the memory dump was created, False otherwise.
        """

        self.session.console.debugger.dump_guest_core(output_path.resolve().as_posix())
        return True

    def _get_non_host_adapter(self, limit: int = 4) -> vboxlib.INetworkAdapter | None:
        """
        Get the first non-host-only adapter attached to the VM.

        :param limit: The maximum number of network adapters to check.
        """
        logger.info("Searching for first host-only adapter")
        for i in range(0, limit):
            adapter = self.machine.get_network_adapter(i)
            if adapter.attachment_type != vboxlib.NetworkAttachmentType.host_only:
                logger.info(f"Returning adapter {i} as the host-only adapter")
                return adapter

        return None

    def get_maintenance_ip(self) -> str:
        """
        Get the IP address of the maintenance (RPyC) network interface.
        """
        adapter = self._get_non_host_adapter()
        if adapter is None:
            raise RuntimeError("No non-host-only adapter found.")

        ip_prop = self.machine.enumerate_guest_properties(
            f"/VirtualBox/GuestInfo/Net/{adapter.slot}/V4/IP"
        )

        host_ip_address = ip_prop[1][0]
        assert isinstance(host_ip_address, str)

        logger.info(f"Maintenance IP is {host_ip_address}")

        return host_ip_address

    def start_network_capture(
        self,
        output_path: Path,
        adapter_id: int | None = None,
    ) -> bool:
        """
        Start a network capture on the specified interface.

        If no interface is specified, the first non-host-only adapter is used
        (on the assumption that the host-only adapter is the maintenance
        interface).

        This method is equivalent to the VMPOP function `start_network_capture()`.
        """
        # Iterate through all network adapters
        if adapter_id is None:
            adapter = self._get_non_host_adapter()
            if adapter is None:
                raise RuntimeError("No non-host-only adapter found.")
            adapter_id = adapter.slot

        logger.info(f"Starting network capture on adapter {adapter_id}")
        adapter = self.machine.get_network_adapter(adapter_id)

        with TemporarySession(self.machine) as session:
            adapter.trace_enabled = True
            adapter.trace_file = output_path.resolve().as_posix()
            session.machine.save_settings()

        return True

    def stop_network_capture(self, adapter_id: int | None = None) -> bool:
        """
        Stop a network capture on the specified interface.

        If no interface is specified, the first non-host-only adapter is used
        (on the assumption that the host-only adapter is the maintenance
        interface).

        This method is equivalent to the VMPOP function `stop_network_capture()`.
        """
        if adapter_id is None:
            adapter = self._get_non_host_adapter()
            if adapter is None:
                raise RuntimeError("No non-host-only adapter found.")
            adapter_id = adapter.slot

        logger.info(f"Stopping network capture on adapter {adapter_id}")
        adapter = self.machine.get_network_adapter(adapter_id)

        with TemporarySession(self.machine) as session:
            adapter.trace_enabled = False
            session.machine.save_settings()

        return True
