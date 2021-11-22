from util import *
from graph import *
from local_repo import *
from metrics_evolutionary import *
from metrics_references import *
from metrics_linguistic import *


METRIC_GRAPH_CLASSES = {
    "evolutionary": ExplicitCouplingGraph,
    "references": ExplicitCouplingGraph,
    "linguistic": SimilarityCouplingGraph,
    "module_distance": ModuleDistanceCouplingGraph,
}


class MetricsGeneration:
    # ascii art: http://patorjk.com/software/taag/#p=display&f=Soft&t=REFERENCES%0A.%0ALINGUISTIC%0A.%0AEVOLUTIONARY%0A.%0ADYNAMIC
    def __init__(self, repo: LocalRepo):
        self.repo = repo

    def calculate_evolutionary_connections(self) -> ExplicitCouplingGraph:
        """
,------.,--.   ,--.,-----. ,--.   ,--. ,--.,--------.,--. ,-----. ,--.  ,--.  ,---.  ,------.,--.   ,--.
|  .---' \  `.'  /'  .-.  '|  |   |  | |  |'--.  .--'|  |'  .-.  '|  ,'.|  | /  O  \ |  .--. '\  `.'  /
|  `--,   \     / |  | |  ||  |   |  | |  |   |  |   |  ||  | |  ||  |' '  ||  .-.  ||  '--'.' '.    /
|  `---.   \   /  '  '-'  '|  '--.'  '-'  '   |  |   |  |'  '-'  '|  | `   ||  | |  ||  |\  \    |  |
`------'    `-'    `-----' `-----' `-----'    `--'   `--' `-----' `--'  `--'`--' `--'`--' '--'   `--'
        """

        coupling_graph = ExplicitCouplingGraph("evolutionary")

        self.repo.get_tree()
        new_couple_by_same_commits(self.repo, coupling_graph)
        # coupling_graph.cutoff_edges(0.0001)
        # coupling_graph.remove_small_components(3)

        return coupling_graph

    def post_evolutionary(self, coupling_graph: ExplicitCouplingGraph):
        # coupling_graph.propagate_down(2, 0.5)
        pass

    def calculate_references_connections(self) -> ExplicitCouplingGraph:
        """
,------. ,------.,------.,------.,------. ,------.,--.  ,--. ,-----.,------. ,---.
|  .--. '|  .---'|  .---'|  .---'|  .--. '|  .---'|  ,'.|  |'  .--./|  .---''   .-'
|  '--'.'|  `--, |  `--, |  `--, |  '--'.'|  `--, |  |' '  ||  |    |  `--, `.  `-.
|  |\  \ |  `---.|  |`   |  `---.|  |\  \ |  `---.|  | `   |'  '--'\|  `---..-'    |
`--' '--'`------'`--'    `------'`--' '--'`------'`--'  `--' `-----'`------'`-----'
        """

        coupling_graph = ExplicitCouplingGraph("references")

        context = ReferencesContext(self.repo)
        context.couple_files_by_import(coupling_graph)
        context.couple_by_inheritance(coupling_graph)
        context.couple_members_by_content(coupling_graph)
        # coupling_graph.remove_small_components(3)
        flush_unresolvable_vars()

        return coupling_graph

    def post_references(self, coupling_graph: ExplicitCouplingGraph):
        coupling_graph.propagate_down(2, 0.5)
        coupling_graph.dilate(1, 0.8)
        pass

    def calculate_linguistic_connections(self) -> SimilarityCouplingGraph:
        """
,--.   ,--.,--.  ,--. ,----.   ,--. ,--.,--. ,---. ,--------.,--. ,-----.
|  |   |  ||  ,'.|  |'  .-./   |  | |  ||  |'   .-''--.  .--'|  |'  .--./
|  |   |  ||  |' '  ||  | .---.|  | |  ||  |`.  `-.   |  |   |  ||  |
|  '--.|  ||  | `   |'  '--'  |'  '-'  '|  |.-'    |  |  |   |  |'  '--'\
`-----'`--'`--'  `--' `------'  `-----' `--'`-----'   `--'   `--' `-----'
        """

        coupling_graph = SimilarityCouplingGraph("linguistic")

        node_words = extract_topic_model_documents(self.repo.get_all_interesting_files())
        topics = train_topic_model(node_words)
        couple_by_topic_similarity(node_words, topics, coupling_graph)

        return coupling_graph

    def post_linguistic(self, coupling_graph: SimilarityCouplingGraph):
        pass

    def calculate_module_distance_connections(self) -> ModuleDistanceCouplingGraph:
        return ModuleDistanceCouplingGraph()

    def post_module_distance(self, coupling_graph: ModuleDistanceCouplingGraph):
        pass

    # -------------------------------------------------------------------------------------------


class MetricManager:
    graph_cache = {}

    @staticmethod
    def cache_key(repo: LocalRepo, name: str) -> str:
        return repo.name + "-" + name

    @staticmethod
    def clear(repo: LocalRepo, name: str):
        MetricManager.graph_cache.pop(MetricManager.cache_key(repo, name), None)
        if MetricManager._data_present(repo.name, name):
            os.remove(CouplingGraph.pickle_path(repo.name, name))

    @staticmethod
    def get(repo: LocalRepo, name: str, ignore_post_processing=False) -> CouplingGraph:
        if MetricManager.cache_key(repo, name) in MetricManager.graph_cache:
            return MetricManager.graph_cache[MetricManager.cache_key(repo, name)]
        if MetricManager._data_present(repo.name, name):
            print("Using precalculated " + name + " values")
            graph = CouplingGraph.load(repo.name, name, METRIC_GRAPH_CLASSES[name])
        else:
            print("No precalculated " + name + " values found, starting calculations...")
            graph: CouplingGraph = getattr(MetricsGeneration(repo), "calculate_" + name + "_connections")()
            graph.print_statistics()
            print("Calculated " + name + " values, saving them now...")
            graph.save(repo.name)
        if not ignore_post_processing:
            getattr(MetricsGeneration(repo), "post_" + name)(graph)
        MetricManager.graph_cache[MetricManager.cache_key(repo, name)] = graph
        return graph

    @staticmethod
    def _data_present(repo_name: str, name: str):
        return os.path.isfile(CouplingGraph.pickle_path(repo_name, name))
