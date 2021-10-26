from custom_types import *
from local_repo import LocalRepo
from analysis import analyze_disagreements, ALL_VIEWS
from best_results_set import BestResultsSet, BRS_DATA_TYPE
from blue_book_metrics import BB_METRICS, BBContext
from study_common import TAXONOMY, make_sort_weights
import matplotlib.pyplot as plt

repos = [
    # "jfree/jfreechart:5ca5d26bb38bafead25f81e88e0938a5d042c2a4",  # May 15
    # "jfree/jfreechart:9020a32e62800916f1897c3eb17c95bf0371230b",  # Mar 7
    # "jfree/jfreechart:99d999395e46f8cf8689724853c9ede89be7c7ea",  # Mar 1
    # "jfree/jfreechart:fc4ddeed916c4cfd6479bf7378c6cdb94f6a19fe",  # Feb 6
    # "jfree/jfreechart:461625fd1f7242a1223f8e73716e9f2b4e9fd8a5",  # Dez 19, 2020
    # "jfree/jfreechart",
    # "jfree/jfreechart:v1.5.3",
    # "jfree/jfreechart:v1.5.2",
    "jfree/jfreechart:v1.5.1",
    # "jfree/jfreechart:v1.5.0",
    # "jfree/jfreechart:v1.0.19",
]


def match_score(result: BRS_DATA_TYPE):
    errors = result[0]
    return sum(x * x for x in errors)


def get_found_violations(repo: LocalRepo):
    all_results: List[BestResultsSet] = analyze_disagreements(repo, ALL_VIEWS, [p + [n + " - " + d] for p, n, d in TAXONOMY], "methods")
    violations_dict = dict()
    for ti, [taxonomy_entry, results] in enumerate(zip(TAXONOMY, all_results)):
        print("######## " + str(ti))
        for result in results.get_best(make_sort_weights(taxonomy_entry[0])):
            score = match_score(result)
            print(score)
            if score <= 0.5:
                a, b, *_ = result[1]
                if a not in violations_dict:
                    violations_dict[a] = set()
                violations_dict[a].add(b)
    return violations_dict


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


plt.rcParams['figure.dpi'] = 300

for repo_name in repos:
    r = LocalRepo(repo_name)
    # r.update()
    print(str(len(r.get_all_commits())) + " known commits, " + str(len(r.get_future_commits())) + " yet to come.")
    # merged_violations = get_found_violations(r)

    sm = plt.cm.ScalarMappable(cmap=None, norm=plt.Normalize(vmin=0, vmax=1))

    columns = tuple(f"{''.join(w[0].upper() for w in m.split('_'))}: {len(find_violations_bb(r, m))}" for m, _f in BB_METRICS)
    rows = tuple(f"{''.join([str(e) if e is not None else '*' for e in p])}: {len(find_violations_for_pattern(r, p, 'methods'))} / {len(find_violations_for_pattern(r, p, 'classes'))}" for p, _n, _d in TAXONOMY)

    values = [[evaluate_metric_alignment(r, p, m, f) for m, f in BB_METRICS] for p, _n, _d in TAXONOMY]
    colors = [[sm.to_rgba(cell) for cell in data] for data in values]
    cellText = [[f"{int(cell * 100)}%" for cell in data] for data in values]

    plt.axis('tight')
    plt.axis('off')
    table = plt.table(cellText=cellText, cellColours=colors, colLabels=columns, rowLabels=rows, loc='center', cellLoc="center")
    table.scale(0.7, 1.5)
    for ri, row_values in enumerate(values):
        for ci, cell_value in enumerate(row_values):
            if cell_value < 0.4:
                # the header row is row 0. The header column is column -1
                table[ri + 1, ci].get_text().set_color("white")
    plt.colorbar(sm)
    plt.show()
