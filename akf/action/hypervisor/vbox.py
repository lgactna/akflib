"""
VirtualBox hypervisor bindings for AKF.
"""

from akf.action.hypervisor.base import HypervisorABC


class VBoxHypervisor(HypervisorABC):
    def __init__(self, name_or_id: str):
        """
        Bind this hypervisor instance to a VirtualBox machine by name or UUID.
        """
        raise NotImplementedError
