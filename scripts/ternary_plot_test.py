import math
import time

import matplotlib.pyplot as plt
import ternary

from util import log_progress

# https://github.com/marcharper/python-ternary
# https://github.com/marcharper/python-ternary/blob/master/examples/Ternary-Examples.ipynb

scale = 8
total_sample_count = (scale + 1) * (scale + 2) / 2

bar = log_progress("Calculating things", total=total_sample_count)


def shannon_entropy(p):
    """Computes the Shannon Entropy at a distribution in the simplex."""
    global bar
    bar.update()
    s = 0.
    for i in range(len(p)):
        try:
            s += p[i] * math.log(p[i])
        except ValueError:
            continue
    time.sleep(0.01)
    print(p)
    return min(-1. * s, 1)


def single_component(p):
    return p[0]


figure, tax = ternary.figure(scale=scale)
tax.heatmapf(shannon_entropy, boundary=True, style="dual-triangular")
bar.close()
# tax.gridlines(color="blue", multiple=scale / 4)


fontsize = 12
tax.right_corner_label("Red mama", fontsize=fontsize)
tax.top_corner_label("Green mama", fontsize=fontsize)
tax.left_corner_label("Blue mama", fontsize=fontsize)
# tax.set_title("Shannon Entropy Heatmap")
tax.boundary(linewidth=1.0)
# tax.ticks(ticks=["0", "25", "50", "75", "100"])
plt.axis('off')

tax.show()
