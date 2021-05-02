from local_repo import *
from analysis import *

# print(sys.argv)
[_self_script_name, repo_name, views, patterns] = sys.argv
views = json.loads(views)
patterns = json.loads(patterns)

print("creating repo")
repo = LocalRepo(repo_name)
print("creating repo done")
print(repo.name)
print(patterns)

# https://stackoverflow.com/questions/1450393/how-do-you-read-from-stdin
total_nodes = int(input())
print("total nodes: " + str(total_nodes))

node_list = []
for n in range(total_nodes):
    node_list.append(input().strip())
print("received " + str(len(node_list)) + " nodes")

analysis_graphs = list([MetricManager.get(repo, g) for g in views])
for g in analysis_graphs:
    for n in node_list:
        g.get_normalized_support(n)

print("M")
sys.stdout.flush()
while True:
    command = input()
    if command.startswith("Q"):  # Quit
        break
    elif command.startswith("J"):  # New job!
        # import pprofile;
        # profiler = pprofile.Profile()
        # with profiler:
        [range_start, range_end] = [int(n) for n in command[len("J "):].strip().split(",")]
        start_nodes = node_list[range_start:range_end]
        for n1 in range(range_start, range_end):
            for n2 in range(0, n1):
                result = analyze_pair((node_list[n1], node_list[n2]), analysis_graphs, patterns)
                if result is not None:
                    print("R " + json.dumps(result))
        print("M")
        sys.stdout.flush()
        # profiler.dump_stats("/home/ebrendel/mvmm/scripts/profiling-stats.txt")
        # print("profiling results saved!")
    else:
        print("Unknown command: " + command)
        sys.stdout.flush()
print("Analysis worker closing")
