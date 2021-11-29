import random
from typing import cast

import pyfiglet
from cachier import cachier
import matplotlib.pyplot as plt
import numpy as np

from repos import all_new_repos
from metrics import MetricManager
from local_repo import LocalRepo
from graph import ExplicitCouplingGraph, SimilarityCouplingGraph
from util import show_histogram, show_multi_histogram


"""

ref / evo:
connected components? (always one with nearly all, often many very small ones)
relative node count (98% of all relevant files?)
edge density relative (70% of all possible edges are non-zero?)
node degree histogram
edge weights histogram

ling:
relative node count (98% of all relevant files?)
edge weights histogram
average topic distributions of root node (= of whole project)
example topics output

"""



@cachier()
def stats_cc_sizes(r, view):
    return MetricManager.get(r, view).get_connected_component_sizes()[::-1]


@cachier()
def stats_relative_n_m(r, view):
    all_nodes = set(node.get_path() for node in LocalRepo.for_name(repo).get_tree().traverse_gen())
    max_n = len(all_nodes)
    max_m = (max_n * (max_n - 1)) / 2
    node_names, _supports, edges = MetricManager.get(r, view).get_data()
    n = len(set(node_names).intersection(all_nodes))
    m = len([e for e in edges if e[2] != 0])
    return n / max_n, m / max_m


@cachier()
def stats_node_degrees_edge_weights(r, view):
    node_names, _supports, edges = MetricManager.get(r, view).get_data()
    node_degrees = [0 for _n in node_names]
    for n0, n1, w in edges:
        node_degrees[n0] += w
        node_degrees[n1] += w
    edge_weights = [e[2] for e in edges]
    random.shuffle(node_degrees)
    random.shuffle(edge_weights)
    return node_degrees[:10000], edge_weights[:10000]


for view in ["evolutionary", "references"]:
    print(pyfiglet.figlet_format(view))
    cc_sizes = []
    relative_node_counts = []
    edge_densities = []
    all_node_degrees = []
    all_edge_weights = []

    for repo in all_new_repos:
        r = LocalRepo.for_name(repo)
        cc = stats_cc_sizes(r, view)
        total_size = sum(cc)
        for i, cc_size in enumerate(cc):
            if i >= 4:
                break
            if len(cc_sizes) <= i:
                cc_sizes.append([])
            cc_sizes[i].append(cc_size / total_size)

        rel_n, rel_m = stats_relative_n_m(r, view)
        relative_node_counts.append(rel_n)
        edge_densities.append(rel_m)
        node_deg, edge_w = stats_node_degrees_edge_weights(r, view)
        all_node_degrees.append(node_deg)
        all_edge_weights.append(edge_w)
    # then show the aggregated results
    for sizes in cc_sizes:
        while len(sizes) < len(cc_sizes[0]):
            sizes.append(0)
    X = list(range(len(cc_sizes)))
    Y = [np.mean(sizes) for sizes in cc_sizes]
    err = [np.std(sizes) for sizes in cc_sizes]
    plt.bar(X, Y, yerr=err)
    plt.title(f"Sizes of the connected components in the {view} graphs")
    # plt.xscale("log")
    # plt.yscale("log")
    plt.ylim((-0.02, 1.1))
    plt.show()
    relative_node_counts.sort()
    edge_densities.sort()
    print(f"{view=}, {np.median(relative_node_counts)=}, {relative_node_counts=}")
    print(f"{view=}, {np.median(edge_densities)=}, {edge_densities=}")
    show_multi_histogram(all_node_degrees, f"{view} diagram of node degrees")
    show_multi_histogram(all_edge_weights, f"{view} diagram of edge weights")


print(pyfiglet.figlet_format("linguistic"))
for repo in all_new_repos:
    r = LocalRepo.for_name(repo)
    sim_graph = cast(SimilarityCouplingGraph, MetricManager.get(r, "linguistic"))
    # sim_graph.similarity_get_node("")
    # graph.print_statistics()
