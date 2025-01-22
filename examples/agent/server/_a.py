import rpyc
from rpyc.core.stream import SocketStream


class AService(rpyc.Service):  # type: ignore[misc]
    def exposed_a(self, arg1: str) -> str:
        return "a" + arg1

    def a(self, rpyc_conn: SocketStream, arg1: str) -> str:
        # various things can happen here, like logging and argument manipulation
        # before we actually invoke the remote call
        return rpyc_conn.root.a(arg1)  # type: ignore[no-any-return]

    def exposed_b(self) -> str:
        return "b"

    def b(self, rpyc_conn: SocketStream) -> str:
        return rpyc_conn.root.b()  # type: ignore[no-any-return]


# advantage: the "API" part can be separated from the same module where the actual
# RPyC services are defined.
#
# this can also be a disadvantage, as it makes it less
# obvious that the API is tied to the service; if arguments change, they'll be
# in two different files.
#
# disadvantage: we can't guarantee that name conflicts won't happen. if two exposed
# functions have the same name across services, one will shadow the other.
# that is, AService.exposed_a() and BService.exposed_a() will conflict, and the
# first imported class will be the only one visible. i dont' know if there's a way
# to assert that this won't happen at runtime.
class AServiceAPI:
    def a(self, rpyc_conn: SocketStream, arg1: str) -> str:
        return rpyc_conn.root.a(arg1)  # type: ignore[no-any-return]

    def b(self, rpyc_conn: SocketStream) -> str:
        return rpyc_conn.root.b()  # type: ignore[no-any-return]
