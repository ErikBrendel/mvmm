import statistics
import math
from cachier import cachier
from custom_types import *
from local_repo import LocalRepo
from analysis import analyze_disagreements, ALL_VIEWS, get_filtered_nodes
from best_results_set import BRS_DATA_TYPE
from blue_book_metrics import BB_METRICS, BBContext
from repos import repos_and_versions
from util import merge_dicts, plt_save_show
from prc_roc_auc import make_prc_plot, PRC_PLOT_DATA_ENTRY
from study_common import TAXONOMY, make_sort_weights
import matplotlib.pyplot as plt
from refactorings_detection import get_classes_being_refactored_in_the_future


def match_score(result: BRS_DATA_TYPE):
    errors = result[0]
    return statistics.mean(x * x for x in errors)


def find_violations_for_pattern(repo: LocalRepo, pattern: PatternType, filter_mode: NodeFilterMode) -> Set[str]:
    raw_results = analyze_disagreements(repo, ALL_VIEWS, [pattern], filter_mode)[0]
    results: Set[str] = set()
    for result in raw_results.get_best(make_sort_weights(pattern)):
        score = match_score(result)
        if score <= 0.15:
            a, b, *_ = result[1]
            results.add(a)
            results.add(b)
    return results


def find_violations_for_pattern_probabilities(repo: LocalRepo, pattern: PatternType, filter_mode: NodeFilterMode) -> Dict[str, float]:
    raw_results = analyze_disagreements(repo, ALL_VIEWS, [pattern], filter_mode)[0]
    results: Dict[str, float] = {}
    for result in raw_results.get_best(make_sort_weights(pattern)):
        score = match_score(result)
        a, b, *_ = result[1]
        for clazz in [a, b]:
            if clazz not in results or results[clazz] < score:
                results[clazz] = 1 - score
    return results


def find_violations_bb(repo: LocalRepo, bb_metric: str) -> List[str]:
    return BBContext.for_repo(repo).find_by_name(bb_metric)


def evaluate_metric_alignment(repo: LocalRepo, pattern: PatternType, bb_metric: str, filter_mode: NodeFilterMode) -> float:
    own_results = find_violations_for_pattern(repo, pattern, filter_mode)
    bb_results = set(find_violations_bb(repo, bb_metric))
    intersection_size = len(own_results.intersection(bb_results))
    union_size = len(own_results) + len(bb_results) - intersection_size
    if union_size == 0:
        return -0.01
    return intersection_size / float(union_size)


def make_individual_bb_alignment_table(repo: LocalRepo):
    sm = plt.cm.ScalarMappable(cmap=None, norm=plt.Normalize(vmin=0, vmax=1))
    columns = tuple(f"{''.join(w[0].upper() for w in m.split('_'))}: {len(find_violations_bb(repo, m))}" for m, _f in BB_METRICS)
    rows = tuple(f"{''.join([str(e) if e is not None else '*' for e in p])}: "
                 f"{len(find_violations_for_pattern(repo, p, 'methods'))} / {len(find_violations_for_pattern(repo, p, 'classes'))}"
                 for p, _n, _d in TAXONOMY)

    values = [[evaluate_metric_alignment(repo, p, m, f) for m, f in BB_METRICS] for p, _n, _d in TAXONOMY]
    colors = [[sm.to_rgba(cell) for cell in data] for data in values]
    cell_text = [[f"{int(cell * 100)}%" if cell >= 0 else "" for cell in data] for data in values]

    plt.axis('tight')
    plt.axis('off')
    table = plt.table(cellText=cell_text, cellColours=colors, colLabels=columns, rowLabels=rows, loc='center', cellLoc="center")
    table.scale(0.7, 1.5)
    for ri, row_values in enumerate(values):
        for ci, cell_value in enumerate(row_values):
            if cell_value < 0.4:
                # the header row is row 0. The header column is column -1
                table[ri + 1, ci].get_text().set_color("white")
    plt.colorbar(sm)
    plt.title(f"{repo.name}\nalignment of disagreement patterns and blue book disharmonies")
    plt.show()


