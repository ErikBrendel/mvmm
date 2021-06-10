from util import *
from legacy_graph import *
from local_repo import *
from metrics_evolutionary import *
from metrics_structural import *
from metrics_linguistic import *


class MetricsGeneration:
    # ascii art: http://patorjk.com/software/taag/#p=display&f=Soft&t=STRUCTURAL%0A.%0ALINGUISTIC%0A.%0AEVOLUTIONARY%0A.%0ADYNAMIC
    def __init__(self, repo):
        self.repo = repo

    def calculate_evolutionary_connections(self) -> LegacyCouplingGraph:
        """
,------.,--.   ,--.,-----. ,--.   ,--. ,--.,--------.,--. ,-----. ,--.  ,--.  ,---.  ,------.,--.   ,--. 
|  .---' \  `.'  /'  .-.  '|  |   |  | |  |'--.  .--'|  |'  .-.  '|  ,'.|  | /  O  \ |  .--. '\  `.'  /  
|  `--,   \     / |  | |  ||  |   |  | |  |   |  |   |  ||  | |  ||  |' '  ||  .-.  ||  '--'.' '.    /   
|  `---.   \   /  '  '-'  '|  '--.'  '-'  '   |  |   |  |'  '-'  '|  | `   ||  | |  ||  |\  \    |  |    
`------'    `-'    `-----' `-----' `-----'    `--'   `--' `-----' `--'  `--'`--' `--'`--' '--'   `--'    
        """
        # MAX_COMMIT_FILES = 50  # Ignore too large commits. (constant moved)

        coupling_graph = LegacyExplicitCouplingGraph("evolutionary")

        def processDiffs(diffs):
            score = 2 / len(diffs)
            diffs = [d for d in diffs if self.repo.get_tree().has_node(d)]
            for f1, f2 in all_pairs(diffs):
                coupling_graph.add(f1, f2, score)
            for node in diffs:
                coupling_graph.add_support(node, 1)

        print("Discovering commits...")
        all_commits = list(self.repo.get_all_commits())
        # shuffle(all_commits)
        print("Done!")
        self.repo.get_tree()
        print("Commits to analyze: " + str(len(all_commits)))

        map_parallel(
            all_commits,
            partial(get_commit_diff, repo=self.repo),
            processDiffs,
            "Analyzing commits",
            force_non_parallel=False
        )

        coupling_graph.cutoff_edges(0.005)
        coupling_graph.cleanup(3)
        return coupling_graph

    def post_evolutionary(self, coupling_graph: LegacyCouplingGraph):
        pass

    def calculate_structural_connections(self) -> LegacyCouplingGraph:
        """
 ,---. ,--------.,------. ,--. ,--. ,-----.,--------.,--. ,--.,------.   ,---.  ,--.                     
'   .-''--.  .--'|  .--. '|  | |  |'  .--./'--.  .--'|  | |  ||  .--. ' /  O  \ |  |                     
`.  `-.   |  |   |  '--'.'|  | |  ||  |       |  |   |  | |  ||  '--'.'|  .-.  ||  |                     
.-'    |  |  |   |  |\  \ '  '-'  ''  '--'\   |  |   '  '-'  '|  |\  \ |  | |  ||  '--.                  
`-----'   `--'   `--' '--' `-----'  `-----'   `--'    `-----' `--' '--'`--' `--'`-----'   
        """

        coupling_graph = LegacyExplicitCouplingGraph("structural")

        context = StructuralContext(self.repo)
        context.couple_files_by_import(coupling_graph)
        context.couple_by_inheritance(coupling_graph)
        context.couple_members_by_content(coupling_graph)
        coupling_graph.cleanup(3)
        flush_unresolvable_vars()

        return coupling_graph

    def post_structural(self, coupling_graph: LegacyExplicitCouplingGraph):
        coupling_graph.propagate_down(2, 0.5)
        coupling_graph.dilate(1, 0.8)
        pass

    def calculate_linguistic_connections(self) -> LegacyCouplingGraph:
        """
,--.   ,--.,--.  ,--. ,----.   ,--. ,--.,--. ,---. ,--------.,--. ,-----.                                
|  |   |  ||  ,'.|  |'  .-./   |  | |  ||  |'   .-''--.  .--'|  |'  .--./                                
|  |   |  ||  |' '  ||  | .---.|  | |  ||  |`.  `-.   |  |   |  ||  |                                    
|  '--.|  ||  | `   |'  '--'  |'  '-'  '|  |.-'    |  |  |   |  |'  '--'\                                
`-----'`--'`--'  `--' `------'  `-----' `--'`-----'   `--'   `--' `-----'              
        """

        coupling_graph = LegacySimilarityCouplingGraph("linguistic")

        node_words = extract_topic_model_documents(self.repo.get_all_interesting_files())
        topics = train_topic_model(node_words)
        couple_by_topic_similarity(node_words, topics, coupling_graph)

        return coupling_graph

    def post_linguistic(self, coupling_graph: LegacyCouplingGraph):
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
            os.remove(LegacyCouplingGraph.pickle_path(repo.name, name))

    @staticmethod
    def get(repo: LocalRepo, name: str, ignore_post_processing=False) -> LegacyCouplingGraph:
        if name == "module_distance":
            return LegacyModuleDistanceCouplingGraph()
        if MetricManager.cache_key(repo, name) in MetricManager.graph_cache:
            return MetricManager.graph_cache[MetricManager.cache_key(repo, name)]
        if MetricManager._data_present(repo.name, name):
            # print("Using precalculated " + name + " values")
            graph = LegacyCouplingGraph.load(repo.name, name)
            if not ignore_post_processing:
                getattr(MetricsGeneration(repo), "post_" + name)(graph)
            MetricManager.graph_cache[MetricManager.cache_key(repo, name)] = graph
            return graph
        print("No precalculated " + name + " values found, starting calculations...")
        graph: LegacyCouplingGraph = getattr(MetricsGeneration(repo), "calculate_" + name + "_connections")()
        print("Calculated " + name + " values, saving them now...")
        graph.save(repo.name)
        if not ignore_post_processing:
            getattr(MetricsGeneration(repo), "post_" + name)(graph)
        MetricManager.graph_cache[MetricManager.cache_key(repo, name)] = graph
        return graph

    @staticmethod
    def _data_present(repo_name: str, name: str):
        return os.path.isfile(LegacyCouplingGraph.pickle_path(repo_name, name))
