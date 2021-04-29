import numpy as np
from tqdm.notebook import tqdm as log_progress
from functools import partial

log_progress = partial(log_progress, smoothing=0.1)

from util import *

"""  # OLD CLASS
class BestResultsSet:
    def __init__(self, dimension_count, result_keep_size):
        self.dimension_count = dimension_count
        self.result_keep_size = result_keep_size
        self.data = []  # pair of ([coordinates per dimension], user-data)
        self.total_amount = 0
    
    def add_all(self, new_data):
        self.data += new_data
        self.total_amount += len(new_data)
        self.trim_maybe()
        
    def get_best(self, dim_weights):
        def sort_key(datum):
            return sum(datum[0][i] * weight for i, weight in enumerate(dim_weights))
        self.data.sort(key=sort_key)
        return self.data[:self.result_keep_size]
    
    def trim_maybe(self):
        if len(self.data) > self.result_keep_size * 10 * self.dimension_count:
            self.trim()
    
    def trim(self):
        result_keep_tolerance = 2  # higher = keep more, but better chance at not accidentally removing important stuff
        sampling_accuracy = 10  # higher = more runtime, but more acurately detecting required important data
        # previous_size = len(self.data)
        important_data = set()
        prev_result_keep_size = self.result_keep_size
        self.result_keep_size *= result_keep_tolerance
        for dim_weight in log_progress(list(generate_one_distributions(self.dimension_count, sampling_accuracy)), desc="Trimming"):
            important_data.update(self.get_best(dim_weight))
        self.result_keep_size = prev_result_keep_size
        self.data = list(important_data)
        # print("Trimming reduced from", previous_size, "to", len(self.data), "elements")
"""  # NEW CLASS


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
        result_keep_tolerance = 5  # higher = keep more, but better chance at not accidentally removing important stuff
        sampling_accuracy = 5  # higher = more runtime, but more acurately detecting required important data
        # previous_size = len(self.data)
        important_data = set()
        for dim_weight in log_progress(list(generate_one_distributions(self.dimension_count, sampling_accuracy)), desc="Trimming"):
            important_data.update(self.get_best_unsorted(dim_weight, result_keep_tolerance))
        self.data = list(important_data)
        # print("Trimming reduced from", previous_size, "to", len(self.data), "elements")
# """
