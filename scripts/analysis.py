import pdb
from best_results_set import BestResultsSet

from local_repo import *
from metrics import *


def pattern_match(coupling_values, pattern, support_values):
    """how good does this node-pair fit to the given pattern? Range: [0, 1]"""
    error_sum = 0
    values = 0
    support = 1
    for i, coupling_val in enumerate(coupling_values):
        if pattern[i] is not None:
            error = abs(pattern[i] - coupling_val)
            error_sum += error * error
            values += 1
            support = min(support, support_values[i])
    match_score = 1. - (error_sum / values)
    return match_score, support


# as seen in:
# https://thelaziestprogrammer.com/python/a-multiprocessing-pool-pickle
# https://thelaziestprogrammer.com/python/multiprocessing-pool-a-global-solution
class StaticStuff:
    analysis_graphs = None
    target_patterns = None


MIN_PATTERN_MATCH = 0  # how close the coupling values need to match the pattern to be a result
MIN_SUPPORT = 0  # how much relative support a result needs to not be discarded


def analyze_pair(pair):  # , analysis_graphs, target_patterns):
    # pdb.set_trace()
    _a, _b = pair
    if _a.startswith(_b) or _b.startswith(_a):  # ignore nodes that are in a parent-child relation
        return None
    # for each view: how much support do we have for this node pair (minimum of both node support values)
    support_values = [min(supp_a, supp_b) for supp_a, supp_b in zip(*[
        [g.get_normalized_support(node) for g in StaticStuff.analysis_graphs] for node in [_a, _b]
    ])]
    result = [[] for p in StaticStuff.target_patterns]
    for a, b in [(_a, _b), (_b, _a)]:
        normalized_coupling_values = tuple([g.get_normalized_coupling(a, b) for g in StaticStuff.analysis_graphs])
        for i, pattern in enumerate(StaticStuff.target_patterns):
            pattern_match_score_data = tuple(abs(p - v) for p, v in zip(pattern, normalized_coupling_values) if p is not None)
            match_score, support = pattern_match(normalized_coupling_values, pattern, support_values)
            if match_score >= MIN_PATTERN_MATCH and support >= MIN_SUPPORT:
                result[i].append(((*pattern_match_score_data, -support), (a, b, (*normalized_coupling_values, support))))
    return result


SHOW_RESULTS_SIZE = 50


