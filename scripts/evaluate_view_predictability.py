import math
import random
import time
from typing import *

from analysis import ALL_VIEWS
from workarounds import *

import matplotlib.pyplot as plt
import pyfiglet
import ternary

from graph import CouplingGraph
from local_repo import LocalRepo
from metrics import MetricManager
from util import log_progress, all_pairs, score_sorting_similarity
from repos import all_new_repos
from cachier import cachier

import os
cwd = os.getcwd()
print(cwd)

plt.rcParams['figure.dpi'] = 150

repos = all_new_repos
metrics = ALL_VIEWS


fig, axes = plt.subplots(len(repos), 4, figsize=(15, len(repos) * 2.5), constrained_layout=True)
# fig.suptitle('How well can a combination of three views predict the fourth?', fontsize=15)

repo_metric_cache: dict[str, CouplingGraph] = dict()
repo_metric_values_cache: dict[str, List[List[float]]] = dict()


def get_view(repo: str, view: str) -> CouplingGraph:
    key = repo + "-" + view
    if key not in repo_metric_cache:
        repo_metric_cache[key] = MetricManager.get(LocalRepo.for_name(repo), view)
    return repo_metric_cache[key]


def get_metric_values(repo: str, max_node_pairs_to_check=100000) -> List[List[float]]:
    if repo not in repo_metric_values_cache:
        graphs = [get_view(repo, view) for view in metrics]
        nodes = sorted([tree_node.get_path() for tree_node in LocalRepo.for_name(repo).get_tree().traverse_gen() if tree_node.get_type() == "method" and tree_node.get_line_span() >= 1])
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
def check_predictability_params_fast_method_nodes(repo: str, metric: str, other_metrics: tuple[str], weights: tuple[float]) -> float:
    metric_values = get_metric_values(repo)
    mi = metrics.index(metric)
    other_indices = [metrics.index(other_metric) for other_metric in other_metrics]
    def other_combination(entry: List[float]) -> float:
        return sum(w * entry[oi] for oi, w in zip(other_indices, weights))

    target_data_list: List[tuple[float, float]] = [(other_combination(entry), entry[mi]) for entry in metric_values]
    return score_sorting_similarity(target_data_list)
# check_predictability_params_fast_method_nodes.clear_cache()
print("Cached values at: " + check_predictability_params_fast_method_nodes.cache_dpath())

for ri, repo in enumerate(repos):
    print(pyfiglet.figlet_format(repo))

    for mi, predicted_metric in enumerate(metrics):
        other_metrics = tuple(metrics[:mi] + metrics[mi + 1:])

        scale = 6
        total_sample_count = (scale + 1) * (scale + 2) / 2
        bar = log_progress("Calculating color values for plot", total=total_sample_count)

        def check_predictability(weights):
            global bar
            bar.update()
            return check_predictability_params_fast_method_nodes(repo, predicted_metric, other_metrics, tuple(weights))

        tax = ternary.TernaryAxesSubplot(ax=axes[ri, mi], scale=scale)
        tax.heatmapf(check_predictability, boundary=True,
                     style="hex", colorbar=True,
                     vmin=0.5, vmax=1)
        bar.close()
        # tax.gridlines(color="blue", multiple=scale / 4)

        fontsize = 9
        tax.right_corner_label(metric_display_rename(other_metrics[0]), fontsize=fontsize, position=(0.9, 0.04, 0.1))
        tax.top_corner_label(metric_display_rename(other_metrics[1]), fontsize=fontsize, offset=0.12)
        tax.left_corner_label(metric_display_rename(other_metrics[2]), fontsize=fontsize, position=(0.08, 0.04, 0))

        # tax.set_title(repo + ": Predicting " + predicted_metric)
        tax.boundary(linewidth=1.0)
        axes[ri, mi].axis('off')
        if mi == 0:
            axes[ri, mi].text(-0.4, 0.5, "\n".join(" / ".join(repo.split("/")).split(":")), horizontalalignment='center',
                              verticalalignment='center', transform=axes[ri, mi].transAxes,
                              rotation="vertical", fontsize=12)
        if ri == 0:
            axes[ri, mi].text(0.5, 1.1, "Predicting " + metric_display_rename(predicted_metric), horizontalalignment='center',
                              verticalalignment='center', transform=axes[ri, mi].transAxes,
                              fontsize=12)

        # tax.show()
        # noinspection PyProtectedMember
        tax._redraw_labels()
print("Cached values at: " + check_predictability_params_fast_method_nodes.cache_dpath())
plt.show()
