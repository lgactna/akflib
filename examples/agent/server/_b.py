import rpyc


class BService(rpyc.Service):  # type: ignore[misc]
    def exposed_c(self) -> str:
        return "c"

    def exposed_d(self) -> str:
        return "d"
