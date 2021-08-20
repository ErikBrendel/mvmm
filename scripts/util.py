import os
import random
from typing import *

if os.environ.get("JUPYTER"):
    from tqdm.notebook import tqdm as log_progress
else:
    from tqdm import tqdm as log_progress

from functools import partial

log_progress = partial(log_progress, smoothing=0.1)

import math
import time
import re
import regex
from multiprocessing import Pool, TimeoutError, Process, Manager, Lock
from matplotlib import pyplot as plt
import numpy as np


# https://github.com/kuk/log-progress
# https://github.com/tqdm/tqdm/blob/master/tqdm/notebook.py
# https://github.com/tqdm/tqdm/blob/master/tqdm/std.py


def all_pairs(data: List[any]) -> Generator[Tuple[any, any], None, None]:
    length = len(data)
    for i in range(length):
        for j in range(i):
            yield data[j], data[i]


def frange(start, stop, step):
    if step > 0:
        r = start
        while r < stop - 0.0001:
            yield r
            r += step
    else:
        r = start
        while r > stop + 0.0001:
            yield r
            r += step
    yield stop


def generate_one_distributions(dim: int, precision=10) -> Generator[List[float], None, None]:
    """precision = how many steps between 0 and 1"""
    decrement_step = -1 / precision
    result = [0 for i in range(dim)]

    def fill_first(digits, total_value):
        if digits == 1:
            result[0] = total_value
            yield result[:]
            return
        if total_value < 0.0001:
            for i in range(digits):
                result[i] = 0
            yield result[:]
            return
        for val in frange(total_value, 0, decrement_step):
            result[digits - 1] = val
            yield from fill_first(digits - 1, total_value - val)

    yield from fill_first(dim, 1)


def decode(byte_data: bytes) -> str:
    try:
        return byte_data.decode("utf-8")
    except:
        try:
            return byte_data.decode("ISO-8859-1")
        except:
            raise Exception("Cannot decode!")


def common_prefix_length(a, b):
    for i, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            return i
    return min(len(a), len(b))


def unindent_code_snippet(code: str) -> str:
    """given multiple lines of code, where all but the first are indented, remove that indent uniformly so that the code is moved to the left"""
    if "\n" not in code:
        return code
    content = code.split("\n")
    overall_indent = 0
    # increase indent while all lines (except unindented first) actually have indent at that place or are empty
    while all(len(line) <= overall_indent or line[overall_indent].isspace() for line in content[1:]):
        overall_indent += 1
    content = [content[0]] + [line[overall_indent:] for line in content[1:]]
    return "\n".join(content)



class DirectoryExclusionTracker:
    def __init__(self, exclusion_keywords):
        self.exclusion_keywords = exclusion_keywords
        self.exclusion_regex = re.compile(r'\b(' + '|'.join(exclusion_keywords) + r')\b')
        self.skipped_roots = []

    def should_get_skipped(self, path):
        for root in self.skipped_roots:
            if path.startswith(root):
                return True
        if self.exclusion_regex.search(path) is not None:
            self._add_root_from(path)
            return True
        return False

    def get_skipped_roots(self):
        return self.skipped_roots

    def _add_root_from(self, path):
        parts = re.findall(r'\w+|\W+', path)
        seq = [w for w in self.exclusion_keywords if w in parts]
        if len(seq) == 0:
            return
        first_exclusion_pos = min(parts.index(exclusion_keyword) for exclusion_keyword in self.exclusion_keywords if
                                  exclusion_keyword in parts)
        root = "".join(parts[:first_exclusion_pos + 1])
        self.skipped_roots.append(root)


PARALLEL_MAP_DEBUG_MODE = False

PARALLEL_THREADS = 64
MIN_PARALLEL_BATCH_SIZE = 64
MAX_PARALLEL_BATCH_SIZE = 1024
MIN_STEP_SIZE = 10  # at most a tenth of data should be done in one batch


def map_parallel(data_list, mapper, result_handler, desc, force_non_parallel=False):
    """the mapper is distributed, result_handler is called on the main thread"""
    if PARALLEL_MAP_DEBUG_MODE or force_non_parallel:
        for elem in log_progress(data_list, desc=desc):
            result = mapper(elem)
            if result is not None:
                result_handler(result)
    else:
        data_length = len(data_list)
        batch_size = min(max(MIN_PARALLEL_BATCH_SIZE, math.ceil(data_length / PARALLEL_THREADS / MIN_STEP_SIZE)),
                         MAX_PARALLEL_BATCH_SIZE)
        print("Going parallel, with a batch size of " + str(batch_size) + " of " + str(
            data_length) + ", resulting in " + str(math.ceil(data_length / batch_size)) + " batches.")
        with Pool(processes=PARALLEL_THREADS) as pool:
            bar = log_progress(total=len(data_list), desc=desc)
            results = pool.imap_unordered(mapper, data_list, batch_size)
            # single-threaded alternative for debugging:

            for result in results:
                if result is not None:
                    result_handler(result)
                bar.update()

            bar.close()


