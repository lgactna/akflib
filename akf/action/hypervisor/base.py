"""
The hypervisor-agnostic interface.

The concept of a hypervisor interface is inherited from VMPOP, which provides
an ABC for arbitrary hypervisors to be used.
"""

import abc
from typing import Any


class HypervisorABC(abc.ABC):
    """
    The AKF hypervisor interface.

    This class should contain the state necessary to manage a single machine
    through a hypervisor. In turn, instances of this class represent the ability
    to manage and communicate with a single machine. This can be leveraged directly
    or by other parts of the AKF action library to act on the hypervisor.

    The methods in this class should be hypervisor-agnostic, and should be
    implemented in the concrete classes. In general, the methods provided are
    "fundamental" methods that are required to manage a machine, and should be
    available of most hypervisors. To the greatest extent possible, the AKF action
    library should leverage the abstract methods over hypervisor-specific methods.
    Where hypervisor-specific methods are required, they should be typed accordingly.

    TODO: should the hypervisor be independent of the concept of a machine?
    i.e. should this class just be a bunch of static methods, and accept a Machine
    instance or something similar?
    """

    @abc.abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the hypervisor.

        This should cause the instance to be permanently bound to a single VM.
        """
        pass

    @abc.abstractmethod
    def start_vm(self, *args: Any, **kwargs: Any) -> bool:
        """
        Start the virtual machine.

        :return: True if the machine was started, False otherwise.
        """
        pass

    @abc.abstractmethod
    def stop_vm(self, *args: Any, **kwargs: Any) -> bool:
        """
        Stop the virtual machine.

        :return: True if the machine was stopped, False otherwise.
        """
        pass

    @abc.abstractmethod
    def send_keyboard_event(self, *args: Any, **kwargs: Any) -> bool:
        """
        Send a keyboard event to the virtual machine.
        """
        pass

    @abc.abstractmethod
    def send_mouse_event(self, *args: Any, **kwargs: Any) -> bool:
        """
        Send a mouse event to the virtual machine.
        """
        pass

    @abc.abstractmethod
    def execute_process(self, *args: Any, **kwargs: Any) -> bool:
        """
        Execute a process on the virtual machine.
        """
        pass

    @abc.abstractmethod
    def attach_drive(self, *args: Any, **kwargs: Any) -> bool:
        """
        Attach a removable drive to the virtual machine.
        """
        pass

    @abc.abstractmethod
    def detach_drive(self, *args: Any, **kwargs: Any) -> bool:
        """
        Detach a removable drive from the virtual machine.
        """
        pass

    @abc.abstractmethod
    def set_bios_time(self, *args: Any, **kwargs: Any) -> bool:
        """
        Set the BIOS time on the virtual machine.
        """
        pass

    @abc.abstractmethod
    def create_disk_image(self, *args: Any, **kwargs: Any) -> bool:
        """
        Create a disk image from the virtual machine.

        This is equivalent to taking a conventional disk image with a write
        blocker, avoiding the use of software on the VM itself.
        """
        pass

    @abc.abstractmethod
    def create_memory_dump(self, *args: Any, **kwargs: Any) -> bool:
        """
        Create a volatile memory dump from the virtual machine.

        This does not require running an application on the machine itself, which
        is different from the typical process of using something like Magnet Acquire.
        """
        pass

    @abc.abstractmethod
    def start_network_capture(self, *args: Any, **kwargs: Any) -> bool:
        """
        Start capturing network traffic from one of the VM's interfaces.

        This is equivalent to placing a network tap (or similar) on the physical
        line, as opposed to running capture software on the VM itself.
        """
        pass

    @abc.abstractmethod
    def stop_network_capture(self, *args: Any, **kwargs: Any) -> bool:
        """
        Stop capturing network traffic from one of the VM's interfaces.
        """
        pass
