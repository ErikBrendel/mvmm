import subprocess
import sys
from typing import *

CPP_GRAPH_CLI_PATH = "/home/ebrendel/util/mvmm-graphs/coupling_graphs"
METRICS_SAVE_PATH = "../metrics/"


class GraphManager:
    def __init__(self):
        self.process = subprocess.Popen(
            [CPP_GRAPH_CLI_PATH],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        self.cmd_history: List[str] = []

    def execute_void(self, commands: List[str]) -> None:
        for part in commands:
            if "|" in part:
                raise Exception("Found | in command! '" + part + "'")
        cmd = "|".join(commands) + "\n"
        self.cmd_history.append(cmd)
        self.process.stdin.write(cmd.encode("utf-8"))
        self.process.stdin.flush()

    def execute_string(self, commands: List[str]) -> str:
        self.execute_void(commands)
        line = self._read_line()
        while not line.startswith("#result "):
            if line.startswith("#progress "):
                pass  # TODO use awesome progress bars!
            else:
                print("[GRAPHS] " + line)
                sys.stdout.flush()
            line = self._read_line()
        return line[len("#result "):]

    def execute_int(self, commands: List[str]) -> int:
        return int(self.execute_string(commands))

    def execute_float(self, commands: List[str]) -> float:
        return float(self.execute_string(commands))

    def execute_strings(self, commands: List[str]) -> List[str]:
        return self.execute_string(commands).split("|")

    def create_node_set(self, nodes: List[str]):
        return self.execute_int(["createNodeSet"] + nodes)

    def get_node_set(self, node_set_id: int):
        return self.execute_strings(["getNodeSet", str(node_set_id)])

    def _read_line(self):
        return self.process.stdout.readline().decode("utf-8").rstrip()


graph_manager = GraphManager()


class Graph:
    def __init__(self, creation_cmd_or_id: Union[int, List[str]]):
        if isinstance(creation_cmd_or_id, int):
            self.id = creation_cmd_or_id
        else:
            self.id = graph_manager.execute_int(creation_cmd_or_id)

    @property
    def name(self):
        return self._exec_string("getGraphName")

    def get_node_set(self):
        return self._exec_strings("getGraphNodeSet")

    def save_node_set(self):
        return self._exec_int("saveNodeSet")

    def get_normalized_support(self, node: str) -> float:
        return self._exec_float("getNormalizedSupport", [node])

    def get_normalized_coupling(self, a: str, b: str) -> float:
        return self._exec_float("getNormalizedCoupling", [a, b])

    def save(self, repo_name: str) -> None:
        self._exec_void("save", [repo_name, METRICS_SAVE_PATH])

    @staticmethod
    def load(repo_name: str, name: str, cls=None) -> 'Graph':
        if cls is None:
            cls = Graph
        return cls(graph_manager.execute_int(["load", repo_name, name, METRICS_SAVE_PATH]))

    def how_well_predicts_missing_node(self, node_set: List[str], node_missing_from_set: str, all_nodes_id: int) -> float:
        return self._exec_float("howWellPredictsMissingNode", [str(all_nodes_id), node_missing_from_set] + node_set)

    def print_statistics(self):
        self._exec_void("printStatistics")

    def _exec_void(self, cmd: str, other_args: List[str] = []) -> None:
        graph_manager.execute_void([cmd, str(self.id)] + other_args)

    def _exec_int(self, cmd: str, other_args: List[str] = []) -> int:
        return graph_manager.execute_int([cmd, str(self.id)] + other_args)

    def _exec_float(self, cmd: str, other_args: List[str] = []) -> float:
        return graph_manager.execute_float([cmd, str(self.id)] + other_args)

    def _exec_string(self, cmd: str, other_args: List[str] = []) -> str:
        return graph_manager.execute_string([cmd, str(self.id)] + other_args)

    def _exec_strings(self, cmd: str, other_args: List[str] = []) -> List[str]:
        return graph_manager.execute_strings([cmd, str(self.id)] + other_args)


class ExplicitCouplingGraph(Graph):
    def __init__(self, name_or_id: Union[int, str]):
        if isinstance(name_or_id, int):
            Graph.__init__(self, name_or_id)
        else:
            Graph.__init__(self, ["createExplicit", name_or_id])

    def add(self, a: str, b: str, delta: float):
        self._exec_void("explicitAdd", [a, b, str(delta)])

    def add_support(self, node: str, delta: float):
        self._exec_void("explicitAddSupport", [node, str(delta)])

    def add_and_support(self, a: str, b: str, delta: float):
        self._exec_void("explicitAddAndSupport", [a, b, str(delta)])

    def cutoff_edges(self, minimum_weight: float):
        self._exec_void("explicitCutoffEdges", [str(minimum_weight)])

    def propagate_down(self, layers=1, weight_factor=0.2):
        self._exec_void("explicitPropagateDown", [str(layers), str(weight_factor)])

    def dilate(self, iterations=1, weight_factor=0.2):
        self._exec_void("explicitDilate", [str(iterations), str(weight_factor)])


class SimilarityCouplingGraph(Graph):
    def __init__(self, name_or_id: Union[int, str]):
        if isinstance(name_or_id, int):
            Graph.__init__(self, name_or_id)
        else:
            Graph.__init__(self, ["createSimilarity", name_or_id])

    def add_node(self, node: str, coordinates: List[float], support: float):
        self._exec_void("similarityAddNode", [node] + [str(c) for c in coordinates] + [str(support)])


class ModuleDistanceCouplingGraph(Graph):
    def __init__(self, id: Optional[int] = None):
        if id is None:
            Graph.__init__(self, ["createModuleDistance"])
        else:
            Graph.__init__(self, id)


class CachedCouplingGraph(Graph):
    def __init__(self, wrapped_or_id: Union[int, Graph]):
        if isinstance(wrapped_or_id, int):
            Graph.__init__(self, wrapped_or_id)
        else:
            Graph.__init__(self, ["createCached", str(wrapped_or_id.id)])


class CombinedCouplingGraph(Graph):
    def __init__(self, graphs_or_id: Union[int, List[Graph]], weights: Optional[List[float]] = None):
        if isinstance(graphs_or_id, int):
            Graph.__init__(self, graphs_or_id)
        else:
            if weights is None:
                Graph.__init__(self, ["createCombination"] + [str(g.id) for g in graphs_or_id])
            else:
                Graph.__init__(self, ["createCombinationWeights"] + [str(g.id) for g in graphs_or_id] + [str(w) for w in weights])

    def set_weights(self, new_weights: List[float]):
        self._exec_void("combinedSetWeights", [str(w) for w in new_weights])


if __name__ == "__main__":
    g1 = ModuleDistanceCouplingGraph()
    print(g1.name)
    g1.print_statistics()

    g2 = ExplicitCouplingGraph("structural")
    g2.add_and_support("test1", "test2", 2)
    g2.add_and_support("test3", "test2", 1)
    print(g2.name)
    print(g2.get_normalized_support("test1"))
    print(g2.get_normalized_support("test2"))
    print(g2.get_normalized_support("test3"))
    print(g2.get_normalized_support("test4"))
    print(g2.get_normalized_coupling("test1", "test2"))
    print(g2.get_normalized_coupling("test2", "test1"))
    print(g2.get_normalized_coupling("test3", "test2"))
    print(g2.get_normalized_coupling("test2", "test3"))
    print(g2.get_normalized_coupling("test3", "test1"))
    print(g2.get_normalized_coupling("test1", "test3"))
    print(g2.get_normalized_coupling("test4", "test3"))
    g2.print_statistics()

    g3 = SimilarityCouplingGraph("linguistic")
    g3.add_node("test1", [0.8, 0.2, 0], 10)
    g3.add_node("test2", [0.4, 0.4, 0.2], 3)
    g3.add_node("test3", [0.2, 0.6, 0.2], 30)
    print(g3.name)
    print(g3.get_normalized_support("test1"))
    print(g3.get_normalized_support("test2"))
    print(g3.get_normalized_support("test3"))
    print(g3.get_normalized_support("test4"))
    print(g3.get_normalized_coupling("test1", "test2"))
    print(g3.get_normalized_coupling("test2", "test1"))
    print(g3.get_normalized_coupling("test3", "test2"))
    print(g3.get_normalized_coupling("test2", "test3"))
    print(g3.get_normalized_coupling("test3", "test1"))
    print(g3.get_normalized_coupling("test1", "test3"))
    print(g3.get_normalized_coupling("test4", "test3"))
    g3.print_statistics()
