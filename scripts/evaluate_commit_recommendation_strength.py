from __future__ import annotations

import ternary
from matplotlib import pyplot as plt
from cachier import cachier
from local_repo import LocalRepo
from metrics import MetricManager
from metrics_evolutionary import get_commit_diff
from graph import CombinedCouplingGraph, CachedCouplingGraph, CouplingGraph, graph_manager
from prcoessify import processify
from plotting import parallel_coordinates
# from graph import CachedCouplingGraph, CouplingGraph, CombinedCouplingGraph, graph_manager
from util import log_progress, generate_one_distributions
from typing import *

repos = [
    # "ErikBrendel/LudumDare:e77400a84a77c0cf8cf8aea128b78c5c9c8ad81e",  # earlier
    # "ErikBrendel/LudumDare:d2701514c871f5efa3ae5c9766c0a887c1f12252",  # later
    # "neuland/jade4j:v1.2.5",  # current is 1.3.2
    # "neuland/jade4j:v1.1.4",
    # "neuland/jade4j:v1.0.0",
    # "apache/log4j:v1_2_15",  # current is 1.2.17
    # "apache/log4j:v1_2_11",
    # "apache/log4j:v1_2_6",
    # "apache/log4j:v1_2_1",
    # "apache/log4j:v1_1_1",
    # "brettwooldridge/HikariCP:HikariCP-3.1.0",  # current: 4.0.3
    # "jenkinsci/jenkins:jenkins-2.289",  # current: 2.296
    # "jenkinsci/jenkins:jenkins-2.277",  # current: 2.296
    # "jenkinsci/jenkins:jenkins-2.263",  # current: 2.296
    # "jenkinsci/jenkins:jenkins-2.250",  # current: 2.296
    # "jfree/jfreechart:5ca5d26bb38bafead25f81e88e0938a5d042c2a4",  # May 15
    "jfree/jfreechart:9020a32e62800916f1897c3eb17c95bf0371230b",  # Mar 7
    # "jfree/jfreechart:99d999395e46f8cf8689724853c9ede89be7c7ea",  # Mar 1
    # "jfree/jfreechart:fc4ddeed916c4cfd6479bf7378c6cdb94f6a19fe",  # Feb 6
    # "jfree/jfreechart:461625fd1f7242a1223f8e73716e9f2b4e9fd8a5",  # Dez 19, 2020
]

metrics = ["references", "evolutionary", "linguistic", "module_distance"]


@processify
def get_commit_diff_processified(*args) -> Optional[Set[str]]:
    return get_commit_diff(*args)


def node_filter(tree_node):
    return tree_node is not None and tree_node.get_type() == "method" and tree_node.get_line_span() >= 1


nodes_tests_cache: dict[str, Tuple[int, List[tuple[str, List[str]]]]] = {}
graph_cache: dict[str, List[CouplingGraph]] = {}
def get_nodes_and_tests(repo: str):
    if repo not in nodes_tests_cache:
        r = LocalRepo.for_name(repo)
        all_nodes = sorted([tree_node.get_path() for tree_node in r.get_tree().traverse_gen() if node_filter(tree_node)])
        prediction_tests: List[tuple[str, List[str]]] = []
        future_commit_diffs = [get_commit_diff_processified(ch, r) for ch in r.get_future_commits()]
        future_commit_diffs = [[path for path in diff if node_filter(r.get_tree().find_node(path))] for diff in future_commit_diffs if diff is not None]
        commits_to_evaluate = [diffs for diffs in future_commit_diffs if len(diffs) > 1]
        for commit_to_evaluate in commits_to_evaluate:
            for i, method_to_predict in enumerate(commit_to_evaluate):
                other_methods: List[str] = commit_to_evaluate[:i] + commit_to_evaluate[i + 1:]
                prediction_tests.append((method_to_predict, other_methods))
        # nodeset_id = graph_manager.create_node_set(all_nodes)
        # nodes_tests_cache[repo] = (nodeset_id, prediction_tests)
        all_nodes_ns = graph_manager.create_node_set(all_nodes)
        nodes_tests_cache[repo] = (all_nodes_ns, prediction_tests)
        print("Total method nodes: " + str(len(all_nodes)))
        print("Total future tests: " + str(len(prediction_tests)))
    return nodes_tests_cache[repo]
def get_graphs(repo: str):
    if repo not in graph_cache:
        graph_cache[repo] = [CachedCouplingGraph(MetricManager.get(LocalRepo.for_name(repo), m)) for m in metrics]
    return graph_cache[repo]


@cachier()
def get_commit_prediction_score_cpp(repo: str, weights: Tuple[float]):
    all_nodes, prediction_tests = get_nodes_and_tests(repo)
    scores = []
    combined_graph = CombinedCouplingGraph(get_graphs(repo), weights)
    for missing, others in prediction_tests:
        scores.append(combined_graph.how_well_predicts_missing_node(others, missing, all_nodes))
    return sum(scores) / len(scores)


for repo in repos:
    r = LocalRepo.for_name(repo)
    r.update()
    print(str(len(r.get_all_commits())) + " known commits, " + str(len(r.get_future_commits())) + " yet to come.")
    nodes, tests = get_nodes_and_tests(repo)
    print(len(nodes), "nodes")
    for a, bs in tests:
        print(a.split(".java/")[1], [b.split(".java/")[1] for b in bs])

    scale = 8
    results = []
    weight_combinations = list(generate_one_distributions(len(metrics), scale))
    for weights in log_progress(weight_combinations, desc="Evaluating view weight combinations"):
        score = get_commit_prediction_score_cpp(repo, tuple(weights))
        score = score ** 1  # todo make this power slider interactive?
        results.append((", ".join(str(w) for w in weights), score))
    results.sort(key=lambda e: e[1])
    for res in results:
        print(res[0] + ", " + str(res[1]))

    fig, axes = plt.subplots(1, 4, figsize=(15, 3), constrained_layout=True)
    fig.suptitle(r.display_name() + " - How well can view combinations complete future commits?")
    for mi, omitted_metric in enumerate(metrics):
        other_metrics = tuple(metrics[:mi] + metrics[mi + 1:])

        def ternary_fn(tw):
            weights = tw[:]
            weights.insert(mi, 0)
            return get_commit_prediction_score_cpp(repo, tuple(weights)) ** 5

        tax = ternary.TernaryAxesSubplot(ax=axes[mi], scale=scale)
        tax.heatmapf(ternary_fn, boundary=True,
                     style="hex", colorbar=True,
                     vmin=0, vmax=1)
        fontsize = 9
        tax.right_corner_label(other_metrics[0], fontsize=fontsize, position=(0.9, 0.04, 0.1))
        tax.top_corner_label(other_metrics[1], fontsize=fontsize, offset=0.12)
        tax.left_corner_label(other_metrics[2], fontsize=fontsize, position=(0.08, 0.04, 0))

        # tax.set_title(r.display_name() + ": Without " + omitted_metric)
        tax.boundary(linewidth=1.0)

        # tax.show()
        axes[mi].axis("off")
        # noinspection PyProtectedMember
        tax._redraw_labels()
    plt.show()

    # parallel coordinates plot:
    """  # seem rather bad, research in that direction is halted for now
    parallel_data: List[Tuple[List[float], float]] = [
        (w, get_commit_prediction_score_cpp(repo, tuple(w)))
        for w in generate_one_distributions(len(metrics), scale)
    ]
    parallel_coordinates(None, metrics, parallel_data, 0.4 / scale)
    plt.show()
    """

