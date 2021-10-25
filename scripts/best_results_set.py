import pickle
import random

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.qhull import QhullError

from custom_types import *
from util import *


BRS_DATA_TYPE = Tuple[Sequence[float], any]  # pair of ([coordinates per dimension], user-data)


class BestResultsSet:
    def __init__(self, dimension_count, result_keep_size):
        self.dimension_count = dimension_count
        self.result_keep_size = result_keep_size
        self.data: List[BRS_DATA_TYPE] = []
        self.total_amount = 0

    def add(self, new_data: BRS_DATA_TYPE):
        self.data.append(new_data)
        self.total_amount += 1

    def add_all(self, new_data: List[BRS_DATA_TYPE]):
        self.data += new_data
        self.total_amount += len(new_data)

    def get_best(self, dim_weights: List[float], square_errors=True) -> List[BRS_DATA_TYPE]:
        sq = (lambda x: x*x) if square_errors else (lambda x: x)
        def sort_key(datum: BRS_DATA_TYPE):
            return sum(sq(datum[0][d]) * weight for d, weight in enumerate(dim_weights))

        self.data.sort(key=sort_key)
        return self.data[:self.result_keep_size]

    def get_best_unsorted(self, dim_weights: List[float], size_factor=1):
        # from https://stackoverflow.com/a/23734295/4354423
        def sort_key(datum: BRS_DATA_TYPE):
            return sum(datum[0][i] * weight for i, weight in enumerate(dim_weights))

        res_size = self.result_keep_size * size_factor
        sort_data = [sort_key(d) for d in self.data]
        ind = np.argpartition(sort_data, res_size)[:res_size]
        return (self.data[i] for i in ind)

    def trim(self):
        if len(self.data) < 10:
            return
        try:
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html
            # http://www.qhull.org/html/qh-quick.htm#options
            # import pprofile
            # profiler = pprofile.Profile()
            # with profiler:
            random.shuffle(self.data)
            hull_points = set()
            data_coordinates_indices = [(x[0], ind) for ind, x in enumerate(self.data)]
            hull_data = None
            for _it in range(self.result_keep_size):
                for d in range(len(data_coordinates_indices[0][0]) - 1, -1, -1):  # eliminate degenerate dimensions
                    reference_value = data_coordinates_indices[0][0][d]
                    if all(abs(x[d] - reference_value) < 0.000001 for x, ind in data_coordinates_indices):
                        # print("Removing degenerate dimension " + str(d))
                        data_coordinates_indices = [(tuple(x[:d]+x[d+1:]), ind) for x, ind in data_coordinates_indices]
                        hull_data = None
                dimensions = len(data_coordinates_indices[0][0])
                if dimensions < 2:
                    return  # degenerate nodes? just don't trim...
                if hull_data is None:
                    # add fake points to limit the hull to our quadrant only
                    outer_points = [([1] * dimensions) for _p in range(dimensions + 1)]
                    hull_data = outer_points + [x for x, ind in data_coordinates_indices]
                # update outer points
                min_values = [min(coords[d] for coords, ind in data_coordinates_indices) + 0.000001 for d in range(dimensions)]
                fake_point_count = dimensions + 1
                for d in range(dimensions):
                    hull_data[d][d] = min_values[d]
                # do the hull
                hull = ConvexHull(hull_data)  # qhull_options="Qs QJ0.001" ?
                actual_indices = [i - fake_point_count for i in hull.vertices if i >= fake_point_count]
                hull_points.update(data_coordinates_indices[i][1] for i in actual_indices)
                remove_indices(data_coordinates_indices, actual_indices)
                remove_indices(hull_data, [i for i in hull.vertices if i >= fake_point_count])
                if len(data_coordinates_indices) < dimensions + 2:
                    return  # just abort the whole trimming: all of the data points are important!
            print("Reduced result size from " + str(len(self.data)) + " to " + str(len(hull_points)))
            self.data = list(self.data[ind] for ind in hull_points)

            # import uuid
            # profiler.dump_stats("trim-stats-" + str(uuid.uuid1()) + ".txt")
            # print("Saved profiling results!")
        except QhullError as qhe:
            print("QHull crashed! No trimming will be performed: " + str(qhe).split("\n")[0])

    def export(self, name: str):
        os.makedirs(self._get_dir_name(name), exist_ok=True)
        with open(name, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(name) -> Optional['BestResultsSet']:
        if not os.path.isfile(name):
            return None
        with open(name, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def get_name(repo_name: str, views: List[str], node_filter_mode: str, target_pattern: PatternType) -> str:
        return "../analysis_results/" + repo_name + "/" + node_filter_mode + "_" + "_".join(view + str(val) for view, val in zip(views, target_pattern)) + ".pickle"

    @staticmethod
    def _get_dir_name(name: str) -> str:
        return "/".join(name.split("/")[:-1])
