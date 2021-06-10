import math
import random
import sys

from cpp_graph import CppGraph, CppExplicitCouplingGraph, CppSimilarityCouplingGraph, graph_manager
from graph import ExplicitCouplingGraph, SimilarityCouplingGraph
from metrics import MetricManager, MetricsGeneration
from local_repo import LocalRepo
from util import log_progress, all_pairs

import glob


files = glob.glob('../metrics/**/*.gpickle', recursive=True)
name_parts = [file[len("../metrics/"):-len(".gpickle")].split("/") for file in files]
repo_names = [(user + "/" + repo, name) for user, repo, name in name_parts]


def is_close(a, b):
    return abs(a - b) < 0.0000001

"""
for repo, name in log_progress(repo_names, desc="Converting"):
    print("Converting: " + repo + "::" + name)
    r = LocalRepo(repo)
    old_graph = MetricManager.get(r, name, ignore_post_processing=True)
    if name == "linguistic":
        g = CppSimilarityCouplingGraph(name)
        og: SimilarityCouplingGraph = old_graph
        for node in og.get_node_set():
            g.add_node(node, og.coords[node], og.support[node])
        g.save(repo)
    elif name == "structural" or name == "evolutionary":
        g = CppExplicitCouplingGraph(name)
        og: ExplicitCouplingGraph = old_graph
        for node in og.get_node_set():
            g.add_support(node, og.get_support(node))
        for a, b, info in og.g.edges.data():
            g.add(a, b, info["weight"])
        g.save(repo)
    else:
        print("Skipping: " + repo + "/" + name)
    print("nice")

"""




for repo, name in log_progress(repo_names, desc="Checking"):
    r = LocalRepo(repo)
    old_graph = MetricManager.get(r, name, ignore_post_processing=True)
    new_graph = CppGraph.load(repo, name)
    old_node_set = old_graph.get_node_set()
    new_node_set = set(new_graph.get_node_set())
    if old_node_set != new_node_set:
        raise Exception("Node sets not equal!")
    for node in old_node_set:
        if not is_close(old_graph.get_normalized_support(node), new_graph.get_normalized_support(node)):
            raise Exception("supports not equal!")
    test_options = list(all_pairs(list(old_node_set)))
    if len(test_options) > 1000:
        random.seed(42)
        test_options = random.sample(test_options, 1000)
    for a, b in test_options:
        if not is_close(old_graph.get_normalized_coupling(a, b), new_graph.get_normalized_coupling(a, b)):
            old_graph.get_normalized_coupling(a, b)
            raise Exception("coupling values not equal!")

"""

for repo in ["ErikBrendel/LudumDare", "ErikBrendel/LD35", "vanzin/jEdit", "wumpz/jhotdraw"]:
    r = LocalRepo(repo)
    new_graph: CppExplicitCouplingGraph = CppGraph.load(repo, "structural", CppExplicitCouplingGraph)
    MetricsGeneration(r).post_structural(new_graph)
    old_graph = MetricManager.get(r, "structural")
    old_node_set = old_graph.get_node_set()
    new_node_set = set(new_graph.get_node_set())
    if old_node_set != new_node_set:
        raise Exception("Node sets not equal!")
    test_options = list(all_pairs(list(old_node_set)))
    if len(test_options) > 1000:
        random.seed(42)
        test_options = random.sample(test_options, 1000)
    for a, b in log_progress(test_options):
        if not is_close(old_graph.get_normalized_coupling(a, b), new_graph.get_normalized_coupling(a, b)):
            old_graph.get_normalized_coupling(a, b)
            raise Exception("coupling values not equal!")
"""
