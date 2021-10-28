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


def make_alignment_table_with(repo: LocalRepo, name: str, data: Set[str], title: str):
    vd: Set[str] = set()
    for p, n, d in TAXONOMY:
        vd.update(find_violations_for_pattern(repo, p, "classes"))
        for m in find_violations_for_pattern(repo, p, "methods"):
            vd.add(repo.get_tree().find_node(m).get_containing_class_node().get_path())

    total = set(get_filtered_nodes(repo, "classes"))
    not_data = total.difference(data)
    not_vd = total.difference(vd)

    columns = (f" {name} ", f" -{name} ", " Total ")
    rows = (" VD ", " -VD ", " Total ")

    def fmt(a: Set[str], b: Set[str] = None) -> str:
        if b is None:
            return str(len(a))
        intersection = len(a.intersection(b))
        return f"{int(intersection / float(len(a) + len(b) - intersection) * 100)}%\n({intersection})"

    cell_text = [
        [fmt(vd, data), fmt(vd, not_data), fmt(vd)],
        [fmt(not_vd, data), fmt(not_vd, not_data), fmt(not_vd)],
        [fmt(data), fmt(not_data), fmt(total)]
    ]

    plt.axis('tight')
    plt.axis('off')
    table = plt.table(cellText=cell_text, colLabels=columns, rowLabels=rows, loc='center', cellLoc="center")
    table.scale(0.5, 3.5)
    plt.title(f"{repo.name}: {title}")
    accuracy = (len(vd.intersection(data)) + len(not_vd.intersection(not_data))) / float(len(total))
    super_balanced_accuracy = (  # https://en.wikipedia.org/wiki/Precision_and_recall#Imbalanced_data
                                      (len(vd.intersection(data)) / len(vd)) +
                                      (len(vd.intersection(data)) / len(data)) +
                                      (len(not_vd.intersection(not_data)) / len(not_vd)) +
                                      (len(not_vd.intersection(not_data)) / len(not_data))
                              ) / 4.0
    plt.text(0.5, 0.1, f"Accuracy: {int(accuracy * 100)}%, balanced: {int(super_balanced_accuracy * 100)}%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    plt.show()


def make_aggregated_bb_alignment_table(repo: LocalRepo):
    bb_context = BBContext.for_repo(repo)
    bb: Set[str] = set()
    for disharmony in bb_context.find_all_disharmonies():
        bb.add(bb_context.get_containing_class_of(disharmony))

    make_alignment_table_with(repo, "BB", bb, "Own disharmonies vs Blue Book")


def make_aggregated_ref_alignment_table(repo: LocalRepo, old_version: str):
    make_alignment_table_with(repo, "Ref", get_classes_being_refactored_in_the_future(repo, old_version), "Own disharmonies vs Future Refactorings")


plt.rcParams['figure.dpi'] = 300


def preprocess(repo_name: str):
    repo = LocalRepo(repo_name)
    all_patterns = [p for p, n, d in TAXONOMY]
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "classes")
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "methods")


#for repo_name in repos:
#    preprocess(repo_name)

for repo_name in repos:
    r = LocalRepo(repo_name)
    make_individual_bb_alignment_table(r)
    make_aggregated_bb_alignment_table(r)


for repo_name, old_version in [
    ("jfree/jfreechart:v1.5.3", "v1.5.0"),
]:
    r = LocalRepo(repo_name)
    make_aggregated_ref_alignment_table(r, old_version)

