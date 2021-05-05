import logging; logging.basicConfig(level=logging.INFO)
import pdb
import pyfiglet

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *

repos = [
    # "wrandelshofer/jhotdraw/JHotDraw",
    # "wrandelshofer/jhotdraw/jhotdraw6",
    # "wrandelshofer/jhotdraw/jhotdraw7",
    # "wrandelshofer/jhotdraw/jhotdraw8",
    # "wumpz/jhotdraw",
    "ErikBrendel/LudumDare",  # 8 minutes BTM
    # "eclipse/eclipse.jdt.core",  # from duerschmidt
    # "jenkinsci/jenkins",
    # "neuland/jade4j",
    # "jfree/jfreechart",
    # "brettwooldridge/HikariCP",  # 1.2h BTM
    # "adamfisk/LittleProxy",  # 1.5h BTM
    # "dynjs/dynjs",  # 2.5h BTM
    # "SonarSource/sonarqube",  # quite big / prob. several hours BTM
    # "square/okhttp",
    # "eclipse/che",
    # "elastic/elasticsearch",
    # "apache/camel",
    # "jOOQ/jOOQ",
]

for repo in repos:
    r = LocalRepo(repo)
    print(pyfiglet.figlet_format(r.name))
    r.update()

    for view in []:  # ["structural", "evolutionary", "linguistic"]
        # MetricManager.clear(r, view)

        coupling_graph = MetricManager.get(r, view)
        # coupling_graph.plaintext_save(repo)
        # coupling_graph.html_save(repo)

        print("\nResults from the " + view + " view:\n")

        coupling_graph.print_statistics()
        # coupling_graph.print_most_linked_nodes()
        # coupling_graph.show_weight_histogram()
        # coupling_graph.visualize(use_spring=False, with_labels=False)
        # coupling_graph.visualize(use_spring=True, with_labels=False)
        print("\n")
    # continue

    # amalysis
    repo_tree = r.get_tree()


    def node_filter(node_path):
        tree_node = repo_tree.find_node(node_path)
        return tree_node.get_type() == "method" and tree_node.get_line_span() >= 2


    results = analyze_disagreements(r, ["structural", "evolutionary", "linguistic", "module_distance"], [
        [0, 1, 1, 1, "Non-struct?"],
        [1, 1, 1, 0, "Too far apart"],
        [0, 0, 1, 0, "Independent Feature duplication"],
        [0, 1, 1, 0, "Parallel-Maintained Feature duplication"],
        [1, None, 0, 1, "Weakly modularized code"],
        [0, 0, 0, 1, "Close but totally unrelated"],
    ], node_filter, parallel=True)
    print([len(r.data) for r in results])

print("\nProgram is over!")
