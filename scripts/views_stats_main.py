import math
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
def stats_ling_relative_n(r):
    all_nodes = set(node.get_path() for node in LocalRepo.for_name(repo).get_tree().traverse_gen())
    max_n = len(all_nodes)
    node_names = MetricManager.get(r, "linguistic").get_node_set()
    n = len(set(node_names).intersection(all_nodes))
    return n / max_n


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
    return node_degrees[:100000], edge_weights[:100000]


def stats_sampled_edge_weights(r, view, nodes=None):
    g = MetricManager.get(r, view)
    if nodes is None:
        nodes = list(g.get_node_set())
    edge_weights = []
    n = len(nodes)
    sample_size = min(n, math.ceil(100000 / n))
    for n1 in nodes:
        samples = random.sample(nodes, sample_size)
        for n2 in samples:
            edge_weights.append(g.get_normalized_coupling(n1, n2))
    return edge_weights


@cachier()
def stats_ling_edge_weights(r):
    return stats_sampled_edge_weights(r, "linguistic")


@cachier()
def stats_project_structure_edge_weights(r: LocalRepo):
    return stats_sampled_edge_weights(r, "module_distance", list(node.get_path() for node in r.get_tree().traverse_gen()))


for view in ["references", "evolutionary"]:
    print(pyfiglet.figlet_format(view))
    cc_sizes = []
    relative_node_counts = []
    edge_densities = []
    all_node_degrees = []
    all_edge_weights = []
    cc_amounts = []

    for repo in all_new_repos:
        r = LocalRepo.for_name(repo)
        cc = stats_cc_sizes(r, view)
        print(f"{cc=}")
        total_size = sum(cc)
        cc_amounts.append(len(cc))
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
    # X = [str(x) for x in range(len(cc_sizes))]
    # Y = [np.mean(sizes) for sizes in cc_sizes]
    # err = [np.std(sizes) for sizes in cc_sizes]
    # plt.bar(X, Y, yerr=err)
    # plt.xlabel("Connected Component")
    # plt.ylabel("Relative Size")
    # # plt.title(f"Sizes of the connected components in the {view} graphs")
    # # plt.xscale("log")
    # # plt.yscale("log")
    # plt.ylim((-0.02, 1.1))
    # # plt.axes().xaxis.set_major_locator(MaxNLocator(integer=True))
    # plt.show()
    relative_node_counts.sort()
    edge_densities.sort()
    print(f"{cc_amounts=}")
    print("cc-sizes:", cc_sizes)
    print(f"{view=}, {np.median(relative_node_counts)=}, {relative_node_counts=}")
    print(f"{view=}, {np.median(edge_densities)=}, {edge_densities=}")
    show_multi_histogram(all_node_degrees, "", xlabel="Weighted Node Degree", ylog=True)
    show_multi_histogram(all_edge_weights, "", xlabel="Edge Weight", ylog=True)


import sys
sys.exit(0)

print(pyfiglet.figlet_format("linguistic"))
all_edge_weights = []
relative_node_counts = []
topic_probs = [[] for _i in range(10)]
supports = []
for repo in all_new_repos:
    r = LocalRepo.for_name(repo)
    all_edge_weights.append(stats_ling_edge_weights(r))
    rel_n = stats_ling_relative_n(r)
    relative_node_counts.append(rel_n)
    sim_graph = cast(SimilarityCouplingGraph, MetricManager.get(r, "linguistic"))
    top_support, top_weights = sim_graph.similarity_get_node("")
    for i, weight in enumerate(sorted(top_weights, reverse=True)):
        topic_probs[i].append(weight)
    supports.append(top_support)
    # graph.print_statistics()
plt.hlines(0.1, 0, 11, linestyles='dashed', colors='k')
X = [i + 1 for i in range(len(topic_probs))]
Y = [np.mean(sizes) for sizes in topic_probs]
err = [np.std(sizes) for sizes in topic_probs]
plt.bar(X, Y, yerr=err)
# plt.title(f"Sizes of the topics in the linguistic graphs")
plt.xlim((0.001, 10.9999))
plt.ylim((-0.02, 0.3))
plt.show()
relative_node_counts.sort()
print(f"view=linguistic, {np.median(relative_node_counts)=}, {relative_node_counts=}")
show_multi_histogram(all_edge_weights, "", xlabel="Coupling Strength", ylabel="Amount within a sample of 100,000 edges", ylog=True)  # "linguistic diagram of edge weights")
supports.sort()
print(f"view=linguistic, {np.median(supports)=}, {supports=}")


print(pyfiglet.figlet_format("project_structure"))
all_edge_weights = []
for repo in all_new_repos:
    r = LocalRepo.for_name(repo)
    all_edge_weights.append(stats_project_structure_edge_weights(r))
show_multi_histogram(all_edge_weights, "", xlabel="Coupling Strength", ylabel="Amount within a sample of 100,000 edges", ylog=True)  # "linguistic diagram of edge weights")

