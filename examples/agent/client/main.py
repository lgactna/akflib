import rpyc

c = rpyc.connect("localhost", 18861)
# print(c.root.a("h"))

print(c.root)
