import subprocess
import sys
import os
from typing import *

from util import log_progress, show_histogram

CPP_GRAPH_CLI_PATH = os.getenv("COUPLING_GRAPH_EXECUTABLE", "/home/ebrendel/util/mvmm-graphs/coupling_graphs")
METRICS_SAVE_PATH = "../metrics/"
LOG_COMMANDS = False


class GraphManager:
    def __init__(self):
        self.process = subprocess.Popen(
            [CPP_GRAPH_CLI_PATH],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        self.current_progress_bar = None
        self.progress_name: Optional[str] = None

    def execute_void(self, commands: List[str]) -> None:
        for part in commands:
            if "|" in part:
                raise Exception("Found | in command! '" + part + "'")
            if "\n" in part:
                raise Exception("Found line break in command! '" + part.replace("\n", "\\n") + "'")
        cmd = "|".join(commands) + "\n"
        if LOG_COMMANDS:
            print("[CG] " + cmd[:-1])
        try:
            self.process.stdin.write(cmd.encode("utf-8"))
            self.process.stdin.flush()
        except BrokenPipeError as e:
            print("Command failed: " + cmd[:-1])
            raise e

    def execute_string(self, commands: List[str]) -> str:
        self.execute_void(commands)
        line = self._read_line()
        while not line.startswith("#result"):
            if line.startswith("#progress "):
                progress_parts = line[len("#progress "):].split(" ", 2)
                self._show_progress(int(progress_parts[0]), int(progress_parts[1]), progress_parts[2])
            else:
                if "Unknown command" in line:
                    raise Exception(f"LAST COMMAND FAILED: {'|'.join(commands)} | Error message: {line}")
                if len(line) > 0:
                    print("[G] " + line)
                    sys.stdout.flush()
            line = self._read_line()
        return line[len("#result"):].lstrip()

    def execute_int(self, commands: List[str]) -> int:
        return int(self.execute_string(commands))

    def execute_float(self, commands: List[str]) -> float:
        return float(self.execute_string(commands))

    def execute_strings(self, commands: List[str]) -> List[str]:
        result = self.execute_string(commands)
        if len(result) == 0:
            return []
        return result.split("|")

    def create_node_set(self, nodes: List[str]):
        return self.execute_int(["createNodeSet"] + nodes)

    def get_node_set(self, node_set_id: int):
        return self.execute_strings(["getNodeSet", str(node_set_id)])

    def _read_line(self):
        line = self.process.stdout.readline().decode("utf-8").rstrip()
        if len(line) == 0:
            self.process.poll()
            if self.process.returncode is not None:
                if self.process.returncode < 0:
                    raise Exception("Coupling Graph Subprocess was terminated with POSIX signal " + str(-self.process.returncode) + "!")
                else:
                    raise Exception("Coupling Graph Subprocess terminated with " + str(self.process.returncode) + "!")
        return line

    def _show_progress(self, progress, total, description):
        if description != self.progress_name and self.current_progress_bar is not None:
            self.current_progress_bar.close()
            self.current_progress_bar = None
        if self.current_progress_bar is None:
            self.progress_name = description
            self.current_progress_bar = log_progress(desc="[G] " + description)
        self.current_progress_bar.total = total
        self.current_progress_bar.n = progress
        self.current_progress_bar.update(0)
        if progress == total:
            self.current_progress_bar.close()
            self.current_progress_bar = None

    def flush(self):
        self.execute_string(["echo", "foo"])


graph_manager = GraphManager()


class CouplingGraph:
    def __init__(self, creation_cmd_or_id: Union[int, List[str]]):
        if isinstance(creation_cmd_or_id, int):
            self.id = creation_cmd_or_id
        else:
            self.id = graph_manager.execute_int(creation_cmd_or_id)

    @property
    def name(self):
        return self._exec_string("getGraphName")

    def get_node_set(self) -> Optional[Set[str]]:
        return set(self._exec_strings("getGraphNodeSet"))

    def save_node_set(self):
        return self._exec_int("saveNodeSet")

    def get_normalized_support(self, node: str) -> float:
        return self._exec_float("getNormalizedSupport", [node])

    def get_normalized_coupling(self, a: str, b: str) -> float:
        return self._exec_float("getNormalizedCoupling", [a, b])

    def save(self, repo_name: str) -> None:
        self._exec_void("save", [repo_name, METRICS_SAVE_PATH])

    @staticmethod
    def load(repo_name: str, name: str, cls=None) -> 'CouplingGraph':
        if cls is None:
            cls = CouplingGraph
        return cls(graph_manager.execute_int(["load", repo_name, name, METRICS_SAVE_PATH]))

    @staticmethod
    def pickle_path(repo_name, name):
        return graph_manager.execute_string(["getSaveLocation", repo_name, name, METRICS_SAVE_PATH])

    def how_well_predicts_missing_node(self, node_set: List[str], node_missing_from_set: str, all_nodes_id: int) -> float:
        return self._exec_float("howWellPredictsMissingNode", [str(all_nodes_id), node_missing_from_set] + node_set)

    def print_statistics(self):
        self._exec_void("printStatistics")
        self._flush()

    def get_most_linked_node_pairs(self, amount: int) -> List[Tuple[float, str, str]]:
        return [(float(w), a, b) for w, a, b in (p.split(";") for p in self._exec_strings("getMostLinkedNodePairs", [str(amount)]))]

    def print_most_linked_nodes(self, amount=10):
        print("Most linked nodes:")
        debug_list = self.get_most_linked_node_pairs(amount)
        for w, a, b in debug_list[0:amount]:
            print(str(w) + ": " + a + " <> " + b)

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

    def _exec_ints(self, cmd: str, other_args: List[str] = []) -> List[int]:
        return [int(v) for v in self._exec_strings(cmd, other_args)]

    def _flush(self):
        graph_manager.flush()


class ExplicitCouplingGraph(CouplingGraph):
    def __init__(self, name_or_id: Union[int, str]):
        if isinstance(name_or_id, int):
            CouplingGraph.__init__(self, name_or_id)
        else:
            CouplingGraph.__init__(self, ["createExplicit", name_or_id])

    def add(self, a: str, b: str, delta: float):
        self._exec_void("explicitAdd", [a, b, str(delta)])

    def add_support(self, node: str, delta: float):
        self._exec_void("explicitAddSupport", [node, str(delta)])

    def add_and_support(self, a: str, b: str, delta: float):
        self._exec_void("explicitAddAndSupport", [a, b, str(delta)])

    def cutoff_edges(self, minimum_weight: float):
        self._exec_void("explicitCutoffEdges", [str(minimum_weight)])
        self._flush()

    def remove_small_components(self, minimum_component_size: int):
        self._exec_void("explicitRemoveSmallComponents", [str(minimum_component_size)])
        self._flush()

    def propagate_down(self, layers=1, weight_factor=0.2):
        self._exec_void("explicitPropagateDown", [str(layers), str(weight_factor)])
        self._flush()

    def dilate(self, iterations=1, weight_factor=0.2):
        self._exec_void("explicitDilate", [str(iterations), str(weight_factor)])
        self._flush()
        
    def get_data(self) -> Tuple[List[str], List[float], List[Tuple[int, int, float]]]:
        # see the c++ program for the output format specification, but it should be this:
        # line 1: format specifier (always "Explicit")
        # line 2: all node strings
        # line 3: support values for each node
        # line 4: all edges, by node index "n1,n2,weight"
        type_name, raw_node_names, raw_supports, raw_edges, *_ = self._exec_strings("explicitGetData")
        if type_name != "Explicit":
            raise Exception("expected explicit type for getting data")
        node_names = raw_node_names.split(";")
        supports = [float(support) for support in raw_supports.split(";")]
        edges = [(int(n1), int(n2), float(weight)) for n1, n2, weight in (edge_data.split(",") for edge_data in raw_edges.split(";"))]
        return node_names, supports, edges

    def get_connected_component_sizes(self):
        return self._exec_ints("getConnectedComponentSizes")

    def show_weight_histogram(self):
        node_names, supports, edges = self.get_data()

        edge_weights = [w for n1, n2, w in edges]
        show_histogram(edge_weights, 'Histogram of edge weights in coupling graph', 'Coupling Strength', 'Amount', 'b')

        node_weights = [0.0 for _n in supports]
        for n1, n2, w in edges:
            node_weights[n1] += w
            node_weights[n2] += w
        show_histogram(node_weights, 'Histogram of node weights', 'Coupling Strength', 'Amount', 'g')

        show_histogram(supports, 'Histogram of node support values', 'Support', 'Amount', 'g')


class SimilarityCouplingGraph(CouplingGraph):
    def __init__(self, name_or_id: Union[int, str]):
        if isinstance(name_or_id, int):
            CouplingGraph.__init__(self, name_or_id)
        else:
            CouplingGraph.__init__(self, ["createSimilarity", name_or_id])

    def add_node(self, node: str, coordinates: List[float], support: float):
        self._exec_void("similarityAddNode", [node] + [str(c) for c in coordinates] + [str(support)])

    def similarity_get_node(self, node_name: str) -> Optional[Tuple[float, List[float]]]:
        """get support and coords of node"""
        result = self._exec_strings("similarityGetNode", [node_name])
        if len(result) == 0:
            return None
        return float(result[0]), [float(c) for c in result[1:]]

    def similarity_has_node(self, node_name: str) -> bool:
        supp_coords = self.similarity_get_node(node_name)
        if supp_coords is None:
            return False
        supp, coords = supp_coords
        return supp > 0 and sum(coords) > 0  # float > 0 is also false for NaN


class ModuleDistanceCouplingGraph(CouplingGraph):
    def __init__(self, id: Optional[int] = None):
        if id is None:
            CouplingGraph.__init__(self, ["createModuleDistance"])
        else:
            CouplingGraph.__init__(self, id)

    def save(self, repo_name: str):
        pass

    def get_node_set(self) -> None:
        return None


class CachedCouplingGraph(CouplingGraph):
    def __init__(self, wrapped_or_id: Union[int, CouplingGraph]):
        if isinstance(wrapped_or_id, int):
            CouplingGraph.__init__(self, wrapped_or_id)
        else:
            CouplingGraph.__init__(self, ["createCached", str(wrapped_or_id.id)])


class CombinedCouplingGraph(CouplingGraph):
    def __init__(self, graphs_or_id: Union[int, List[CouplingGraph]], weights: Optional[Sequence[float]] = None):
        if isinstance(graphs_or_id, int):
            CouplingGraph.__init__(self, graphs_or_id)
        else:
            if weights is None:
                CouplingGraph.__init__(self, ["createCombination"] + [str(g.id) for g in graphs_or_id])
            else:
                CouplingGraph.__init__(self, ["createCombinationWeights"] + [str(g.id) for g in graphs_or_id] + [str(w) for w in weights])

    def set_weights(self, new_weights: List[float]):
        self._exec_void("combinedSetWeights", [str(w) for w in new_weights])


if __name__ == "__main__":
    g1 = ModuleDistanceCouplingGraph()
    print(g1.name)
    g1.print_statistics()

    g2 = ExplicitCouplingGraph("references")
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
