import logging; logging.basicConfig(level=logging.INFO)
import pdb
import pyfiglet

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *
"""
repos = [
    # "wrandelshofer/jhotdraw/JHotDraw",
    # "wrandelshofer/jhotdraw/jhotdraw6",
    # "wrandelshofer/jhotdraw/jhotdraw7",
    # "wrandelshofer/jhotdraw/jhotdraw8",
    # "wumpz/jhotdraw",
    "ErikBrendel/LudumDare",
    "ErikBrendel/LD35",
    # "jenkinsci/jenkins",
    # "eclipse/aspectj.eclipse.jdt.core",  # from duerschmidt
    # "neuland/jade4j",
    "jfree/jfreechart",
    # "brettwooldridge/HikariCP",
    # "adamfisk/LittleProxy",
    # "dynjs/dynjs",
    # "SonarSource/sonarqube",
    # "eclipse/che",
    # "elastic/elasticsearch",
    # "apache/camel",
    # "jOOQ/jOOQ",
    # "netty/netty",
    # "ErikBrendel/ProgressiveImageEditor",
]"""
print("Repos to check: " + str(len(repos)))
print(repos)
# repos.sort(key=lambda repo: len(LocalRepo(repo).get_all_interesting_files()))
print("Sorted results:")
print(repos)

for repo in repos:
    r = LocalRepo(repo)
    print(pyfiglet.figlet_format(r.name))
    r.update()
    # print("|".join(sorted([tree_node.get_path() for tree_node in r.get_tree().traverse_gen() if get_node_filter_func(r, "classes")(tree_node.get_path())])))

    for view in []:  # ["references", "evolutionary", "linguistic"]
        # MetricManager.clear(r, view)

        coupling_graph = MetricManager.get(r, view, ignore_post_processing=False)
        # coupling_graph.plaintext_save(repo)
        # coupling_graph.html_save(repo)

        # print("\nResults from the " + view + " view:\n")

        # coupling_graph.print_statistics()
        # coupling_graph.print_most_linked_nodes()
        # coupling_graph.show_weight_histogram()
        # coupling_graph.visualize(use_spring=False, with_labels=False)
        # coupling_graph.visualize(use_spring=True, with_labels=False)
        print("\n")

    # analysis
    for node_filter_mode in ALL_NODE_FILTER_MODES:
        results = analyze_disagreements(r, ["references", "evolutionary", "linguistic", "module_distance"], [
            # [0, 1, 1, 1, "Non-ref?"],
            # [1, 1, 1, 0, "Too far apart"],
            # [0, 0, 1, 0, "Independent Feature duplication"],
            # [0, 1, 1, 0, "Parallel-Maintained Feature duplication"],
            [1, None, 0, 1, "Weakly modularized code"],
            [0, None, 1, 0, "Feature Duplication"],
            # [0, 0, 0, 1, "Close but totally unrelated"],

            # full 16 for testing:
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
        ], node_filter_mode, parallel=False, ignore_previous_results=False)
        print([len(r.data) for r in results])

graph_manager.flush()
print("\nProgram is over!")

"""
TODO:


Kopplungs Werte nicht nach min/max/median normalisieren, sondern nach dem Histogramm: der Wert zwischen 0 und 1 sollte proportional zum rang in der sortierten Liste sein. 0 und 1 bleiben weiterhin die extremfälle (beachte hier wenn viele kanten den gleichen Wert haben!), aber alles dazwischen ist gleichmäßiger verteilt. Das sollte gut die powerlaw Verteilung auflösen und alle Ausreißer ähnlich nah an 0.99 bringen 
Das klingt mathematisch nach der inversen CDF über alle beobachteten support scores, weil cdf(min) = 0, cdf(max) = 1, cdf(median) = 0.5 - würde ich aber erst umschreiben wenn wir uns sicher sind dass auch genau das passiert ("interpolate" klingt nicht danach. Du müsstest alle supports sortieren, und die relative position in der Liste ausgeben für die Berechnung der CDF^-1) / Was dafür sprechen kann, *nicht* die CDF zu nehmen ist dass eine lineare Interpolation große Unterschiede besser berücksichtigt. Die CDF würde nur die "Reihenfolge" der Werte abbilden, also [1, 2, 50, 99, 100] wäre äquivalent zu [1, 49, 50, 51, 100], was man vielleicht nicht will. / Aktuell ist es nicht die CDF, sondern tatsächlich 2 lineare Interpolationen, einmal vom Minimum zum Median, und einmal von dort zum Maximum. Es steht auf meiner Todo-Liste für die Masterarbeit, da auch mal eine CDF auszuprobieren. Vielleicht geht es ja besser. Würde zumindest besser mit outliern klar kommen. Mit dem aktuellen Ansatz hat (dank power law) fast kein Methoden-paar einen Wert  größer als 0.51

Normalisieren sollte auch nur innerhalb einer Ebene an Modulen passieren: nicht Methoden und Klassen gleichzeitig normalisieren, sondern erst den node Filter anwenden und dann nur diese Menge Normalisieren

support probability based: https://stats.stackexchange.com/questions/237037/bayesian-updating-with-new-data

"""