def analyze_disagreements(repo, views, target_patterns, node_filter_func=None, node_pair_filter_func=None):
    """
    when views are [struct, evo, ling], the pattern [0, 1, None, "comment"] searches for nodes that are
    strongly coupled evolutionary, loosely coupled structurally, and the language does not matter
    """
    if len(views) < 1:
        return
    if not all([len(p) >= len(views) for p in target_patterns]):
        print("Patterns need at least one element per graph!")
        return

    analysis_graphs = list([MetricManager.get(repo, g) for g in views])
    # for g in analysis_graphs:
    #    g.propagate_down(2, 0.2)
    analysis_graph_nodes = [g.get_node_set() for g in analysis_graphs]
    intersection_nodes = list(set.intersection(*[nodes for nodes in analysis_graph_nodes if nodes is not None]))
    intersection_nodes = [n for n in intersection_nodes if repo.get_tree().has_node(n)]

    union_nodes = list(set.union(*[nodes for nodes in analysis_graph_nodes if nodes is not None]))
    union_nodes = set([n for n in union_nodes if repo.get_tree().has_node(n)])
    print("Intersection Nodes: " + str(len(intersection_nodes)) + ", Union Nodes: " + str(len(union_nodes)))
    for view, graph in zip(views, analysis_graphs):
        graph_nodes = graph.get_node_set()
        if graph_nodes is None:
            continue
        graph_nodes = set([n for n in graph_nodes if repo.get_tree().has_node(n)])
        in_view_not_intersection = list(graph_nodes.difference(set(intersection_nodes)))
        in_union_not_view = list(union_nodes.difference(graph_nodes))
        print("  View '" + view + "': " + str(len(graph_nodes)) + " Nodes in total")
        if len(in_view_not_intersection) > 0:
            print("    In view but not intersection: " + str(len(in_view_not_intersection)))
            for path in in_view_not_intersection[:5]:
                print("      " + repo.url_for(path) + " " + path.split("/")[-1])
        if len(in_union_not_view) > 0:
            print("    In union but not view: " + str(len(in_union_not_view)))
            for path in in_union_not_view[:5]:
                print("      " + repo.url_for(path) + " " + path.split("/")[-1])

    all_nodes = intersection_nodes
    print("Total node count:", len(all_nodes))
    print("Methods:", sum(repo.get_tree().find_node(path).get_type() == "method" for path in all_nodes))
    print("constructors:", sum(repo.get_tree().find_node(path).get_type() == "constructor" for path in all_nodes))
    print("fields:", sum(repo.get_tree().find_node(path).get_type() == "field" for path in all_nodes))
    print("classes:", sum(repo.get_tree().find_node(path).get_type() == "class" for path in all_nodes))
    print("interfaces:", sum(repo.get_tree().find_node(path).get_type() == "interface" for path in all_nodes))
    print("enums:", sum(repo.get_tree().find_node(path).get_type() == "enum" for path in all_nodes))
    print("without type:", sum(repo.get_tree().find_node(path).get_type() is None for path in all_nodes))
    if node_filter_func is not None:
        all_nodes = [node for node in all_nodes if node_filter_func(node)]
    print("all filtered nodes:", len(all_nodes))

    all_node_pairs = list(all_pairs(all_nodes))
    if node_pair_filter_func is not None:
        prev_len = len(all_node_pairs)
        all_node_pairs = [pair for pair in all_node_pairs if node_pair_filter_func(pair[0], pair[1])]
        if len(all_node_pairs) == 0:
            print("NO NODES TO ANALYZE, ABORTING!")
            return
        print("Amount of node pairs to check:", len(all_node_pairs), "of", prev_len, "(" + str(len(all_node_pairs) / prev_len * 100) + "%)")

    # all_node_pairs = all_node_pairs[:1000]

    print("Going parallel...")
    pattern_results = [
        BestResultsSet(sum(type(x) == int for x in p) + 1, SHOW_RESULTS_SIZE)  # one dim for each graph that is used in the pattern + 1 for support
        for p in target_patterns]

    def handle_results(pattern_results_part):
        for i, part in enumerate(pattern_results_part):
            pattern_results[i].add_all(part)

    StaticStuff.analysis_graphs = analysis_graphs
    StaticStuff.target_patterns = target_patterns
    map_parallel(
        all_node_pairs,
        analyze_pair,  # partial(analyze_pair, analysis_graphs=analysis_graphs, target_patterns=target_patterns),
        handle_results,
        "Analyzing edges",
        force_non_parallel=True
    )

    print("Results:")
    for i, (pattern, results) in enumerate(zip(target_patterns, pattern_results)):
        print("\nPattern " + str(i) + " (" + str(pattern) + "):")

        def nice_path(path):
            ending = "." + repo.type_extension()
            if ending in path:
                return path[path.index(ending) + len(ending) + 1:]
            return path

        def get_raw_i(i):
            def getter(d):
                return d[1][2][i]

            return getter

        def get_i(i):
            def getter(d):
                return d[0][i]

            return getter

        name_and_raw_getters = [(name, get_raw_i(i)) for i, name in enumerate(views) if pattern[i] is not None] + [("support", get_raw_i(-1))]
        sort_val_getters = [get_i(i) for i in range(len([p for p in pattern if p is not None]))] + [(get_i(-1))]
        dimensions = [(name, get, get_raw) for (name, get_raw), get in zip(name_and_raw_getters, sort_val_getters)]

        def make_show_data(dim):
            def show_data(multi_sorted_results):
                print(results.total_amount, "raw results,", len(multi_sorted_results), "final results")

                display_data = multi_sorted_results[:SHOW_RESULTS_SIZE]
                # for d in display_data:
                #    print(d)
                display_data = [
                    ["{:1.4f}".format(raw_getter(datum)) for name, getter, raw_getter in dim] +
                    ['<a target="_blank" href="' + repo.url_for(path) + '" title="' + path + '">' + nice_path(path) + '</a>' for path in datum[1][0:2]]
                    for datum in display_data]
                header = [name for name, *_ in dim] + ["support", "method 1", "method 2"]
                show_html_table([header] + display_data, len(dim) + 2)

            return show_data

        # results.trim()
        interactive_multi_sort(results.data, dimensions, make_show_data(dimensions))

        # pdb.set_trace()
    # TODO trim node set of nodes to those they have in common?
