import math
import random
import time

import matplotlib.pyplot as plt
import pyfiglet
import ternary

from graph import WeightCombinedGraph, CouplingGraph, get_graph_node_set_combination
from local_repo import LocalRepo
from metrics import MetricManager
from util import log_progress, all_pairs, score_sorting_similarity

from cachier import cachier

import os
cwd = os.getcwd()
print(cwd)

repos = [
    "ErikBrendel/LudumDare",
    "ErikBrendel/LD35",
    # "eclipse/eclipse.jdt.core",
    # "jenkinsci/jenkins",
    # "jOOQ/jOOQ",
    "wumpz/jhotdraw",
    "neuland/jade4j",
    # "square/okhttp", <-- node sets too small???
    "apache/log4j",
    "junit-team/junit4",
    "jfree/jfreechart",
    "vanzin/jEdit",
    "hunterhacker/jdom",
]
metrics = ["structural", "evolutionary", "linguistic", "module_distance"]

repos.sort(key=lambda repo: len(LocalRepo(repo).get_all_interesting_files()))


fig, axes = plt.subplots(len(repos), 4, figsize=(15, len(repos) * 2.5), constrained_layout=True)
fig.suptitle('How well can a combination of three views predict the fourth?', fontsize=15)

repo_obj_cache: dict[str, LocalRepo] = dict()
repo_metric_cache: dict[str, CouplingGraph] = dict()
repo_metric_values_cache: dict[str, list[list[float]]] = dict()


def get_view(repo: str, view: str) -> CouplingGraph:
    key = repo + "-" + view
    if key not in repo_metric_cache:
        if repo not in repo_obj_cache:
            repo_obj_cache[repo] = LocalRepo(repo)
            repo_obj_cache[repo].update()
        repo_metric_cache[key] = MetricManager.get(repo_obj_cache[repo], view)
    return repo_metric_cache[key]


def get_metric_values(repo: str, max_node_pairs_to_check=10000) -> list[list[float]]:
    if repo not in repo_metric_values_cache:
        graphs = [get_view(repo, view) for view in metrics]
        nodes = sorted(list(get_graph_node_set_combination(graphs)))
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
def check_predictability_params_fast(repo: str, metric: str, other_metrics: tuple[str], weights: tuple[float]) -> float:
    metric_values = get_metric_values(repo)
    mi = metrics.index(metric)
    other_indices = [metrics.index(other_metric) for other_metric in other_metrics]
    def other_combination(entry: list[float]) -> float:
        return sum(w * entry[oi] for oi, w in zip(other_indices, weights))

    target_data_list: list[tuple[float, float]] = [(other_combination(entry), entry[mi]) for entry in metric_values]
    return score_sorting_similarity(target_data_list)
# check_predictability_params_fast.clear_cache()

@cachier()
def check_predictability_params(repo: str, metric: str, other_metrics: tuple[str], weights: tuple[float]) -> float:
    pred_graph = get_view(repo, metric)
    comp_graph = WeightCombinedGraph([get_view(repo, m) for m in other_metrics], weights)
    return pred_graph.how_well_predicted_by(comp_graph, max_node_pairs_to_check=5000)
# print(check_predictability_params.cache_dpath())
# check_predictability_params.clear_cache()

for ri, repo in enumerate(repos):
    print(pyfiglet.figlet_format(repo))

    for mi, predicted_metric in enumerate(metrics):
        other_metrics = tuple(metrics[:mi] + metrics[mi + 1:])

        scale = 16
        total_sample_count = (scale + 1) * (scale + 2) / 2
        bar = log_progress("Calculating color values for plot", total=total_sample_count)

        def check_predictability(weights):
            global bar
            bar.update()
            return check_predictability_params_fast(repo, predicted_metric, other_metrics, tuple(weights))

        tax = ternary.TernaryAxesSubplot(ax=axes[ri, mi], scale=scale)
        tax.heatmapf(check_predictability, boundary=True,
                     style="hex", colorbar=True,
                     vmin=0.5, vmax=1)
        bar.close()
        # tax.gridlines(color="blue", multiple=scale / 4)

        fontsize = 9
        tax.right_corner_label(other_metrics[0], fontsize=fontsize, position=(0.9, 0.04, 0.1))
        tax.top_corner_label(other_metrics[1], fontsize=fontsize, offset=0.12)
        tax.left_corner_label(other_metrics[2], fontsize=fontsize, position=(0.08, 0.04, 0))

        # tax.set_title(repo + ": Predicting " + predicted_metric)
        tax.boundary(linewidth=1.0)
        axes[ri, mi].axis('off')
        if mi == 0:
            axes[ri, mi].text(-0.4, 0.5, " / ".join(repo.split("/")), horizontalalignment='center',
                              verticalalignment='center', transform=axes[ri, mi].transAxes,
                              rotation="vertical", fontsize=12)
        if ri == 0:
            axes[ri, mi].text(0.5, 1.1, "Predicting " + predicted_metric, horizontalalignment='center',
                              verticalalignment='center', transform=axes[ri, mi].transAxes,
                              fontsize=12)

        # tax.show()
        # noinspection PyProtectedMember
        tax._redraw_labels()
plt.show()
