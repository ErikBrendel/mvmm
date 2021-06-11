import pdb
import random
import sys
import threading
import json

from best_results_set import BestResultsSet

from custom_types import *
from local_repo import *
from metrics import *


MIN_SUPPORT = 0  # how much relative support a result needs to not be discarded


def analyze_pair(pair, analysis_graphs, target_patterns: PatternsType) -> Optional[PairAnalysisResultsType]:
    # pdb.set_trace()
    _a, _b = pair
    if _a.startswith(_b) or _b.startswith(_a):  # ignore nodes that are in a parent-child relation
        return None
    # for each view: how much support do we have for this node pair (minimum of both node support values)
    support_values = [min(supp_a, supp_b) for supp_a, supp_b in zip(*[
        [g.get_normalized_support(node) for g in analysis_graphs] for node in [_a, _b]
    ])]
    results: List[List[AnalysisResultType]] = [[] for p in target_patterns]
    for a, b in [(_a, _b), (_b, _a)]:
        normalized_coupling_values = tuple(g.get_normalized_coupling(a, b) for g in analysis_graphs)
        for i, pattern in enumerate(target_patterns):
            pattern_match_score_data = tuple(abs(p - v) for p, v in zip(pattern, normalized_coupling_values) if p is not None)
            support = min(support for i, support in enumerate(support_values) if pattern[i] is not None)
            if support >= MIN_SUPPORT:
                results[i].append(((*pattern_match_score_data, -support), (a, b, (*normalized_coupling_values, support))))
    return results


SHOW_RESULTS_SIZE = 50
USE_NODE_UNION = False  # or intersection instead?


def analyze_disagreements(repo: LocalRepo, views: List[str], target_patterns: PatternsType, node_filter_func=None, parallel=True, ignore_previous_results=False) -> Optional[List[BestResultsSet]]:
    """
    when views are [struct, evo, ling], the pattern [0, 1, None, "comment"] searches for nodes that are
    strongly coupled evolutionary, loosely coupled structurally, and the language does not matter
    """
    if len(views) < 1:
        return
    if not all([len(p) >= len(views) for p in target_patterns]):
        print("Patterns need at least one element per graph!")
        return

    result_sets: List[Optional[BestResultsSet]] = [None for p in target_patterns]
    if not ignore_previous_results:
        for i, pattern in enumerate(target_patterns):
            result = BestResultsSet.load(BestResultsSet.get_name(repo.name, views, pattern))
            if result is not None:
                result_sets[i] = result

    if all(r is not None for r in result_sets):
        return result_sets

    analysis_graphs = list([MetricManager.get(repo, g) for g in views])
    analysis_graph_nodes = [g.get_node_set() for g in analysis_graphs]
    intersection_nodes = list(set.intersection(*[nodes for nodes in analysis_graph_nodes if nodes is not None]))
    intersection_nodes = [n for n in intersection_nodes if repo.get_tree().has_node(n)]

    union_nodes = list(set.union(*[nodes for nodes in analysis_graph_nodes if nodes is not None]))
    union_nodes = set([n for n in union_nodes if repo.get_tree().has_node(n)])
    # TODO use get_graph_node_set_combination instead
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

    all_nodes = union_nodes if USE_NODE_UNION else intersection_nodes
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

    required_patterns = [p for p, r in zip(target_patterns, result_sets) if r is None]
    calculated_results: List[BestResultsSet]
    if parallel:
        calculated_results = find_disagreement_results_parallel(repo, views, required_patterns, all_nodes)
    else:
        calculated_results = find_disagreement_results_serial(analysis_graphs, required_patterns, all_nodes)

    # TODO do this in parallel as well once all the part results came in!
    for r in log_progress(calculated_results, desc="Trimming merged result sets"):
        r.trim()
    print("Done")

    fill_none_with_other(result_sets, calculated_results)
    for r, p in zip(result_sets, target_patterns):
        r.export(BestResultsSet.get_name(repo.name, views, p))
    return result_sets


