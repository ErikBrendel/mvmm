from tqdm.notebook import tqdm as log_progress
from functools import partial

log_progress = partial(log_progress, smoothing=0.1)
import math
import time
import re
import regex
from multiprocessing import Pool, TimeoutError, Process, Manager, Lock


# https://github.com/kuk/log-progress
# https://github.com/tqdm/tqdm/blob/master/tqdm/notebook.py
# https://github.com/tqdm/tqdm/blob/master/tqdm/std.py

def all_pairs(data):
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


def generate_one_distributions(dim, precision=10):
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


def decode(byte_data):
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


class DirectoryExclusionTracker:
    def __init__(self, exclusion_keywords):
        self.exclusion_keywords = exclusion_keywords
        self.exclusion_regex = re.compile(r'\b' + '|'.join(exclusion_keywords) + r'\b')
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
        first_exclusion_pos = min(parts.index(exclusion_keyword) for exclusion_keyword in self.exclusion_keywords if
                                  exclusion_keyword in parts)
        root = "".join(parts[:first_exclusion_pos + 1])
        self.skipped_roots.append(root)


PARALLEL_MAP_DEBUG_MODE = False

PARALLEL_THREADS = 64
MIN_PARALLEL_BATCH_SIZE = 64
MAX_PARALLEL_BATCH_SIZE = 1024
MIN_STEP_SIZE = 10  # at most a thenth of data should be done in one batch


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
        t = None

        def wrapped(*args, **kwargs):
            nonlocal t
            t_ = time.time()
            if t is None or t_ - t >= s:
                result = f(*args, **kwargs)
                t = time.time()
                return result

        return wrapped

    return decorate


import ipywidgets as widgets
from IPython.display import display


def interactive_multi_sort(data, dimension_names_and_getters, callback_func, output_height="350px"):
    """names and getters: [('dim1', getter), ('dim2', getter)], names must be unique"""

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
            total += slider_values[name] * getter_func(datum)
        return total

    # Todo: https://ipywidgets.readthedocs.io/en/latest/examples/Using%20Interact.html?highlight=event#Arguments-that-are-dependent-on-each-other
    # https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Styling.html#The-Grid-layout
    @debounce(0.2)
    def slider_func(**kwargs):
        if update_sliders(**kwargs):
            return
        print(", ".join(name + ": " + "{:1.4f}".format(val) for name, val in slider_values.items()))
        data.sort(key=sort_key)
        callback_func(data)

    initial_slider_value = 1.0 / len(dimension_names_and_getters)
    for name, getter_func, *_ in dimension_names_and_getters:
        slider_values[name] = initial_slider_value
        sliders[name] = widgets.FloatLogSlider(base=10, min=-3, max=0, step=0.01, value=initial_slider_value,
                                               continuous_update=True,
                                               layout={'width': '500px'})
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
    display(widgets.HTML(value=content))


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


if __name__ == "__MAIN__":
    print(len(list(generate_one_distributions(5, 5))))
    for x in generate_one_distributions(5, 5):
        print(" ".join("{:1.1f}".format(d) for d in x))
