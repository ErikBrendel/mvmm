from abc import ABC, abstractmethod
import pickle
import networkx as nx
import numpy as np
from scipy.spatial import distance
import os
import pdb

from util import *


METRICS_SAVE_PATH = "../metrics/"
EXPORT_SAVE_PATH = "../export/"

class CouplingGraph(ABC):
    def __init__(self, name):
        self.name = name
        
    def get_node_set(self):
        return None
    
    @abstractmethod
    def get_normalized_support(self, node):
        pass
    
    @abstractmethod
    def get_normalized_coupling(self, a, b):
        pass

    def save(self, repo_name):
        os.makedirs(METRICS_SAVE_PATH + repo_name, exist_ok=True)
        with open(CouplingGraph.pickle_path(repo_name, self.name), 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(repo_name, name):
        with open(CouplingGraph.pickle_path(repo_name, name), 'rb') as f:
            return pickle.load(f)

    @staticmethod
    def pickle_path(repo_name, name):
        # see https://networkx.github.io/documentation/stable/reference/readwrite/gpickle.html
        return METRICS_SAVE_PATH + repo_name + "/" + name + ".gpickle"
    
    def plaintext_save(self, repo_name):
        content = self.plaintext_content()
        os.makedirs(EXPORT_SAVE_PATH + repo_name, exist_ok=True)
        with open(EXPORT_SAVE_PATH + repo_name + "/" + self.name + ".graph.txt", "w") as f:
            f.write(content)
    
    @abstractmethod
    def plaintext_content(self):
        pass
    
    @abstractmethod
    def print_statistics(self):
        pass
    
    def show_weight_histogram(self):
        print("No Histogram Data to show for " + type(self).__name__)
        
    def visualize(self, use_spring = False, with_labels = True):
        print("No visualization for " + type(self).__name__)
    
    def print_most_linked_nodes(self, amount = 10):
        print("No Most Linked Nodes Data for " + type(self).__name__)


class NodeSetCouplingGraph(CouplingGraph):
    def __init__(self, name):
        CouplingGraph.__init__(self, name)
        self.children = None
        
    @abstractmethod
    def get_node_set(self):
        pass
    
    def create_child_cache(self):
        self.children = {}
        for n in self.get_node_set():
            self.children.setdefault(n, set())
            while n is not None:  # TODO no loop needed?
                p = self.get_parent(n)
                self.children.setdefault(p, set()).add(n)
                n = p
        
    def get_children(self, node):
        if self.children is None or node not in self.children:
            self.create_child_cache()
        return self.children.get(node, [])
        
    def get_parent(self, node):
        if len(node) <= 1:
            return None
        return "/".join(node.split("/")[:-1])


class NormalizeSupport(ABC):
    def __init__(self):
        self.median_maximum_support_cache = None
    
    """@abstractmethod
    def get_absolute_support(self, node):
        pass"""

    def get_normalized_support(self, node):
        """
        on a scale of [0, 1], how much support do we have for coupling values with that node?
        This should depend on how much data (including children) we have for this node, relative to how much data is normal in this graph.
        It should also be outlier-stable, so that having median-much data maybe results in a support score of 0.5?
        """
        abs_supp = self.get_absolute_support(node)
        median, maximum = self.get_absolute_support_median_and_max()
        if abs_supp <= median:
            return 0.5 * abs_supp / median
        else:
            return 0.5 + (0.5 * (abs_supp - median) / (maximum - median))
    
    def get_absolute_support_median_and_max(self):
        if self.median_maximum_support_cache is None:
            supports = list([self.get_absolute_support(node) for node in self.get_node_set()])
            mean = np.mean(supports) # TODO mean seems to fit better?
            maximum = max(supports)
            self.median_maximum_support_cache = (mean, maximum)
        return self.median_maximum_support_cache

class NormalizeSupportWithChildren(NormalizeSupport):
    def __init__(self):
        NormalizeSupport.__init__(self)
        
    """@abstractmethod
    def get_absolute_self_support(self, node):
        pass
    
    @abstractmethod
    def get_children(self, node):
        pass"""
    
    def get_absolute_support(self, node):
        result = self.get_absolute_self_support(node)
        for child in self.get_children(node):
            result += self.get_absolute_support(child)
        return result


class NormalizeCouplingWithChildren:
    def __init__(self):
        self.total_relative_coupling_cache = {}
    """
    @abstractmethod
    def get_children(self, node):
        pass
    
    @abstractmethod
    def get_parent(self, node):
        pass
    
    @abstractmethod
    def get_directly_coupled(self, node):
        # list of nodes that are directly coupled with the given one
        pass
    
    @abstractmethod
    def get_direct_coupling(self, a, b):
        pass"""
    
    def get_coupling_candidates(self, node, add_predecessors = False):
        """Return all the nodes with which the given one could have a non-zero relative coupling.
         * := The direct coupling nodes of given+descendants, and all their predecessors"""
        this_and_descendants = self.get_self_and_descendants(node)
        
        direct_coupling_candidates = []
        for n in this_and_descendants:
            for n2 in self.get_directly_coupled(n):
                direct_coupling_candidates.append(n2)
        
        result = set()
        result.add("")  # root node, added to stop the predecessor iteration
        for other in direct_coupling_candidates:
            while result.add(other): # while not present yet
                if not add_predecessors:
                    break
                other = self.get_parent(other)
        result.remove("")  # root node - removed, since not very interesting
        return result
    
    def get_self_and_descendants(self, node):
        """return the given node and all its descendants as a list"""
        result = []
        self.get_self_and_descendants_rec(node, result)
        return result
    
    def get_self_and_descendants_rec(self, node, result):
        """add the given node and all its descendants into the provided list"""
        result.append(node)
        for child in self.get_children(node):
            self.get_self_and_descendants_rec(child, result)
    
    def get_direct_multi_coupling(self, a, others):
        """sum of direct coupling between a and all b"""
        return sum(self.get_direct_coupling(a, b) for b in others)
    
    def get_relative_coupling(self, a, b):
        """sum of direct coupling between a+descendants and b+descendants"""
        others = self.get_self_and_descendants(b)
        return self.get_relative_multi_direct_coupling(a, others)
    
    def get_relative_multi_coupling(self, a, others):
        """sum of direct coupling between a+descendants and others+descendants"""
        direct_others = []
        for other in others:
            self.get_self_and_descendants_rec(other, direct_others)
        return self.get_relative_multi_direct_coupling(a, direct_others)
    
    def get_relative_multi_direct_coupling(self, a, others):
        """sum of direct coupling between a+descendants and others"""
        if len(others) == 0:
            return 0
        result = self.get_direct_multi_coupling(a, others)
        for child in self.get_children(a):
            result += self.get_relative_multi_direct_coupling(child, others)
        return result
    
    def get_total_relative_coupling(self, a):
        """the sum of direct couplings that a has, cached"""
        if a in self.total_relative_coupling_cache:
            return self.total_relative_coupling_cache[a]
        
        a_candidates = self.get_coupling_candidates(a, add_predecessors = False)
        total_coupling = self.get_relative_multi_direct_coupling(a, a_candidates)
        self.total_relative_coupling_cache[a] = total_coupling
        return total_coupling
    
    def get_normalized_coupling(self, a, b):
        """relative coupling between a and b, normalized by the sum of couplings that a has, in range [0, 1]"""
        if a not in self.g or b not in self.g:
            return 0
        target_coupling = self.get_relative_coupling(a, b)
        if target_coupling == 0:
            return 0
        total_coupling = self.get_total_relative_coupling(a)
        return target_coupling / total_coupling


class ExplicitCouplingGraph(NormalizeCouplingWithChildren, NormalizeSupportWithChildren, NodeSetCouplingGraph):
    def __init__(self, name):
        NodeSetCouplingGraph.__init__(self, name)
        NormalizeCouplingWithChildren.__init__(self)
        NormalizeSupportWithChildren.__init__(self)
        self.g = nx.Graph()
        
    def get_node_set(self):
        return set(self.g.nodes)
        
    def add(self, a, b, delta):
        if a == b:
            return
        new_value = self.get(a, b) + delta
        self.g.add_edge(a, b, weight=new_value)
        
    def get(self, a, b):
        if a in self.g and b in self.g.adj[a]:
            return self.g.adj[a][b]["weight"]
        return 0
    
    def get_direct_coupling(self, a, b):
        return self.get(a, b)
    
    def get_directly_coupled(self, node):
        if node in self.g:
            return [n for n in self.g[node]]
        else:
            return []
    
    def add_support(self, node, delta):
        if not node in self.g.nodes:
            self.g.add_node(node)
        self.g.nodes[node]["support"] = self.get_support(node) + delta
        
    def get_support(self, node):
        return self.g.nodes.get(node, {}).get("support", 0)
        
    def get_absolute_self_support(self, node):
        return self.get_support(node)
    
    def add_and_support(self, a, b, delta):
        self.add(a, b, delta)
        self.add_support(a, delta)
        self.add_support(b, delta)
    
    def cutoff_edges(self, minimum_weight):
        fedges = [(a, b) for a, b, info in self.g.edges.data() if info["weight"] < minimum_weight]
        self.g.remove_edges_from(fedges)
        
    def cleanup(self, min_component_size):  # min_component_size = 5
        # self.g.remove_nodes_from(list(nx.isolates(self.g)))
        for component in list(nx.connected_components(self.g)):
            if len(component) < min_component_size:
                for node in component:
                    self.g.remove_node(node)
    
    def propagate_down(self, layers = 1, weight_factor = 0.2):
        """copy the connections of each node (scaled by weight_factor) to its children"""
        children_dict = self._get_children_dict()
        child_having_nodes = list(children_dict.keys())
        child_having_nodes.sort(key=lambda path: -path.count('/'))
        for iteration in range(layers):
            changes_to_apply = []
            for node in log_progress(child_having_nodes, desc="Propagating down coupling information, iteration " + str(iteration + 1) + "/" + str(layers)):
                connections_and_weights = [(conn, self.get(node, conn) * weight_factor) for conn in self.g[node] if not conn.startswith(node + "/")]
                for child in children_dict[node]:
                    for conn, val in connections_and_weights:
                        for conn_child in children_dict.get(conn, []):
                            changes_to_apply.append((child, conn_child, val))
            for a, b, delta in log_progress(changes_to_apply, desc="Applying changes, iteration " + str(iteration + 1) + "/" + str(layers)):
                self.add(a, b, delta)
                
    def dilate(self, iterations = 1, weight_factor = 0.2):
        all_nodes = list(self.g.nodes)
        for iteration in range(iterations):
            changes_to_apply = []
            for node in log_progress(all_nodes, desc="Dilating coupling information, iteration " + str(iteration + 1) + "/" + str(iterations)):
                connections_and_weights = [(conn, self.get(node, conn) * weight_factor) for conn in self.g[node] if not conn.startswith(node + "/") and not node.startswith(conn + "/")]
                for (c1, w1), (c2, w2) in all_pairs(connections_and_weights):
                    changes_to_apply.append((c1, c2, min(w1, w2)))
            for a, b, delta in log_progress(changes_to_apply, desc="Applying changes, iteration " + str(iteration + 1) + "/" + str(iterations)):
                self.add(a, b, delta)
    
    def _get_children_dict(self):
        result = {}
        all_nodes = list(self.g.nodes)
        for node in all_nodes:
            result[node] = set()
        for node in all_nodes:
            if "/" in node:
                parent = "/".join(node.split("/")[0:-1])
                if parent in result:
                    result[parent].add(node)
        for node in all_nodes:
            if len(result[node]) == 0:
                del result[node]
        return result
        
    def get_max_weight(self):
        return max([self.g[e[0]][e[1]]["weight"] for e in self.g.edges])
    
    def plaintext_content(self):
        node_list = list(self.g.nodes)
        node2index = dict(zip(node_list, range(len(node_list))))
        return ";".join(node_list) + "\n" + ";".join([str(node2index[a]) + "," + str(node2index[b]) + "," + str(d["weight"]) for a, b, d in self.g.edges(data=True)])
        
    def print_statistics(self):
        # https://networkx.github.io/documentation/latest/tutorial.html#analyzing-graphs
        node_count = len(self.g.nodes)
        edge_count = len(self.g.edges)
        cc = sorted(list(nx.connected_components(self.g)), key= lambda e: -len(e))
        print("ExplicitCouplingGraph statistics: "
              + str(node_count) + " nodes, "
              + str(edge_count) + " edges, "
              + str(len(cc)) + " connected component(s), with sizes: ["
              + ", ".join([str(len(c)) for c in cc[0:20]])
              + "]")
        edge_weights = [self.g[e[0]][e[1]]["weight"] for e in self.g.edges]
        edge_weights.sort()
        node_supports = [self.get_support(n) for n in self.g.nodes]
        node_supports.sort()
        print("Edge weights:", edge_weights[0:5], "...", edge_weights[-5:], ", mean:", np.array(edge_weights).mean())
        print("Node support values:", node_supports[0:5], "...", node_supports[-5:], ", mean:", np.array(node_supports).mean())
        
    def show_weight_histogram(self):
        edge_weights = [self.g[e[0]][e[1]]["weight"] for e in self.g.edges]
        show_histogram(edge_weights, 'Histogram of edge weights in coupling graph', 'Coupling Strength', 'Amount', 'b')
        
        node_weights = [sum([self.g[n][n2]["weight"] for n2 in self.g.adj[n]]) for n in self.g.nodes]
        show_histogram(node_weights, 'Histogram of node weights', 'Coupling Strength', 'Amount', 'g')
        
        node_supports = [self.get_support(n) for n in self.g.nodes]
        show_histogram(node_supports, 'Histogram of node support values', 'Support', 'Amount', 'g')
        
    def visualize(self, use_spring = False, with_labels = True):
        # https://networkx.github.io/documentation/latest/reference/generated/networkx.drawing.nx_pylab.draw_networkx.html
        for e in self.g.edges:
            self.g[e[0]][e[1]]["distance"] = 1.000001 - self.g[e[0]][e[1]]["weight"]  # the value must not be exactly zero
        
        edge_weights = [self.g[e[0]][e[1]]["weight"] for e in self.g.edges]
        max_weight = max(edge_weights)
        mean_weight = np.array(edge_weights).mean()
        target_max_weight = min(max_weight, mean_weight * 2)
        
        plt.figure(figsize=(8, 8))
        VIZ_POW = 10
        max_w_fact = (1. / target_max_weight) ** VIZ_POW
        
        layout = nx.drawing.layout.kamada_kawai_layout(self.g, weight="distance") if use_spring else None
        
        # nx.draw_kamada_kawai(self.g, alpha=0.2, node_size=100)
        # nx.draw(self.g, alpha=0.2, node_size=100)
        edge_colors = [(0., 0., 0., min(1., (self.g[a][b]["weight"] ** VIZ_POW) * max_w_fact)) for a, b in self.g.edges]
        nx.draw(self.g, pos=layout, node_size=50, edge_color=edge_colors, node_color=[(0.121, 0.469, 0.703, 0.2)], with_labels=with_labels)
        
        plt.show()
        
    def print_most_linked_nodes(self, amount = 10):
        print("Most linked nodes:")
        debug_list = sorted(list(self.g.edges.data()), key = lambda e: -e[2]["weight"])
        for a, b, info in debug_list[0:amount]:
            print(str(info["weight"]) + ": " + a + " <> " + b)


DOCUMENT_SIMILARITY_EXP = 8 # higher = lower equality values, lower = equality values are all closer to 1
class SimilarityCouplingGraph(NormalizeSupport, NodeSetCouplingGraph):
    """assigns d-dimensional coordinates to nodes, coupling is defined by their closeness."""
    def __init__(self, name):
        NodeSetCouplingGraph.__init__(self, name)
        NormalizeSupport.__init__(self)
        self.support = {}
        self.coords = {}
        
    def get_node_set(self):
        return set(self.coords.keys())
        
    def add_node(self, node, coordinates, support):
        self.coords[node] = coordinates
        self.support[node] = support
        
    def get_support(self, node):
        return self.support.get(node, 0)
    
    def get_absolute_support(self, node):
        return self.get_support(node)
    
    def get_normalized_coupling(self, a, b):
        def array_similarity(a, b):
            """given two arrays of numbers, how equal are they?"""
            dist = distance.jensenshannon(a, b, 2)  # TODO check for alternative distance metrics?
            if np.isnan(dist):
                pdb.set_trace()
                return 0
            return math.pow(1. - dist, DOCUMENT_SIMILARITY_EXP)
        coords_a = self.coords.get(a)
        coords_b = self.coords.get(b)
        if coords_a is None or coords_b is None:
            return 0
        return array_similarity(coords_a, coords_b)
    
    def plaintext_content(self):
        return "\n".join(
            ",".join([node, str(self.support[node])] + [str(c) for c in self.coords[node]])
            for node in self.get_node_set()
        )
    
    def print_statistics(self):
        node_count = len(self.coords)
        if node_count == 0:
            print("Empty SimilarityCouplingGraph!")
            return
        min_coord = next(iter(self.coords.values()))
        max_coord = list(min_coord)
        for val in self.coords.values():
            for d in range(len(min_coord)):
                min_coord[d] = min(min_coord[d], val[d])
                max_coord[d] = max(max_coord[d], val[d])
        print("SimilarityCouplingGraph statistics: " + str(node_count) + " nodes")
        print("Min coordinates: " + str(min_coord))
        print("Max coordinates: " + str(max_coord))
        node_supports = [self.get_support(n) for n in self.get_node_set()]
        node_supports.sort()
        print("Node support values:", node_supports[0:5], "...", node_supports[-5:], ", mean:", np.array(node_supports).mean())


class ModuleDistanceCouplingGraph(CouplingGraph):
    def __init__(self):
        CouplingGraph.__init__(self, "module_distance")
        
    def get_normalized_support(self, node):
        return 1
    
    def get_normalized_coupling(self, a, b):
        dist = path_module_distance(a, b)
        base = 1.1  # needs to be bigger than one. Lower values = stronger coupling across bigger distances. Higher values = faster decay of coupling across module distance
        return math.pow(base, -dist)
    
    def plaintext_content(self):
        return ""
    
    def print_statistics(self):
        return "Module Distance"


if False:  # Local debugging code
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