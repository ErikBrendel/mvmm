import numpy as np

from repos import all_new_repos
from local_repo import *
from metrics import *
from cachier import cachier


@cachier()
def get_all_nodes(r: LocalRepo) -> Set[str]:
    return set([tree_node.get_path() for tree_node in r.get_tree().traverse_gen()])


@cachier()
def get_all_view_nodes(r: LocalRepo, view: str) -> Set[str]:
    if view == "linguistic":
        g: SimilarityCouplingGraph = MetricManager.get(r, view)
        return set([m for m in (get_all_nodes(r)) if g.similarity_has_node(m)])
    elif view in {"references", "evolutionary"}:
        g: ExplicitCouplingGraph = MetricManager.get(r, view, ignore_post_processing=True)
        return set(g.get_data()[0]).intersection(get_all_nodes(r))
    raise Exception("No")


for view in ["references", "evolutionary", "linguistic"]:
    print("\n" * 3 + view)
    coverage_values = []
    for repo_name in ["jfree/jfreechart:v1.5.3"]:  # ["jfree/jfreechart:v1.5.3"]  /  all_new_repos
        r = LocalRepo.for_name(repo_name)
        all_modules = get_all_nodes(r)
        graph_node_names = get_all_view_nodes(r, view)
        coverage = len(graph_node_names) / len(all_modules)
        coverage_values.append(coverage)
        print(f"{repo_name}/{view}: {coverage:.1%}")
        freq_dist = FreqDist()
        tree = r.get_tree()
        for missing_module in (all_modules - graph_node_names):
            freq_dist[tree.find_node(missing_module).get_type_including_file()] += 1
        print(dict(freq_dist))
        for type in ["directory", "file", "method", "constructor", "field", "class", "enum", "interface"]:
            in_repo_typed = set([n for n in all_modules if tree.find_node(n).get_type_including_file() == type])
            in_graph_typed = in_repo_typed.intersection(graph_node_names)
            coverage_typed = len(in_graph_typed) / len(in_repo_typed)
            print(f"  {type}: {coverage_typed:.1%} ({len(in_graph_typed)} / {len(in_repo_typed)})")
            if 0 < len(in_graph_typed) < len(in_repo_typed):
                print("    > " + " ".join(list(in_repo_typed - in_graph_typed)))
                if len(in_graph_typed) < 5:
                    print("    > only ones covered: " + " ".join(list(in_graph_typed)))
    print(f"TOTAL COVERAGE: {np.mean(coverage_values)=} / {np.median(coverage_values)=} ({sorted(coverage_values)=})")
