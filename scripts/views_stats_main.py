from typing import *
import math
import random
from collections import defaultdict
from typing import cast

import pyfiglet
from cachier import cachier
import matplotlib.pyplot as plt
import numpy as np

from repos import all_new_repos
from metrics import MetricManager
from local_repo import LocalRepo
from graph import ExplicitCouplingGraph, SimilarityCouplingGraph
from analysis import ALL_VIEWS
from workarounds import metric_display_rename
from util import show_histogram, show_multi_histogram, plt_save_show, all_pairs, log_progress

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


@cachier()
def stats_node_degrees_edge_weights_generic(r: LocalRepo, view: str) -> Tuple[List[float], List[float]]:
    g = MetricManager.get(r, view)
    all_nodes = set(node.get_path() for node in LocalRepo.for_name(repo).get_tree().traverse_gen())
    print(r.name + " (" + view + "): " + str(len(all_nodes)))
    random.seed(42)
    all_nodes = random.sample(list(all_nodes), 2000)
    node_degrees_dict = defaultdict(lambda: 0.0)
    edge_weights = []
    for n1, n2 in log_progress(list(all_pairs(all_nodes)), desc="Sampling edge data "):
        w = g.get_normalized_coupling(n1, n2)
        node_degrees_dict[n1] += w
        node_degrees_dict[n2] += w
        edge_weights.append(w)
    return list(node_degrees_dict.values()), edge_weights



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


def view_name_to_short(view: str) -> str:
    if view == "linguistic":
        return "ling"
    if view in ["references", "evolutionary"]:
        return view[:3]
    return metric_display_rename(view)


# for repo in all_new_repos:
#     LocalRepo.for_name(repo).get_tree()
plt.rcParams['figure.dpi'] = 250
plt.rcParams['axes.axisbelow'] = True

for view in ALL_VIEWS:
    print(pyfiglet.figlet_format(view))
    all_node_degrees = []
    all_edge_weights = []
    for repo in all_new_repos:
        r = LocalRepo.for_name(repo)
        node_deg, edge_w = stats_node_degrees_edge_weights_generic(r, view)
        all_node_degrees.append(node_deg)
        all_edge_weights.append(edge_w)
    show_multi_histogram(all_node_degrees, f"Weighted Node Degrees in the {view} graphs", xlabel="Weighted Node Degree", ylog=True, show=False)
    plt_save_show(f"stats_{view_name_to_short(view)}_node_degrees", zoom_factor=1.5)
    show_multi_histogram(all_edge_weights, f"Edge Weights in the {view} graphs", xlabel="Edge Weight", ylog=True, show=False)
    plt_save_show(f"stats_{view_name_to_short(view)}_edge_weights", zoom_factor=1.5)

    zero_edge_counts = [(np.array(edge_w) == 0.0).sum() / len(edge_w) for edge_w in all_edge_weights]
    nonzero_edge_counts = [1.0 - z for z in zero_edge_counts]
    one_edge_counts = [(np.array(edge_w) == 1.0).sum() / len(edge_w) for edge_w in all_edge_weights]
    nontrivial_edge_counts = [1.0 - z - o for z, o in zip(zero_edge_counts, one_edge_counts)]
    print(f"{view=}, {np.median(zero_edge_counts)=}, {sorted(zero_edge_counts)=}")
    print(f"{view=}, {np.median(nonzero_edge_counts)=}, {sorted(nonzero_edge_counts)=}")
    print(f"{view=}, {np.median(one_edge_counts)=}, {sorted(one_edge_counts)=}")
    print(f"{view=}, {np.median(nontrivial_edge_counts)=}, {sorted(nontrivial_edge_counts)=}")
    print()
    zero_node_degrees = [(np.array(node_deg) == 0.0).sum() / len(node_deg) for node_deg in all_node_degrees]
    nonzero_node_weights = [1.0 - z for z in zero_node_degrees]
    print(f"{view=}, {np.median(zero_node_degrees)=}, {sorted(zero_node_degrees)=}")
    print(f"{view=}, {np.median(nonzero_node_weights)=}, {sorted(nonzero_node_weights)=}")


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
    X = [str(x) for x in range(len(cc_sizes))]
    for Y in zip(*cc_sizes):
        plt.bar(X, Y, alpha=1.25 ** -len(all_new_repos), facecolor="g")
    err = [np.std(sizes) for sizes in cc_sizes]
    # plt.bar(X, [np.mean(sizes) for sizes in cc_sizes], yerr=err, alpha=0, facecolor="r")
    plt.xlabel("Connected Component")
    plt.ylabel("Relative Size")
    # plt.title(f"Connected Component Sizes in the {view} graphs")
    # plt.xscale("log")
    # plt.yscale("log")
    plt.ylim((-0.02, 1.1))
    plt.grid(visible=True, axis="y")
    # plt.axes().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt_save_show(f"stats_{view_name_to_short(view)}_cc", zoom_factor=1.5)
    relative_node_counts.sort()
    edge_densities.sort()
    print(f"{cc_amounts=}")
    print("cc-sizes:", cc_sizes)
    print(f"{view=}, {np.median(relative_node_counts)=}, {relative_node_counts=}")
    print(f"{view=}, {np.median(edge_densities)=}, {edge_densities=}")
    # show_multi_histogram(all_node_degrees, f"Weighted Node Degrees in the {view} graphs", xlabel="Weighted Node Degree", ylog=True, show=False)
    # plt_save_show(f"stats_{view_name_to_short(view)}_node_degrees", zoom_factor=1.5)
    # show_multi_histogram(all_edge_weights, f"Edge Weights in the {view} graphs", xlabel="Edge Weight", ylog=True, show=False)
    # plt_save_show(f"stats_{view_name_to_short(view)}_edge_weights", zoom_factor=1.5)


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
X = [str(i + 1) for i in range(len(topic_probs))]
for Y in zip(*topic_probs):
    plt.bar(X, Y, alpha=1.25 ** -len(all_new_repos), facecolor="g")
err = [np.std(sizes) for sizes in topic_probs]
# plt.bar(X, [np.mean(sizes) for sizes in topic_probs], yerr=err, alpha=0, facecolor="r")
plt.hlines(0.1, -1, 10, linestyles='dashed', colors='k')
# plt.title(f"Sizes of the topics in the linguistic graphs")
plt.xlim((-0.999, 9.9999))
plt.ylim((-0.02, 0.3))
plt.grid(visible=True, axis="y")
plt_save_show(f"stats_ling_topic_sizes", zoom_factor=1.5)
relative_node_counts.sort()
print(f"view=linguistic, {np.median(relative_node_counts)=}, {relative_node_counts=}")
# show_multi_histogram(all_edge_weights, "Edge Weights in the linguistic graphs", xlabel="Coupling Strength", ylabel="Amount within a sample of 100,000 edges", ylog=True, show=False)
# plt_save_show(f"stats_ling_edge_weights", zoom_factor=1.5)
supports.sort()
print(f"view=linguistic, {np.median(supports)=}, {supports=}")


# print(pyfiglet.figlet_format("project_structure"))
# all_edge_weights = []
# for repo in all_new_repos:
#     r = LocalRepo.for_name(repo)
#     all_edge_weights.append(stats_project_structure_edge_weights(r))
# show_multi_histogram(all_edge_weights, "Edge Weights in the project structure graphs", xlabel="Coupling Strength", ylabel="Amount within a sample of 100,000 edges", ylog=True, show=False)
# plt_save_show(f"stats_project_structure_edge_weights", zoom_factor=1.5)
