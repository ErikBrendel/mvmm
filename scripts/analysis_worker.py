from local_repo import *
from analysis import *

# print(sys.argv)
[_self_script_name, repo_name, views, patterns_str] = sys.argv
views = json.loads(views)
target_patterns: PatternsType = json.loads(patterns_str)

repo = LocalRepo(repo_name)

# https://stackoverflow.com/questions/1450393/how-do-you-read-from-stdin
total_nodes = int(input())

node_list = []
for n in range(total_nodes):
    node_list.append(input().strip())

analysis_graphs = list([MetricManager.get(repo, g) for g in views])
for g in analysis_graphs:
    for n in node_list:
        g.get_normalized_support(n)

pattern_results = [
    BestResultsSet(sum(type(x) == int for x in p) + 1, SHOW_RESULTS_SIZE)  # one dim for each graph that is used in the pattern + 1 for support
    for p in target_patterns]


def handle_results(pattern_results_part):
    for i, part in enumerate(pattern_results_part):
        pattern_results[i].add_all(part)


print("R")
sys.stdout.flush()
while True:
    command = input()
    if command.startswith("D"):  # Done with jobs, please give results now
        break
    elif command.startswith("J"):  # New job!
        # import pprofile;
        # profiler = pprofile.Profile()
        # with profiler:
        [range_start, range_end] = [int(n) for n in command[len("J "):].strip().split(",")]
        start_nodes = node_list[range_start:range_end]
        for n1 in range(range_start, range_end):
            for n2 in range(0, n1):
                results = analyze_pair((node_list[n1], node_list[n2]), analysis_graphs, target_patterns)
                if results is not None:
                    handle_results(results)
        print("M")
        sys.stdout.flush()
        # profiler.dump_stats("/home/ebrendel/mvmm/scripts/profiling-stats.txt")
        # print("profiling results saved!")
    else:
        print("Unknown command: " + command)
        sys.stdout.flush()
for i, results in enumerate(pattern_results):
    results.trim()
    print("T " + str(i) + " " + json.dumps(results.data))
    sys.stdout.flush()
print("Analysis worker closing with result sizes: " + ",".join(str(len(r.data)) for r in pattern_results))
print("Q")
