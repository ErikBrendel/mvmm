import math
import random
import time
from typing import *

import matplotlib.pyplot as plt
import pyfiglet

from legacy_graph import LegacyCouplingGraph, get_graph_node_set_combination
from local_repo import LocalRepo
from metrics import MetricManager
from util import log_progress, all_pairs, score_sorting_similarity

from cachier import cachier

import os
cwd = os.getcwd()
print(cwd)

repos = [
    # "ErikBrendel/LudumDare",
    # "ErikBrendel/LD35",
    # "eclipse/eclipse.jdt.core",
    # "jenkinsci/jenkins",
    # "jOOQ/jOOQ",
    # "wumpz/jhotdraw",
    # "neuland/jade4j",
    # "apache/log4j",
    # "junit-team/junit4",
    "jfree/jfreechart",
    "jfree/jfreechart:v1.5.3",
    "jfree/jfreechart:v1.5.0",
    "jfree/jfreechart:v1.0.19",
    # "vanzin/jEdit",
    # "hunterhacker/jdom",
    # "SonarSource/sonarqube",
    # "brettwooldridge/HikariCP",
    # "adamfisk/LittleProxy",
    # "dynjs/dynjs",
]
metrics = ["references", "evolutionary", "linguistic", "module_distance"]

# repos.sort(key=lambda repo: len(LocalRepo(repo).get_all_interesting_files()))


fig, axes = plt.subplots(len(repos), 1, figsize=(3, len(repos) * 2.5), constrained_layout=True)
fig.suptitle('Correlations between views', fontsize=15)

repo_obj_cache: dict[str, LocalRepo] = dict()
repo_metric_cache: dict[str, LegacyCouplingGraph] = dict()
repo_metric_values_cache: dict[str, List[List[float]]] = dict()


def get_view(repo: str, view: str) -> LegacyCouplingGraph:
    key = repo + "-" + view
    if key not in repo_metric_cache:
        if repo not in repo_obj_cache:
            repo_obj_cache[repo] = LocalRepo(repo)
            repo_obj_cache[repo].update()
        repo_metric_cache[key] = MetricManager.get(repo_obj_cache[repo], view)
    return repo_metric_cache[key]


def get_metric_values(repo: str, max_node_pairs_to_check=100000) -> List[List[float]]:
    if repo not in repo_metric_values_cache:
        graphs = [get_view(repo, view) for view in metrics]
        nodes = sorted([tree_node.get_path() for tree_node in repo_obj_cache[repo].get_tree().traverse_gen() if tree_node.get_type() == "method" and tree_node.get_line_span() >= 1])
        node_pairs = list(all_pairs(nodes))
        random.seed(42)  # for reproducibility
        if len(node_pairs) > max_node_pairs_to_check:
            print("Sampling down node pairs from " + str(len(node_pairs)) + " to " + str(max_node_pairs_to_check))
            node_pairs = random.sample(node_pairs, max_node_pairs_to_check)
        else:
            print("Node pair amount " + str(len(node_pairs)) + " does not exceed " + str(max_node_pairs_to_check) + ", all are used")
            random.shuffle(node_pairs)
        repo_metric_values_cache[repo] = [[g.get_normalized_coupling(a, b) for g in graphs] for a, b in log_progress(node_pairs, desc="getting coupling values")]
    return repo_metric_values_cache[repo]


@cachier()
def check_view_alignment_method_nodes(repo: str, metric: str, other_metric: str) -> float:
    metric_values = get_metric_values(repo)
    mi1 = metrics.index(metric)
    mi2 = metrics.index(other_metric)

    target_data_list: List[tuple[float, float]] = [(entry[mi2], entry[mi1]) for entry in metric_values]
    return score_sorting_similarity(target_data_list)
# check_predictability_params_fast.clear_cache()
print("Cached values at: " + check_view_alignment_method_nodes.cache_dpath())

for ri, repo in enumerate(repos):
    print(pyfiglet.figlet_format(repo))
    sm = plt.cm.ScalarMappable(cmap=None, norm=plt.Normalize(vmin=0.5, vmax=1))

    columns = tuple(" " + m[0].upper() + " " for m in metrics)
    # Add a table at the bottom of the axes
    colors = [[sm.to_rgba(check_view_alignment_method_nodes(repo, m1, m2)) for m2 in metrics] for m1 in metrics]
    # cellText = [[str(int(check_view_alignment(repo, m1, m2) * 100)) + "%" for m2 in metrics] for m1 in metrics]

    axes[ri].set_aspect('equal')
    axes[ri].set_title(repo)
    axes[ri].axis('tight')
    axes[ri].axis('off')
    axes[ri].table(cellColours=colors, colLabels=columns, rowLabels=columns, loc='center', cellLoc="center").scale(0.7, 1.5)

    plt.colorbar(sm, ax=axes[ri])

print("Cached values at: " + check_view_alignment_method_nodes.cache_dpath())
plt.show()
