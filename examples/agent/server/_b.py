import rpyc


class BService(rpyc.Service):
    def exposed_c(self):
        return "c"

    def exposed_d(self):
        return "d"