def show_histogram(data, title, xlabel='Data', ylabel='Amount', color='g'):
    # https://matplotlib.org/3.3.1/api/_as_gen/matplotlib.pyplot.hist.html
    if len(data) == 0:
        print("Empty data, cannot show histogram")
        return
    plt.hist(data, "auto", facecolor=color, alpha=0.75)
    plt.axvline(np.array(data).mean(), color='k', linestyle='dashed', linewidth=1)
    # plt.xscale("log")
    # plt.yscale("log")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.show()


def smoothstep(x):
    return x * x * (3 - 2 * x)


def smootherstep(x):
    return x * x * x * (x * (x * 6 - 15) + 10)


TAN_SIZE_X = 5  # higher = more smoothing
TAN_SIZE_Y = math.atan(TAN_SIZE_X)


def smoothstep_tan(x):
    return math.atan(x * TAN_SIZE_X * 2 - TAN_SIZE_X) / TAN_SIZE_Y / 2 + 0.5


def inv_smoothstep_tan(x):
    return (math.tan((x - 0.5) * TAN_SIZE_Y * 2) + TAN_SIZE_X) / TAN_SIZE_X / 2


def debounce(s):
    """Decorator ensures function that can only be called once every `s` seconds.
    """

    def decorate(f):
        t: Optional[float] = None

        def wrapped(*args, **kwargs):
            nonlocal t
            t_ = time.time()
            if t is None or t_ - t >= s:
                result = f(*args, **kwargs)
                t = time.time()
                return result

        return wrapped

    return decorate




def interactive_multi_sort(data, dimension_names_and_getters, callback_func, output_height="350px", square_errors=True):
    """names and getters: [('dim1', getter), ('dim2', getter)], names must be unique"""
    import ipywidgets as widgets
    from IPython.display import display

    dim_names = [name for name, getter, *_ in dimension_names_and_getters]
    slider_values = {}
    sliders = {}

    def balance_slider_values(keep_name):
        current_sum = sum(slider_values.values())
        if abs(current_sum - 1) < 0.001:
            return False
        new_keep_value = slider_values[keep_name]
        if new_keep_value == current_sum:
            new_val = (1.0 - new_keep_value) / (len(dim_names) - 1)
            for name in dim_names:
                if name != keep_name:
                    slider_values[name] = new_val
                    sliders[name].value = slider_values[name]
        else:
            reduce_factor = (1 - new_keep_value) / (current_sum - new_keep_value)
            for name in dim_names:
                if name != keep_name:
                    slider_values[name] *= reduce_factor
                    old_callbacks = sliders[name]._msg_callbacks
                    sliders[name]._msg_callbacks = sliders[name]._msg_callbacks.__class__()
                    sliders[name].value = slider_values[name]
                    sliders[name]._msg_callbacks = old_callbacks
        return True

    def update_sliders(**kwargs):
        changed_name = None
        for name in dim_names:
            if abs(slider_values[name] - sliders[name].value) > 0.001:
                slider_values[name] = sliders[name].value
                changed_name = name
        if changed_name is not None:
            return balance_slider_values(changed_name)
        else:
            return False

    def sort_key(datum):
        # assumes normalized (summing to 1) values in "slider_values"
        total = 0
        for name, getter_func, *_ in dimension_names_and_getters:
            error = getter_func(datum)
            if square_errors:
                error *= error
            total += slider_values[name] * error
        return total

    # Todo: https://ipywidgets.readthedocs.io/en/latest/examples/Using%20Interact.html?highlight=event#Arguments-that-are-dependent-on-each-other
    # https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Styling.html#The-Grid-layout
    @debounce(0.2)
    def slider_func(**kwargs):
        if update_sliders(**kwargs):
            return
        # print(", ".join(name + ": " + "{:1.4f}".format(val) for name, val in slider_values.items()))
        data.sort(key=sort_key)
        callback_func(data)

    initial_slider_value = 1.0 / len(dimension_names_and_getters)
    for name, getter_func, *_ in dimension_names_and_getters:
        slider_values[name] = initial_slider_value
        sliders[name] = widgets.FloatLogSlider(base=10, min=-3, max=0, step=0.01, value=initial_slider_value,
                                               continuous_update=True,
                                               layout={'width': '900px'})
        # sliders[name].observe(slider_func, 'value')
    # out = widgets.interactive_output(slider_func, sliders)
    # ui = widgets.VBox(sliders.values())
    # display(ui, out)
    interactive_plot = widgets.interactive(slider_func, **sliders)
    # https://ipywidgets.readthedocs.io/en/latest/examples/Using%20Interact.html?highlight=event#Flickering-and-jumping-output
    interactive_plot.children[-1].layout.height = output_height
    display(interactive_plot)
    # widgets.interact_manual(slider_func, **sliders)