def find_disagreement_results_serial(analysis_graphs, target_patterns: PatternsType, all_nodes: List[str]) -> List[BestResultsSet]:
    all_node_pairs = list(all_pairs(all_nodes))

    # all_node_pairs = all_node_pairs[:1000]

    print("Going single-threaded...")
    pattern_results = [
        BestResultsSet(sum(type(x) == int for x in p) + 1, SHOW_RESULTS_SIZE)  # one dim for each graph that is used in the pattern + 1 for support
        for p in target_patterns]

    def handle_results(pattern_results_part):
        for i, part in enumerate(pattern_results_part):
            pattern_results[i].add_all(part)

    map_parallel(
        all_node_pairs,
        partial(analyze_pair, analysis_graphs=analysis_graphs, target_patterns=target_patterns),
        handle_results,
        "Analyzing edges",
        force_non_parallel=True
    )
    return pattern_results


def find_disagreement_results_parallel(repo, views, target_patterns: PatternsType, all_nodes: List[str]) -> List[BestResultsSet]:
    random.shuffle(all_nodes)
    thread_count = 120
    batch_size_pairs = 1000
    batch_size = int(math.ceil(min(max(1.0, batch_size_pairs / len(all_nodes)), 10)))
    jobs = [(start, min(start + batch_size, len(all_nodes))) for start in range(0, len(all_nodes), batch_size)]
    random.shuffle(jobs)
    thread_count = min(thread_count, len(jobs))
    print("Parallel analysis with " + str(thread_count) + " threads, batch size " + str(batch_size) + ", resulting in " + str(len(jobs)) + " jobs to handle " + str(len(all_nodes)) + " nodes.")
    worker_script = os.path.join(os.path.dirname(__file__), "analysis_worker.py")

    threads_ready_bar = log_progress(total=thread_count, desc="Starting parallel analysis workers")
    jobs_given_bar = log_progress(total=len(jobs), desc="Analyzing module pairs")
    results_received_bar = log_progress(total=thread_count*len(target_patterns), desc="Collecting results from parallel workers")

    workers = [
        subprocess.Popen([sys.executable, worker_script, repo.name, json.dumps(views), json.dumps(target_patterns)], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        for i in range(thread_count)]
    for w in workers:
        w.stdin.write((str(len(all_nodes)) + "\n").encode("utf-8"))
    for node in all_nodes:
        for w in workers:
            w.stdin.write((node + "\n").encode("utf-8"))
    for w in workers:
        w.stdin.flush()

    pattern_results = [
        BestResultsSet(sum(type(x) == int for x in p) + 1, SHOW_RESULTS_SIZE)  # one dim for each graph that is used in the pattern + 1 for support
        for p in target_patterns]

    def process_interaction(worker: subprocess.Popen):
        while True:
            line = worker.stdout.readline().decode("utf-8").rstrip()
            if not line:
                pdb.set_trace()
                continue
            if line == "Q":
                break
            elif line == "R":
                threads_ready_bar.update()
                if threads_ready_bar.n >= threads_ready_bar.total:
                    threads_ready_bar.close()
                line = "M"
            if line == "M":  # process wants more jobs
                if len(jobs) > 0:
                    job = jobs.pop()
                    worker.stdin.write(("J " + str(job[0]) + "," + str(job[1]) + "\n").encode("utf-8"))
                    worker.stdin.flush()
                    jobs_given_bar.update()
                else:
                    try:
                        worker.stdin.write("D\n".encode("utf-8"))  # Done with jobs, please give results now
                        worker.stdin.flush()
                        worker.stdin.close()
                    except Exception as e:
                        print("Exception while closing worker thread:", e)
            elif line.startswith("T "):  # aggregated results coming in
                results_received_bar.update()
                if results_received_bar.n >= results_received_bar.total:
                    results_received_bar.close()
                parsed_line = line.split(" ", 2)
                pattern_results[int(parsed_line[1])].add_all(json.loads(parsed_line[2]))
            elif not line.startswith("Using precalculated "):  # if it is some special output
                print("[AW] " + line.rstrip())  # message from analysis worker

    worker_handlers = [threading.Thread(target=process_interaction, args=(w,)) for w in workers]
    for h in worker_handlers:
        h.start()
    for h in worker_handlers:
        h.join()
    jobs_given_bar.close()
    print("All workers are closed!")

    return pattern_results


def interactive_analyze_disagreements(repo, views, target_patterns: PatternsType, node_filter_func=None, parallel=True, ignore_previous_results=False):
    pattern_results = analyze_disagreements(repo, views, target_patterns, node_filter_func, parallel, ignore_previous_results)

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
