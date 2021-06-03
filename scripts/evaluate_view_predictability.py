import math
import time

import matplotlib.pyplot as plt
import pyfiglet
import ternary

from graph import WeightCombinedGraph
from local_repo import LocalRepo
from metrics import MetricManager
from util import log_progress

repo = "ErikBrendel/LudumDare"
metrics = ["structural", "evolutionary", "linguistic", "module_distance"]

r = LocalRepo(repo)
print(pyfiglet.figlet_format(r.name))
r.update()

for i, predicted_metric in enumerate(metrics):
    other_metrics = metrics[:i] + metrics[i+1:]
    pred_graph = MetricManager.get(r, predicted_metric)
    comp_graph = WeightCombinedGraph([MetricManager.get(r, m) for m in other_metrics])

    scale = 8
    total_sample_count = (scale + 1) * (scale + 2) / 2
    bar = log_progress("Calculating color values for plot", total=total_sample_count)

    def check_predictability(weights):
        global bar
        bar.update()
        comp_graph.weights = weights
        return pred_graph.how_well_predicted_by(comp_graph, max_node_pairs_to_check=1000)

    figure, tax = ternary.figure(scale=scale)
    tax.heatmapf(check_predictability, boundary=True, style="hex") # vmin=0, vmax=1
    bar.close()
    # tax.gridlines(color="blue", multiple=scale / 4)

    fontsize = 12
    tax.right_corner_label(other_metrics[0], fontsize=fontsize)
    tax.top_corner_label(other_metrics[1], fontsize=fontsize)
    tax.left_corner_label(other_metrics[2], fontsize=fontsize)
    tax.set_title("Predicting " + predicted_metric)
    tax.boundary(linewidth=1.0)
    plt.axis('off')

    tax.show()
