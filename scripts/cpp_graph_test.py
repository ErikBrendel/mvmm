
from cpp_graph import CppGraph, CppExplicitCouplingGraph, graph_manager

g = CppExplicitCouplingGraph("foo")
g.add_and_support("test", "foo", 4)
g.add_and_support("test", "foo", 5)
g.add_and_support("test", "foo2", 2)

g.save("testperson/testrepo")

g2 = CppGraph.load("testperson/testrepo", "foo", CppExplicitCouplingGraph)


ns = graph_manager.create_node_set(["test", "lol", "xd"])

print(graph_manager.get_node_set(ns))
print(g.get_normalized_coupling("test", "foo"))
print(g2.get_normalized_coupling("test", "foo"))
