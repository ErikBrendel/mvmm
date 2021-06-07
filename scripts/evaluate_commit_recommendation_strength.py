from local_repo import LocalRepo
from metrics import MetricManager
from metrics_evolutionary import get_commit_diff
from graph import WeightCombinedGraph, ResultCachedGraph
from util import log_progress, generate_one_distributions

repos = [
    "ErikBrendel/LudumDare:e77400a84a77c0cf8cf8aea128b78c5c9c8ad81e",  # earlier
    "ErikBrendel/LudumDare:d2701514c871f5efa3ae5c9766c0a887c1f12252",  # later
]

metrics = ["structural", "evolutionary", "linguistic", "module_distance"]

for repo in repos:
    r = LocalRepo(repo)
    r.update()
    print(str(len(r.get_all_commits())) + " known commits, " + str(len(r.get_future_commits())) + " yet to come.")
    metric_graphs = [ResultCachedGraph(MetricManager.get(r, m)) for m in metrics]
    for g in metric_graphs:
        g.print_statistics()

    def node_filter(tree_node):
        return tree_node is not None and tree_node.get_type() == "method" and tree_node.get_line_span() >= 1

    all_nodes = sorted([tree_node.get_path() for tree_node in r.get_tree().traverse_gen() if node_filter(tree_node)])

    prediction_tests: list[tuple[str, list[str]]] = []

    future_commit_diffs = [get_commit_diff(ch, r) for ch in r.get_future_commits()]
    future_commit_diffs = [[path for path in diff if node_filter(r.get_tree().find_node(path))] for diff in future_commit_diffs if diff is not None]
    commits_to_evaluate = [diffs for diffs in future_commit_diffs if len(diffs) > 1]
    for commit_to_evaluate in log_progress(commits_to_evaluate, desc="Constructing evaluation data set"):
        for i, method_to_predict in enumerate(commit_to_evaluate):
            other_methods: list[str] = commit_to_evaluate[:i] + commit_to_evaluate[i + 1:]
            prediction_tests.append((method_to_predict, other_methods))

    results = []
    weight_combinations = list(generate_one_distributions(len(metrics), 8))
    for weights in log_progress(weight_combinations, desc="Evaluating view weight combinations"):
        scores = []
        for missing, others in prediction_tests:
            scores.append(WeightCombinedGraph(metric_graphs, weights).how_well_predicts_missing_node(others, missing, all_nodes))
        score = sum(scores) / len(scores)
        results.append((", ".join(str(w) for w in weights), score))

    results.sort(key=lambda e: e[1])
    for r in results:
        print(r[0] + ", " + str(r[1]))

    print("nice")

