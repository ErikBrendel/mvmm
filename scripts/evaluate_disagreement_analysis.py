import statistics

import pyfiglet

from custom_types import *
from local_repo import LocalRepo
from analysis import analyze_disagreements, ALL_VIEWS, get_filtered_nodes
from best_results_set import BestResultsSet, BRS_DATA_TYPE
from blue_book_metrics import BB_METRICS, BBContext
from util import map_parallel, merge_dicts
from prc_auc import make_prc_plot, PRC_PLOT_DATA_ENTRY, make_roc_plot
from study_common import TAXONOMY, make_sort_weights
import matplotlib.pyplot as plt
from refactorings_detection import get_classes_being_refactored_in_the_future, get_classes_being_refactored_in_the_future_heuristically_filtered

repos = [
    'ErikBrendel/LudumDare',
    'ErikBrendel/LD35',
    "junit-team/junit4",
    "vanzin/jEdit",
    # "jfree/jfreechart:5ca5d26bb38bafead25f81e88e0938a5d042c2a4",  # May 15
    # "jfree/jfreechart:9020a32e62800916f1897c3eb17c95bf0371230b",  # Mar 7
    # "jfree/jfreechart:99d999395e46f8cf8689724853c9ede89be7c7ea",  # Mar 1
    # "jfree/jfreechart:fc4ddeed916c4cfd6479bf7378c6cdb94f6a19fe",  # Feb 6
    # "jfree/jfreechart:461625fd1f7242a1223f8e73716e9f2b4e9fd8a5",  # Dez 19, 2020
    "jfree/jfreechart",
    # "jfree/jfreechart:v1.5.3",
    # "jfree/jfreechart:v1.5.2",
    # "jfree/jfreechart:v1.5.1",
    # "jfree/jfreechart:v1.5.0",
    # "jfree/jfreechart:v1.0.19",

    "jOOQ/jOOQ",
    "wumpz/jhotdraw",
    # "neuland/jade4j",
    "apache/log4j",
    # "hunterhacker/jdom",
    "jenkinsci/jenkins",
    "brettwooldridge/HikariCP",
    # "adamfisk/LittleProxy",
    # "dynjs/dynjs",
    "SonarSource/sonarqube",
    "eclipse/aspectj.eclipse.jdt.core",
]


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
                results[clazz] = score
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


def make_prc_plot_for(data_list: List[PRC_DATA_ENTRY], base_data: Set[str], total_data: Set[str], title: str):
    data_comments: List[str] = []
    converted_data_list: List[PRC_PLOT_DATA_ENTRY] = []

    n = len(total_data)

    for name, original_data in data_list:
        converted_data: Union[List[float], List[int]]
        if isinstance(original_data, dict):
            converted_data = [1 - original_data.get(item, 1) for item in total_data]
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

    make_prc_plot(converted_data_list, base_labels, title, show=False)
    plt.text(0.5, 0.2, "\n".join(data_comments),
             horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    plt.show()
    make_roc_plot(converted_data_list, base_labels, title, show=False)
    plt.text(0.5, 0.2, "\n".join(data_comments),
             horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    plt.show()



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
    for disharmony in bb_context.find_all_disharmonies():
        result.add(bb_context.get_containing_class_of(disharmony))
    return result


def get_view_disagreement_data_probabilities(repo: LocalRepo) -> Dict[str, float]:
    return merge_dicts(lambda a, b: max(a, b), *[find_violations_for_pattern_probabilities(repo, p, "classes") for p, *_ in TAXONOMY])


##############################


plt.rcParams['figure.dpi'] = 150


def preprocess(repo_name: str):
    repo = LocalRepo(repo_name)
    all_patterns = [p for p, n, d in TAXONOMY]
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "classes")
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "methods")


#for repo_name in repos:
#    preprocess(repo_name)

#for repo_name in repos:
#    r = LocalRepo(repo_name)
#    make_individual_bb_alignment_table(r)


repos_and_old_versions = [
    # ("jfree/jfreechart:v1.5.3", "v1.0.18"),
    # ("jfree/jfreechart:v1.5.3", "v1.5.0"),
    # ("junit-team/junit4:r4.13.2", "r4.6"),
    # ("apache/logging-log4j2:rel/2.14.1", "rel/2.11.2"),
    # ("apache/logging-log4j2:rel/2.14.1", "rel/2.8"),
    # ("apache/logging-log4j2:rel/2.14.1", "rel/2.4"),
    # ("apache/logging-log4j2:rel/2.14.1", "rel/2.1"),
    # ("apache/logging-log4j2:rel/2.14.1", "rel/2.0"),
] + [("apache/hadoop:release-0.15.0", f"release-0.{v}.0") for v in range(1, 15)]
for repo_name, old_version in repos_and_old_versions:
    r = LocalRepo(repo_name)
    old_r = r.get_old_version(old_version)
    preprocess(old_r.name)

    vd = get_view_disagreement_data(old_r)
    bb = get_bb_data(old_r)
    ref = get_classes_being_refactored_in_the_future(r, old_version, False)
    ref_verified = get_classes_being_refactored_in_the_future(r, old_version, True)
    ref_heuristic = get_classes_being_refactored_in_the_future_heuristically_filtered(r, old_version)
    total_list = get_filtered_nodes(r, "classes")
    total = set(total_list)

    # make_alignment_table("VD", vd, "REFa", ref, total,
    #                      f"{old_r.name}\n View Disagreement Reports vs All Automatically Detected Refactorings")
    # make_alignment_table("VD", vd, "REFh", ref_heuristic, total,
    #                      f"{old_r.name}\n View Disagreement Reports vs Heuristically Filtered Refactorings")
    # make_alignment_table("VD", vd, "REFv", ref_verified, total,
    #                      f"{old_r.name}\n View Disagreement Reports vs Manually Verified Refactorings")
    # make_alignment_table("BB", bb, "REFa", ref, total,
    #                      f"{old_r.name}\n Blue Book Disharmonies vs All Automatically Detected Refactorings")
    # make_alignment_table("BB", bb, "REFh", ref_heuristic, total,
    #                      f"{old_r.name}\n Blue Book Disharmonies vs Heuristically Filtered Refactorings")
    # make_alignment_table("BB", bb, "REFv", ref_verified, total,
    #                      f"{old_r.name}\n Blue Book Disharmonies vs Manually Verified Refactorings")
    # make_alignment_table("VD", vd, "BB", bb, total,
    #                      f"{old_r.name}\n View Disagreement Reports vs Blue Book Disharmonies")
    # make_individual_bb_alignment_table(old_r)
    vd_prob = get_view_disagreement_data_probabilities(old_r)
    # make_prc_plot_for([("VD", vd_prob), ("BB", bb)], ref, total, f"{old_r.name}\nPrecision-Recall Plot of View Disagreements predicting all refactorings")
    make_prc_plot_for([("VD", vd_prob), ("BB", bb)], ref_heuristic, total, f"{old_r.name}\nPrecision-Recall Plot of View Disagreements heuristically filtered refactorings")
    # make_prc_plot_for("VD", vd_prob, bb, total, "Precision-Recall Plot of View Disagreements predicting BB")



