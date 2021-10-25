from typing import *
from local_repo import LocalRepo
from analysis import analyze_disagreements, ALL_VIEWS
from best_results_set import BestResultsSet, BRS_DATA_TYPE
from study_common import TAXONOMY, make_sort_weights

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
    errors = result[1][2]
    return sum(x * x for x in errors)


def get_found_violations(r: LocalRepo):
    all_results: List[BestResultsSet] = analyze_disagreements(r, ALL_VIEWS, [p + [n + " - " + d] for p, n, d in TAXONOMY], "methods")
    merged_results = []
    for taxonomy_entry, results in zip(TAXONOMY, all_results):
        for result in results.get_best(make_sort_weights(taxonomy_entry[0])):
            merged_results.append([result, match_score(result)])
    merged_results.sort(key=lambda elem: elem[1])
    violations_dict = dict()
    for result, score in merged_results:
        if score <= 0.5:
            a, b, *_ = result[1]
            if a not in violations_dict:
                violations_dict[a] = set()
            violations_dict[a].add(b)
    return violations_dict


for repo in repos:
    r = LocalRepo(repo)
    r.update()
    print(str(len(r.get_all_commits())) + " known commits, " + str(len(r.get_future_commits())) + " yet to come.")
    merged_violations = get_found_violations(r)
