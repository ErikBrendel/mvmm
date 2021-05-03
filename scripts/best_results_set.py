import random

import numpy as np
from scipy.spatial import ConvexHull

from util import *


class BestResultsSet:
    def __init__(self, dimension_count, result_keep_size):
        self.dimension_count = dimension_count
        self.result_keep_size = result_keep_size
        self.data = []  # pair of ([coordinates per dimension], user-data)
        self.total_amount = 0

    def add_all(self, new_data):
        self.data += new_data
        self.total_amount += len(new_data)

    def get_best(self, dim_weights):
        def sort_key(datum):
            return sum(datum[0][i] * weight for i, weight in enumerate(dim_weights))

        self.data.sort(key=sort_key)
        return self.data[:self.result_keep_size]

    def get_best_unsorted(self, dim_weights, size_factor=1):
        # from https://stackoverflow.com/a/23734295/4354423
        def sort_key(datum):
            return sum(datum[0][i] * weight for i, weight in enumerate(dim_weights))

        res_size = self.result_keep_size * size_factor
        sort_data = [sort_key(d) for d in self.data]
        ind = np.argpartition(sort_data, res_size)[:res_size]
        return (self.data[i] for i in ind)

    def trim(self):
        if len(self.data) < 10:
            return
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html
        # http://www.qhull.org/html/qh-quick.htm#options
        # import pprofile
        # profiler = pprofile.Profile()
        # with profiler:
        dimensions = len(self.data[0][0])
        random.shuffle(self.data)
        hull_points = set()
        data_coordinates_indices = [(x[0], ind) for ind, x in enumerate(self.data)]
        hull_data = None
        for _it in range(self.result_keep_size):
            for d in range(len(data_coordinates_indices[0][0]) - 1, -1, -1):  # eliminate degenerate dimensions
                if all(x[d] == data_coordinates_indices[0][0][d] for x, ind in data_coordinates_indices):
                    # print("Removing degenerate dimension " + str(d))
                    data_coordinates_indices = [(tuple(x[:d]+x[d+1:]), ind) for x, ind in data_coordinates_indices]
                    hull_data = None
            if hull_data is None:
                hull_data = [x for x, ind in data_coordinates_indices]
            if len(hull_data[0]) < 2:
                return  # degenerate nodes? just don't trim...
            hull = ConvexHull(hull_data, qhull_options="Qs")
            hull_points.update(data_coordinates_indices[i][1] for i in hull.vertices)
            remove_indices(data_coordinates_indices, hull.vertices)
            remove_indices(hull_data, hull.vertices)
            if len(data_coordinates_indices) < dimensions + 2:
                return  # just abort the whole trimming: all of the data points are important!
        # print("Reduced result size from " + str(len(self.data)) + " to " + str(len(hull_points)))
        self.data = list(self.data[ind] for ind in hull_points)

        # import uuid
        # profiler.dump_stats("trim-stats-" + str(uuid.uuid1()) + ".txt")
        # print("Saved profiling results!")

