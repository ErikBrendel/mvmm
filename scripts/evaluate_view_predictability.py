import math
import time

import matplotlib.pyplot as plt
import pyfiglet
import ternary

from graph import WeightCombinedGraph
from local_repo import LocalRepo
from metrics import MetricManager
from util import log_progress

repos = [
    "ErikBrendel/LudumDare",
    "ErikBrendel/LD35",
    # "eclipse/eclipse.jdt.core",
    # "jenkinsci/jenkins",
    "jOOQ/jOOQ",
    "wumpz/jhotdraw",
    "neuland/jade4j",
]
metrics = ["structural", "evolutionary", "linguistic", "module_distance"]


fig, axes = plt.subplots(len(repos), 4, figsize=(12, len(repos) * 3))
fig.suptitle('How well can a combination of three views predict the fourth?', fontsize=15)

for ri, repo in enumerate(repos):
    r = LocalRepo(repo)
    print(pyfiglet.figlet_format(r.name))
    r.update()

    for mi, predicted_metric in enumerate(metrics):
        other_metrics = metrics[:mi] + metrics[mi + 1:]
        pred_graph = MetricManager.get(r, predicted_metric)
        comp_graph = WeightCombinedGraph([MetricManager.get(r, m) for m in other_metrics])

        scale = 4
        total_sample_count = (scale + 1) * (scale + 2) / 2
        bar = log_progress("Calculating color values for plot", total=total_sample_count)

        def check_predictability(weights):
            global bar
            bar.update()
            comp_graph.weights = weights
            return pred_graph.how_well_predicted_by(comp_graph, max_node_pairs_to_check=1000)

        tax = ternary.TernaryAxesSubplot(ax=axes[ri, mi], scale=scale)
        tax.heatmapf(check_predictability, boundary=True,
                     style="hex", colorbar=True,
                     vmin=0.4, vmax=1)  # cmap="RdYlBu"
        bar.close()
        # tax.gridlines(color="blue", multiple=scale / 4)

        fontsize = 9
        tax.right_corner_label(other_metrics[0], fontsize=fontsize, position=(0.9, 0.04, 0.1))
        tax.top_corner_label(other_metrics[1], fontsize=fontsize, offset=0.12)
        tax.left_corner_label(other_metrics[2], fontsize=fontsize, position=(0.04, 0.04, 0))

        # tax.set_title(repo + ": Predicting " + predicted_metric)
        tax.boundary(linewidth=1.0)
        axes[ri, mi].axis('off')
        if mi == 0:
            axes[ri, mi].text(-0.4, 0.5, repo, horizontalalignment='center',
                              verticalalignment='center', transform=axes[ri, mi].transAxes,
                              rotation="vertical", fontsize=12)
        if ri == 0:
            axes[ri, mi].text(0.5, 1.1, "Predicting " + predicted_metric, horizontalalignment='center',
                              verticalalignment='center', transform=axes[ri, mi].transAxes,
                              fontsize=12)

        # tax.show()
        tax._redraw_labels()
plt.show()
