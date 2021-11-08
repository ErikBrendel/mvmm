import pdb
import random
import sys
import threading
import json

from best_results_set import BestResultsSet

from custom_types import *
from local_repo import *
from metrics import *
from workarounds import *

ALL_VIEWS = ["references", "evolutionary", "linguistic", "module_distance"]
ALL_PATTERNS: PatternsType = [
    [0, 0, 0, 0, 'Not coupled at all'],
    [0, 0, 0, 1, 'Only "project structure": Close but completely unrelated to each other'],
    [0, 0, 1, 0, 'Only "linguistic": Independent feature duplication'],
    [0, 0, 1, 1, 'Close independent feature duplication?'],
    [0, 1, 0, 0, 'Only "evolutionary": Modules are related to each other on an unknown and hidden level'],
    [0, 1, 0, 1, 'Your code is successfully modularized by "things that change together", but your language and structure do not reflect this modularity'],
    [0, 1, 1, 0, 'Parallel-Maintained feature duplication'],
    [0, 1, 1, 1, 'Everything except references: These nodules belong together, but it is not obvious from the code. Maybe meta-programming? Maybe the references metric is bad?'],
    [1, 0, 0, 0, 'Only "references": Using "library code" somewhere else'],
    [1, 0, 0, 1, 'Weakly modularized code:  close in the project structure and coupled by references, but semantically disjoint'],
    [1, 0, 1, 0, 'Using and/or extending a library'],
    [1, 0, 1, 1, 'Everything except evolutionary: One module developed in independent parts OR using a weird committing policy in the company OR one big chunk of code copied into the repo'],
    [1, 1, 0, 0, 'Separate modules developed together because they need each other.'],
    [1, 1, 0, 1, 'Weakly modularized code: dependent on each other, but semantically disjoint'],
    [1, 1, 1, 0, 'Too far apart: These modules seem to belong closer together than they currently are in the project structure'],
    [1, 1, 1, 1, 'Evenly coupled across all metrics'],
]


def get_node_filter_func(repo: LocalRepo, mode: NodeFilterMode):
    repo_tree = repo.get_tree()
    file_extension = "." + repo.type_extension()

    def node_filter_methods(node_path):
        tree_node = repo_tree.find_node(node_path)
        return tree_node.get_type() in ["method", "constructor"] and tree_node.get_line_span() >= 4

    def node_filter_classes(node_path):
        tree_node = repo_tree.find_node(node_path)
        return tree_node.get_type() in ["class", "interface", "enum"] and tree_node.get_line_span() >= 2

    def node_filter_files(node_path):
        tree_node = repo_tree.find_node(node_path)
        return tree_node.get_type() is None and tree_node.name.endswith(file_extension)

    def node_filter_packages(node_path):
        tree_node = repo_tree.find_node(node_path)
        return \
            tree_node.get_type() is None and \
            not tree_node.name.endswith(file_extension) and \
            any(child.name.endswith(file_extension) for child in tree_node.children.values())

    return {
        "methods": node_filter_methods,
        "classes": node_filter_classes,
        "files": node_filter_files,
        "packages": node_filter_packages
    }[mode]


def get_filtered_nodes(repo: LocalRepo, mode: NodeFilterMode) -> List[str]:
    node_filter_func = get_node_filter_func(repo, mode)
    return [tree_node.get_path()
            for tree_node in repo.get_tree().traverse_gen()
            if node_filter_func(tree_node.get_path())]


SHOW_RESULTS_SIZE = 2000


