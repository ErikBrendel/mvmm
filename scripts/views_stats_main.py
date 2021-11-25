from typing import cast

import pyfiglet
from cachier import cachier
import matplotlib.pyplot as plt
import numpy as np

from repos import all_old_repos
from metrics import MetricManager
from local_repo import LocalRepo
from graph import ExplicitCouplingGraph, SimilarityCouplingGraph
from util import show_histogram


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


for view in ["evolutionary", "references"]:
    print(pyfiglet.figlet_format(view))
    cc_sizes = []
    relative_node_counts = []
    edge_densities = []

    for repo in all_old_repos:
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
    plt.show()
    relative_node_counts.sort()
    edge_densities.sort()
    print(f"{view=}, {relative_node_counts=}")
    print(f"{view=}, {edge_densities=}")

print(pyfiglet.figlet_format("linguistic"))
for repo in all_old_repos:
    r = LocalRepo.for_name(repo)
    sim_graph = cast(SimilarityCouplingGraph, MetricManager.get(r, "linguistic"))
    # sim_graph.similarity_get_node("")
    # graph.print_statistics()
