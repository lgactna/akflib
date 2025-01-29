"""
Shared definitions for agent clients.
"""

import logging
from types import TracebackType
from typing import Type, TypeVar

import rpyc

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="AKFServiceAPI")


class AKFServiceAPI:
    def __init__(self, host: str, port: int) -> None:
        """
        Initialize the "API" with an RPyC connection to the service.

        This may be used as a context manager, in which case the RPyC connection
        will be closed when the context exits.

        `rpyc_conn` may be used to interact with the service directly, as needed.
        """
        try:
            self.rpyc_conn = rpyc.connect(
                host,
                port,
                config={
                    # "allow_all_attrs": True,
                    "sync_request_timeout": None,  # Wait forever for responses
                },
            )
        except ConnectionRefusedError as e:
            logger.error(f"Could not connect to RPyC service at {host}:{port}")
            raise e

    def __enter__(self: T) -> "T":
        return self

    def __exit__(
        self,
        exctype: Type[BaseException] | None,
        excinst: BaseException | None,
        exctb: TracebackType | None,
    ) -> None:
        self.rpyc_conn.close()