def analyze_disagreements(repo: LocalRepo, views: List[str], target_patterns: PatternsType,
                          node_filter_mode: NodeFilterMode, ignore_previous_results=False,
                          random_shuffled_view_access=False) -> List[BestResultsSet]:
    """
    when views are [ref, evo, ling], the pattern [0, 1, None, "comment"] searches for nodes that are
    strongly coupled evolutionary, loosely coupled by references, and the language does not matter
    """
    if len(views) < 1:
        return []
    if not all([len(p) >= len(views) for p in target_patterns]):
        print("Patterns need at least one element per graph!")
        raise Exception("Patterns need at least one element per graph!")

    result_sets: List[Optional[BestResultsSet]] = [None for p in target_patterns]
    if not ignore_previous_results:
        for i, pattern in enumerate(target_patterns):
            result = BestResultsSet.load(BestResultsSet.get_name(repo.name, views, node_filter_mode, pattern))
            if result is not None:
                result_sets[i] = result

    if all(r is not None for r in result_sets):
        return result_sets

    if random_shuffled_view_access:
        # access all views in random order to balance preprocessing
        views_shuffled = views[:]
        random.shuffle(views_shuffled)
        for v in views_shuffled:
            MetricManager.get(repo, v)
    analysis_graphs = list([MetricManager.get(repo, v) for v in views])

    all_nodes = get_filtered_nodes(repo, node_filter_mode)

    print("Total node count:", len(all_nodes))
    print("Methods:", sum(repo.get_tree().find_node(path).get_type() == "method" for path in all_nodes))
    print("constructors:", sum(repo.get_tree().find_node(path).get_type() == "constructor" for path in all_nodes))
    print("fields:", sum(repo.get_tree().find_node(path).get_type() == "field" for path in all_nodes))
    print("classes:", sum(repo.get_tree().find_node(path).get_type() == "class" for path in all_nodes))
    print("interfaces:", sum(repo.get_tree().find_node(path).get_type() == "interface" for path in all_nodes))
    print("enums:", sum(repo.get_tree().find_node(path).get_type() == "enum" for path in all_nodes))
    print("without type:", sum(repo.get_tree().find_node(path).get_type() is None for path in all_nodes))
    node_filter_func = get_node_filter_func(repo, node_filter_mode)
    if node_filter_func is not None:
        all_nodes = [node for node in all_nodes if node_filter_func(node)]
    print("all filtered nodes:", len(all_nodes))

    required_patterns = [p for p, r in zip(target_patterns, result_sets) if r is None]
    calculated_results: List[BestResultsSet] = find_disagreement_results_serial_cpp(analysis_graphs, required_patterns, all_nodes)

    fill_none_with_other(result_sets, calculated_results)
    for r, p in zip(result_sets, target_patterns):
        r.export(BestResultsSet.get_name(repo.name, views, node_filter_mode, p))
    return result_sets


def find_disagreement_results_serial_cpp(analysis_graphs: List[CouplingGraph], target_patterns: PatternsType, all_nodes: List[str]) -> List[BestResultsSet]:
    ns = graph_manager.create_node_set(all_nodes)

    # "findDisagreements", "nodeSetId resultSize graphAmount graphs... patternsComponents...
    fixed_args = ["findDisagreements", str(ns), str(SHOW_RESULTS_SIZE), str(len(analysis_graphs))]
    graph_args = [str(g.id) for g in analysis_graphs]
    patterns_args = ["nan" if v is None else str(v) for pattern in target_patterns for v in pattern[:len(analysis_graphs)]]
    raw_results = graph_manager.execute_strings(fixed_args + graph_args + patterns_args)

    pattern_results = [
        BestResultsSet(sum(type(x) == int for x in p) + 1, SHOW_RESULTS_SIZE)  # one dim for each graph that is used in the pattern + 1 for support
        for p in target_patterns]

    result_i = 0
    brs_i = 0

    all_dim_count = len(analysis_graphs) + 1  # and support
    while result_i < len(raw_results):
        if len(raw_results[result_i]) == 0:
            result_i += 1
            brs_i += 1
        else:
            dimension_count = pattern_results[brs_i].dimension_count
            sort_values = tuple(float(raw_results[result_i + i]) for i in range(dimension_count))
            name1 = raw_results[result_i + dimension_count]
            name2 = raw_results[result_i + dimension_count + 1]
            display_values = tuple(float(raw_results[result_i + dimension_count + 2 + i]) for i in range(all_dim_count))

            pattern_results[brs_i].add((sort_values, (name1, name2, display_values)))

            result_i += dimension_count + 2 + all_dim_count  # sort values, the two node names, display values

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
                non_duplicated_data = []
                seen_node_pairs = set()
                duplication_skip = 0
                for datum in multi_sorted_results[:SHOW_RESULTS_SIZE]:
                    a, b = datum[1][0:2]
                    if a > b:
                        a, b = b, a
                    key = a + "|" + b
                    if key not in seen_node_pairs:
                        seen_node_pairs.add(key)
                        non_duplicated_data.append(datum)
                    else:
                        duplication_skip += 1

                print(results.total_amount, "raw results,", len(multi_sorted_results), "final results, skipped", duplication_skip, "duplicates")

                # for d in display_data:
                #    print(d)
                display_data = [
                    ["{:1.4f}".format(raw_getter(datum)) for name, getter, raw_getter in dim] +
                    [path_html(repo, path) for path in datum[1][0:2]] +
                    ["{:1.4f}".format(sum(x * x for x in datum[0]))]
                    for datum in non_duplicated_data]
                header = [metric_display_rename(name) for name, *_ in dim] + ["method 1", "method 2", "match_score"]
                show_html_table([header] + display_data)

            return show_data

        # results.trim()
        interactive_multi_sort(results.data, dimensions, make_show_data(dimensions))

        # pdb.set_trace()
    # TODO trim node set of nodes to those they have in common?