def make_alignment_table(row_name: str, row_data: Set[str], col_name: str, col_data: Set[str], total_data: Set[str], title: str):
    not_row_data = total_data.difference(row_data)
    not_col_data = total_data.difference(col_data)

    columns = (f" {col_name} ", f" -{col_name} ", " Total ")
    rows = (f" {row_name} ", f" -{row_name} ", " Total ")

    def fmt(a: Set[str], b: Set[str] = None) -> str:
        if b is None:
            return str(len(a))
        intersection = len(a.intersection(b))
        return f"{int(intersection / float(len(a) + len(b) - intersection) * 100)}%\n({intersection})"

    cell_text = [
        [fmt(row_data, col_data), fmt(row_data, not_col_data), fmt(row_data)],
        [fmt(not_row_data, col_data), fmt(not_row_data, not_col_data), fmt(not_row_data)],
        [fmt(col_data), fmt(not_col_data), fmt(total_data)]
    ]
    plt.axis('tight')
    plt.axis('off')
    table = plt.table(cellText=cell_text, colLabels=columns, rowLabels=rows, loc='center', cellLoc="center")
    table.scale(0.5, 3.5)
    plt.title(title)
    accuracy = (len(row_data.intersection(col_data)) + len(not_row_data.intersection(not_col_data))) / float(len(total_data))
    super_balanced_accuracy = (  # https://en.wikipedia.org/wiki/Precision_and_recall#Imbalanced_data
                                      (len(row_data.intersection(col_data)) / len(row_data)) +
                                      (len(row_data.intersection(col_data)) / len(col_data)) +
                                      (len(not_row_data.intersection(not_col_data)) / len(not_row_data)) +
                                      (len(not_row_data.intersection(not_col_data)) / len(not_col_data))
                              ) / 4.0
    plt.text(0.5, 0.1, f"Accuracy: {int(accuracy * 100)}%, balanced: {int(super_balanced_accuracy * 100)}%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    plt.show()


PRC_DATA_ENTRY = Tuple[str, Union[Dict[str, float], Set[str]]]


def make_prc_plot_for(data_list: List[PRC_DATA_ENTRY], base_data: Set[str], total_data: Set[str], filename: str):
    if len(base_data) == 0:
        print(f"No data for {filename}")
        return
    data_comments: List[str] = []
    converted_data_list: List[PRC_PLOT_DATA_ENTRY] = []

    n = len(total_data)

    for name, original_data in data_list:
        converted_data: Union[List[float], List[int]]
        if isinstance(original_data, dict):
            converted_data = [original_data.get(item, 0) for item in total_data]
            zero_data = sum(x == 0 for x in converted_data)
            one_data = sum(x == 1 for x in converted_data)
            nontrivial_data = len(converted_data) - zero_data - one_data
            data_comments.append(f"{name} data:"
                                 f" 0: {zero_data} ({int(zero_data / n * 100)}%),"
                                 f" 1: {one_data} ({int(one_data / n * 100)}%),"
                                 f" nontrivial: {nontrivial_data} ({int(nontrivial_data / n * 100)}%)")
        else:
            converted_data = [1 if item in original_data else 0 for item in total_data]
            converted_ones = sum(converted_data)
            data_comments.append(f"{name} data: {converted_ones} ({int(converted_ones / n * 100)}%)")
        converted_data_list.append((name, converted_data))

    base_labels = [1 if item in base_data else 0 for item in total_data]
    data_comments.append(f"Base data size: {len(base_data)} ({int(len(base_data) / n * 100)}%) / Total: {n}")

    make_prc_plot(converted_data_list, base_labels, title="", show=False)
    plt.subplots_adjust(left=0.14, right=0.98, top=0.98, bottom=0.16)
    plt.gcf().set_size_inches(plt.gcf().get_figwidth() / 1.5, plt.gcf().get_figheight() / 1.5)
    # plt.text(0.5, -0.25, "\n".join(data_comments),
    #          horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    print("\n".join(data_comments))
    plt_save_show(filename)
    # make_roc_plot(converted_data_list, base_labels, title, show=False)
    # plt.text(0.5, 0.4, "\n".join(data_comments),
    #          horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    # plt.show()


def make_linear_regression_combination(data_list: List[PRC_DATA_ENTRY], base_data: Set[str], total_data: Set[str], merge_fn,
                                       initial_coefficients=None, initial_step_size=0.5) -> PRC_DATA_ENTRY:
    from sklearn.metrics import precision_recall_curve
    from sklearn.metrics import auc
    from itertools import product
    total_data_list = list(total_data)

    def get_of_data(x_var, entry):
        if isinstance(x_var, dict):
            return x_var.get(entry, 0)
        else:
            return 1 if entry in x_var else 0

    X = [[get_of_data(x_var, entry) for _name, x_var in data_list]
         for entry in total_data_list]
    Y = [1 if item in base_data else 0 for item in total_data_list]

    def normalize_coef(raw_coef):
        max_abs_value = max(abs(c) for c in raw_coef)
        return [c / max_abs_value for c in raw_coef]

    def predict(option):
        raw_probs = [merge_fn(coef_val * x_val for coef_val, x_val in zip(option, x_entry)) for x_entry in X]
        minimum, maximum = min(raw_probs), max(raw_probs)
        return [(prob - minimum) / (maximum - minimum) for prob in raw_probs]

    coef = normalize_coef([1 for _data in data_list])
    if initial_coefficients is not None:
        if len(initial_coefficients) != len(coef):
            raise Exception("Initial coefficients size does not match!")
        coef = normalize_coef(initial_coefficients)
    step_size = initial_step_size

    while step_size >= 0.001:
        # find all new possible coefficients
        all_options = [normalize_coef(option) for option in product(*[[c, c - step_size, c + step_size] for c in coef])]
        aucs = [auc(recall, precision) for precision, recall, _t in (precision_recall_curve(Y, predict(o)) for o in all_options)]
        print(f"{step_size:.6f}: {','.join(f'{c:.4f}' for c in coef)}, auc={aucs[0]}")
        if max(aucs) == aucs[0]:
            step_size /= 2  # no improvement here, lets decrease step size and repeat
        else:
            coef = all_options[aucs.index(max(aucs))]

    result: Dict[str, float] = dict()
    for name, prob in zip(total_data_list, predict(coef)):
        result[name] = prob
    names = [name for name, _x_var in data_list]
    new_name = ('+' if merge_fn == sum else ',').join([f'{coef:.2f}' + name for name, coef in zip(names, coef)])
    return new_name, result


@cachier()
def get_vd_best_combination(sum_instead_of_max: bool, _min_class_loc: int, _max_class_loc: int):
    global named_pattern_probs
    global ref_heuristic
    global total
    merge_fn = sum if sum_instead_of_max else max
    return make_linear_regression_combination(named_pattern_probs, ref_heuristic, total, merge_fn)


def get_view_disagreement_data(repo: LocalRepo) -> Set[str]:
    results: Set[str] = set()
    for p, n, d in TAXONOMY:
        results.update(find_violations_for_pattern(repo, p, "classes"))
        for m in find_violations_for_pattern(repo, p, "methods"):
            results.add(repo.get_tree().find_node(m).get_containing_class_node().get_path())
    return results


def get_bb_data(repo: LocalRepo) -> Set[str]:
    bb_context = BBContext.for_repo(repo)
    result: Set[str] = set()
    for disharmony in set(bb_context.find_all_disharmonies()):
        result.add(bb_context.get_containing_class_of(disharmony))
    return result


def get_view_disagreement_data_probabilities_max(repo: LocalRepo) -> Dict[str, float]:
    return merge_dicts(lambda a, b: max(a, b), *[find_violations_for_pattern_probabilities(repo, p, "classes") for p, *_ in TAXONOMY])


def get_view_disagreement_data_probabilities_sum(repo: LocalRepo) -> Dict[str, float]:
    merged = merge_dicts(lambda a, b: a + b, *[find_violations_for_pattern_probabilities(repo, p, "classes") for p, *_ in TAXONOMY])
    for key, val in merged.items():
        merged[key] = val / len(TAXONOMY)
    return merged


##############################


plt.rcParams['figure.dpi'] = 250


class_loc_ranges = [
    (0, math.inf),
    (0, 50),
    (50, 100),
    (100, 200),
    (200, 400),
    (400, math.inf),
]


repos_and_old_versions = [(new, old) for new, olds in repos_and_versions for old in olds]

for min_class_loc, max_class_loc in class_loc_ranges:
    total = set()
    bb = set()
    ref = set()
    vd_prob_max: Dict[str, float] = dict()
    vd_prob_sum: Dict[str, float] = dict()
    class_size_prob: Dict[str, float] = dict()
    pattern_probs: List[Dict[str, float]] = [dict() for _t in TAXONOMY]
    for i, (repo_name, old_version) in enumerate(repos_and_old_versions):
        new_r = LocalRepo.for_name(repo_name)
        old_r = new_r.get_old_version(old_version)

        total_list_r = [name for name in get_filtered_nodes(old_r, "classes") if min_class_loc <= old_r.get_tree().find_node(name).get_line_span() <= max_class_loc]
        total_r = set(total_list_r)
        total.update(f"{old_r.name}/{name}" for name in total_r)

        bb.update(f"{old_r.name}/{name}" for name in get_bb_data(old_r).intersection(total_r))
        ref.update(f"{old_r.name}/{name}" for name in get_classes_being_refactored_in_the_future(new_r, old_version, use_filter=True).intersection(total_r))

        vd_prob_max_r = get_view_disagreement_data_probabilities_max(old_r)
        for name in list(vd_prob_max_r.keys()):
            if name not in total_r:
                vd_prob_max_r.pop(name)
        vd_prob_max.update(dict((f"{old_r.name}/{name}", value) for name, value in vd_prob_max_r.items()))
        vd_prob_sum_r = get_view_disagreement_data_probabilities_sum(old_r)
        for name in list(vd_prob_sum_r.keys()):
            if name not in total_r:
                vd_prob_sum_r.pop(name)
        vd_prob_sum.update(dict((f"{old_r.name}/{name}", value) for name, value in vd_prob_sum_r.items()))
        for i, (p, *_) in enumerate(TAXONOMY):
            pattern_prob_r = find_violations_for_pattern_probabilities(old_r, p, "classes")
            for name in list(pattern_prob_r.keys()):
                if name not in total_r:
                    pattern_prob_r.pop(name)
            pattern_probs[i].update(dict((f"{old_r.name}/{name}", value) for name, value in pattern_prob_r.items()))

        class_size_prob.update(dict((f"{old_r.name}/{name}", old_r.get_tree().find_node(name).get_line_span() / 10000.0) for name in total_r))

    if len(ref) == 0:
        print("No refactorings found, continuing to next loop")
        continue

    # named_pattern_probs = [("".join(w[0].upper() for w in re.split(r"\W+", name)), probs) for probs, (p, name, *_) in zip(pattern_probs, TAXONOMY)]

    # best_combination_sum = get_vd_best_combination(True, min_class_loc, max_class_loc)
    # best_combination_max = get_vd_best_combination(False, min_class_loc, max_class_loc)
    if (min_class_loc, max_class_loc) == (0, math.inf):
        make_prc_plot_for([
            ("LOC", class_size_prob),
            ("VD", vd_prob_max),
            # ("VDSum", vd_prob_sum),
            ("LM", bb),
        ], ref, total, "vd_ref_all")
    else:
        make_prc_plot_for([
            ("LOC", class_size_prob),
            ("VD", vd_prob_max),
            # ("VDSum", vd_prob_sum),
            ("LM", bb),
        ], ref, total, f"vd_ref_{min_class_loc}_{max_class_loc}")