def print_html(content):
    # using the IPython.display.HTML thingy (instead of ipywidgets.HTML) to enable JS execution
    # https://github.com/jupyter-widgets/ipywidgets/issues/3079#issuecomment-856390435
    import ipywidgets as widgets
    import IPython.display as display
    # display.display(widgets.HTML(value=content))
    display.display(display.HTML(content))


def show_html_table(data, width=None):
    if width == None:
        width = len(data[0])
    rows = []
    for datum in data:
        rows.append("".join("<td>" + str(datum[i]) + "</td>" for i in range(width)))
    html = '<table border="1" style="border-collapse: collapse">' + "".join(
        "<tr>" + row + "</tr>" for row in rows) + "</table>"
    print_html(html)


# public so other code can use it
def path_module_distance(a, b):
    if a == b:
        return 0
    steps_a = a.split("/")
    steps_b = b.split("/")
    min_len = min(len(steps_a), len(steps_b))
    for i in range(min_len):
        if steps_a[i] == steps_b[i]:
            continue
        # unequal: calc distance
        return len(steps_a) + len(steps_b) - (i * 2)
    return len(steps_a) + len(steps_b) - (min_len * 2)


def remove_indices(list_to_modify, indices_list):
    # removes all the elements in the list_to_modify, and fills those empty places up
    # with not-to-removable elements from the back of the list, super-fast.
    # assumes that the second parameter is way smaller than the first one
    # inspired by: https://stackoverflow.com/a/8313120/4354423
    indices_list.sort()
    indices_set = set(indices_list)
    back_move_pointer = len(list_to_modify) - 1
    while back_move_pointer in indices_set:
        back_move_pointer -= 1
    for index_to_remove in indices_list:
        if index_to_remove >= back_move_pointer:
            break
        list_to_modify[index_to_remove] = list_to_modify[back_move_pointer]
        back_move_pointer -= 1
        while back_move_pointer in indices_set:
            back_move_pointer -= 1
    result_length = len(list_to_modify) - len(indices_list)
    del list_to_modify[result_length:]
    # list_to_modify[:] = [x for i, x in enumerate(list_to_modify) if i not in indices]


def fill_none_with_other(hole_list: List[Optional[any]], filler: List[any]):
    """replace all the None elements in the given list with the values from the filler list"""
    try:
        for f in filler:
            hole_list[hole_list.index(None)] = f
    except ValueError:
        return  # happens when no more None values are present


def count_inversions(arr, key_fn=lambda e: e):
    """ from https://gist.github.com/dishaumarwani/b6d5f4a1b2f741d5bee8d0f69263c48f """
    def merge(l, m, r):
        # No need of merging if subarray form a sorted array after joining
        if key_fn(arr[m]) <= key_fn(arr[m + 1]):
            return 0

        inversion_count = 0
        L = arr[l:m + 1]
        R = arr[m + 1:r + 1]

        # Merge the temp arrays back into arr[l..r]

        i = 0  # Initial index of first subarray
        j = 0  # Initial index of second subarray
        k = l  # Initial index of merged subarray

        len_l = m + 1 - l
        len_r = r - m

        while i < len_l and j < len_r:
            if key_fn(L[i]) <= key_fn(R[j]):
                arr[k] = L[i]
                i += 1
            else:
                inversion_count += len_l - i
                arr[k] = R[j]
                j += 1
            k += 1

        arr[k: k + len_l - i] = L[i:]

        return inversion_count

    def merge_sort(l, r):
        if l < r:
            m = (l + r) // 2
            return merge_sort(l, m) + merge_sort(m + 1, r) + merge(l, m, r)
        return 0

    return merge_sort(0, len(arr) - 1)


def count_relative_inversions(arr, key_fn=lambda e: e):
    comp_values = [key_fn(e) for e in arr]
    comp_values.sort(reverse=True)
    max_inversions = count_inversions(comp_values)
    if max_inversions == 0:
        print("[WARN] cannot really count inversions on this data!")
        return 0.5  # we do not know - so let's say it is about half sorted :D
    return count_inversions(arr, key_fn) / max_inversions


def score_sorting_similarity(data: List[Tuple[float, float]]) -> float:
    # data.sort(key=lambda e: e[0] * 10000000 + e[1])
    # predictability_score = 1.0 - count_relative_inversions(data[:], lambda e: e[1])
    # best_score = predictability_score
    data.sort(key=lambda e: e[0] * 10000000 - e[1])
    predictability_score = 1.0 - count_relative_inversions(data[:], lambda e: e[1])
    worst_score = predictability_score
    return worst_score


if __name__ == "__main__":
    print(len(list(generate_one_distributions(5, 5))))
    for x in generate_one_distributions(5, 5):
        print(" ".join("{:1.1f}".format(d) for d in x))
