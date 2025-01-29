"""
Shared definitions for agent servers/services.
"""

import rpyc


# ignore: mypy does not recognize the `rpyc.Service` class
class AKFService(rpyc.Service):  # type: ignore[misc]
    pass
