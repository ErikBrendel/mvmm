from __future__ import annotations

import ternary
from matplotlib import pyplot as plt
from cachier import cachier
from local_repo import LocalRepo
from metrics import MetricManager
from metrics_evolutionary import get_commit_diff
from graph import WeightCombinedGraph, ResultCachedGraph, CouplingGraph
from prcoessify import processify
from util import log_progress, generate_one_distributions
from typing import *

repos = [
    "ErikBrendel/LudumDare:e77400a84a77c0cf8cf8aea128b78c5c9c8ad81e",  # earlier
    # "ErikBrendel/LudumDare:d2701514c871f5efa3ae5c9766c0a887c1f12252",  # later
    # "neuland/jade4j:v1.2.5",  # current is 1.3.2
    # "neuland/jade4j:v1.1.4",
    # "neuland/jade4j:v1.0.0",
    # "apache/log4j:v1_2_15",  # current is 1.2.17
    # "apache/log4j:v1_2_11",
    # "apache/log4j:v1_2_6",
    # "apache/log4j:v1_2_1",
    # "apache/log4j:v1_1_1",
]

metrics = ["structural", "evolutionary", "linguistic", "module_distance"]


@processify
def get_commit_diff_processified(*args):
    return get_commit_diff(*args)


def node_filter(tree_node):
    return tree_node is not None and tree_node.get_type() == "method" and tree_node.get_line_span() >= 1


repo_objects = {repo: LocalRepo(repo) for repo in repos}
nodes_tests_cache: dict[str, Tuple[list[str], List[tuple[str, List[str]]]]] = {}
graph_cache: dict[str, List[CouplingGraph]] = {}
def get_nodes_and_tests(repo: str):
    if repo not in nodes_tests_cache:
        r = repo_objects[repo]
        all_nodes = sorted([tree_node.get_path() for tree_node in r.get_tree().traverse_gen() if node_filter(tree_node)])
        prediction_tests: List[tuple[str, List[str]]] = []
        future_commit_diffs = [get_commit_diff_processified(ch, r) for ch in r.get_future_commits()]
        future_commit_diffs = [[path for path in diff if node_filter(r.get_tree().find_node(path))] for diff in future_commit_diffs if diff is not None]
        commits_to_evaluate = [diffs for diffs in future_commit_diffs if len(diffs) > 1]
        for commit_to_evaluate in commits_to_evaluate:
            for i, method_to_predict in enumerate(commit_to_evaluate):
                other_methods: List[str] = commit_to_evaluate[:i] + commit_to_evaluate[i + 1:]
                prediction_tests.append((method_to_predict, other_methods))
        nodes_tests_cache[repo] = (all_nodes, prediction_tests)
    return nodes_tests_cache[repo]
def get_graphs(repo: str):
    if repo not in graph_cache:
        graph_cache[repo] = [ResultCachedGraph(MetricManager.get(repo_objects[repo], m)) for m in metrics]
    return graph_cache[repo]


@cachier()
def get_commit_prediction_score(repo: str, weights: Tuple[float]):
    all_nodes, prediction_tests = get_nodes_and_tests(repo)
    scores = []
    for missing, others in prediction_tests:
        scores.append(WeightCombinedGraph(get_graphs(repo), weights).how_well_predicts_missing_node(others, missing, all_nodes))
    return sum(scores) / len(scores)


for repo in repos:
    r = LocalRepo(repo)
    r.update()
    print(str(len(r.get_all_commits())) + " known commits, " + str(len(r.get_future_commits())) + " yet to come.")

    results = []
    weight_combinations = list(generate_one_distributions(len(metrics), 8))
    for weights in log_progress(weight_combinations, desc="Evaluating view weight combinations"):
        score = get_commit_prediction_score(repo, tuple(weights))
        score = score ** 10  # todo make this power slider interactive?
        results.append((", ".join(str(w) for w in weights), score))
    results.sort(key=lambda e: e[1])
    for res in results:
        print(res[0] + ", " + str(res[1]))

    fig, axes = plt.subplots(1, 4, figsize=(15, 3), constrained_layout=True)
    fig.suptitle(r.display_name() + " - How well can view combinations complete future commits?")
    scale = 8
    for mi, omitted_metric in enumerate(metrics):
        other_metrics = tuple(metrics[:mi] + metrics[mi + 1:])

        def ternary_fn(tw):
            weights = tw[:]
            weights.insert(mi, 0)
            return get_commit_prediction_score(repo, tuple(weights))

        tax = ternary.TernaryAxesSubplot(ax=axes[mi], scale=scale)
        tax.heatmapf(ternary_fn, boundary=True,
                     style="hex", colorbar=True,
                     vmin=0.5, vmax=1)
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

