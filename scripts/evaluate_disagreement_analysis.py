import pyfiglet

from custom_types import *
from local_repo import LocalRepo
from analysis import analyze_disagreements, ALL_VIEWS, get_filtered_nodes
from best_results_set import BestResultsSet, BRS_DATA_TYPE
from blue_book_metrics import BB_METRICS, BBContext
from util import map_parallel
from study_common import TAXONOMY, make_sort_weights
import matplotlib.pyplot as plt
from refactorings_detection import get_classes_being_refactored_in_the_future

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
    return sum(x * x for x in errors)


def find_violations_for_pattern(repo: LocalRepo, pattern: PatternType, filter_mode: NodeFilterMode) -> List[str]:
    raw_results = analyze_disagreements(repo, ALL_VIEWS, [pattern], filter_mode)[0]
    results: Set[str] = set()
    for result in raw_results.get_best(make_sort_weights(pattern)):
        score = match_score(result)
        if score <= 0.5:
            a, b, *_ = result[1]
            results.add(a)
            results.add(b)
    return list(results)


def find_violations_bb(repo: LocalRepo, bb_metric: str) -> List[str]:
    return BBContext.for_repo(repo).find_by_name(bb_metric)


def evaluate_metric_alignment(repo: LocalRepo, pattern: PatternType, bb_metric: str, filter_mode: NodeFilterMode) -> float:
    own_results = set(find_violations_for_pattern(repo, pattern, filter_mode))
    bb_results = set(find_violations_bb(repo, bb_metric))
    intersection_size = len(own_results.intersection(bb_results))
    union_size = len(own_results) + len(bb_results) - intersection_size
    if union_size == 0:
        return -0.01
    return intersection_size / float(union_size)


def make_individual_bb_alignment_table(repo: LocalRepo):
    sm = plt.cm.ScalarMappable(cmap=None, norm=plt.Normalize(vmin=0, vmax=1))
    columns = tuple(f"{''.join(w[0].upper() for w in m.split('_'))}: {len(find_violations_bb(repo, m))}" for m, _f in BB_METRICS)
    rows = tuple(f"{''.join([str(e) if e is not None else '*' for e in p])}: {len(find_violations_for_pattern(repo, p, 'methods'))} / {len(find_violations_for_pattern(repo, p, 'classes'))}" for p, _n, _d in TAXONOMY)

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
    plt.title(repo.name)
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


plt.rcParams['figure.dpi'] = 300


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


for repo_name, old_version in [
    # ("jfree/jfreechart:v1.5.3", "v1.5.0"),
    ("junit-team/junit4:r4.13.2", "r4.6"),
    #("junit-team/junit4", ?) # https://github.com/junit-team/junit4/tags
    #("apache/log4j", ?) # https://github.com/apache/log4j/tags
]:
    r = LocalRepo(repo_name)
    old_r = r.get_old_version(old_version)
    preprocess(r.name)
    preprocess(old_r.name)

    vd = get_view_disagreement_data(old_r)
    bb = get_bb_data(old_r)
    ref = get_classes_being_refactored_in_the_future(r, old_version, False)
    ref_verified = get_classes_being_refactored_in_the_future(r, old_version, True)
    total = set(get_filtered_nodes(r, "classes"))

    make_alignment_table("VD", vd, "REFa", ref, total,
                         f"{old_r.name}: View Disagreement Reports vs All Automatically Detected Refactorings")
    make_alignment_table("VD", vd, "REFv", ref_verified, total,
                         f"{old_r.name}: View Disagreement Reports vs Manually Verified Refactorings")
    make_alignment_table("BB", bb, "REFa", ref, total,
                         f"{old_r.name}: Blue Book Disharmonies vs All Automatically Detected Refactorings")
    make_alignment_table("BB", bb, "REFv", ref_verified, total,
                         f"{old_r.name}: Blue Book Disharmonies vs Manually Verified Refactorings")
    make_alignment_table("VD", vd, "BB", bb, total,
                         f"{old_r.name}: View Disagreement Reports vs Blue Book Disharmonies")


