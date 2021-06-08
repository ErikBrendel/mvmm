# from https://github.com/pandas-dev/pandas/blob/master/pandas/plotting/_matplotlib/misc.py#L348
# see also https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.plotting.parallel_coordinates.html
import random
from typing import *
import matplotlib.pyplot as plt


def parallel_coordinates(ax, dimensions: List[str], data: List[Tuple[List[float], float]], wiggle_strength, **kwargs):

    random.seed(789456)
    # disperse data according to neighbour data
    neigh_dispersion_factor = 0.01
    for y, val in data:
        y[0] = (y[0] + y[1] * neigh_dispersion_factor * 2) / (1 + neigh_dispersion_factor * 2)
        y[-1] = (y[-1] + y[-2] * neigh_dispersion_factor * 2) / (1 + neigh_dispersion_factor * 2)
        for i in range(1, len(y) - 1):
            y[i] = (y[i] + y[i - 1] * neigh_dispersion_factor + y[i + 1] * neigh_dispersion_factor) / (1 + neigh_dispersion_factor * 2)

    # randomly disperse the data
    random.shuffle(data)
    for y, val in data:
        for i in range(len(y)):
            y[i] += random.uniform(-wiggle_strength, wiggle_strength)

    axvlines_kwds = {"linewidth": 1, "color": "black"}

    n = len(data)

    ncols = len(dimensions)

    x = list(range(ncols))

    if ax is None:
        ax = plt.gca()

    min_value = min(d[1] for d in data)
    max_value = max(d[1] for d in data)
    print("Value range: " + str(min_value) + " to " + str(max_value))

    sm = plt.cm.ScalarMappable(cmap=None, norm=plt.Normalize(vmin=min_value, vmax=max_value))

    for alpha in [1]:
        for y, color_value in data:
            rgba = (0.5, 0, 0, color_value ** 15)
            # rgba = tuple(list(rgba[0:3]) + [alpha])
            ax.plot(x, y, color=rgba, **kwargs)

    if True:
        for i in x:
            ax.axvline(i, **axvlines_kwds)

    ax.set_xticks(x)
    ax.set_xticklabels(dimensions)
    ax.set_xlim(x[0], x[-1])
    ax.grid()
    return ax