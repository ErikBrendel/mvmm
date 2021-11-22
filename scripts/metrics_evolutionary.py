from collections import defaultdict

from git import Commit, Diff, DiffIndex

from graph import ExplicitCouplingGraph
from util import *
from local_repo import *
from timeit import default_timer as timer

MIN_COMMIT_FILES = 1
MAX_COMMIT_FILES = 50
MIN_COMMIT_METHODS = 2
MAX_COMMIT_METHODS = 200


# needs to be separate so that multiprocessing lib can find it
def get_commit_diff(commit_hash, repo: LocalRepo) -> Optional[Set[str]]:
    # repo_tree = repo.get_tree()

    def walk_tree_cursor(cursor, prefix, content_bytes, node_handler):
        if not cursor.node.is_named:
            return

        def node_text(node):
            return decode(content_bytes[node.start_byte:node.end_byte])

        # cursor.current_field_name() is the role that this node has in its parent
        tree_node_names = []  # TODO keep in sync with references and linguistic view as well as RepoFile class
        if cursor.node.type == "class_declaration" or cursor.node.type == "interface_declaration" or cursor.node.type == "enum_declaration":
            tree_node_names.append(node_text(cursor.node.child_by_field_name("name")))
        elif cursor.node.type == "field_declaration":
            declarators = [child for child in cursor.node.children if child.type == "variable_declarator"]
            tree_node_names += [node_text(d.child_by_field_name("name")) for d in declarators]
        elif cursor.node.type == "method_declaration":
            tree_node_names.append(node_text(cursor.node.child_by_field_name("name")))
        elif cursor.node.type == "constructor_declaration":
            tree_node_names.append("constructor")

        for tree_node_name in tree_node_names:
            node_handler(prefix + "/" + tree_node_name, cursor.node)
        if len(tree_node_names) > 0:
            prefix = prefix + "/" + tree_node_names[0]

        if cursor.goto_first_child():
            walk_tree_cursor(cursor, prefix, content_bytes, node_handler)
            while cursor.goto_next_sibling():
                walk_tree_cursor(cursor, prefix, content_bytes, node_handler)
            cursor.goto_parent()

    def walk_tree(tree, content_bytes, base_path) -> Optional[RepoTree]:
        """ node_handler gets the current logic-path and node for each ast node"""
        if should_skip_file(content_bytes):
            return None
        try:
            found_nodes = RepoTree(None, "")

            def handle(logic_path, ts_node):
                found_nodes.register(logic_path, ts_node)

            walk_tree_cursor(tree.walk(), base_path, content_bytes, handle)
            return found_nodes
        except Exception as e:
            print("Failed to parse file:", base_path, "Error:", e)
            return None

    error_query = JA_LANGUAGE.query("(ERROR) @err")

    def _has_error(tree) -> bool:
        errors = error_query.captures(tree.root_node)
        return len(errors) > 1

    def blob_diff(diff) -> Set[str]:
        # pdb.set_trace()
        if diff.a_blob is None:
            return {diff.b_path}  # newly created
        elif diff.b_blob is None:
            return {diff.a_path}  # deleted
        path = diff.b_path  # in case of rename, stick to newer path, better chance at getting the right thing
        if not path.endswith("." + repo.type_extension()):
            return {path}
        a_content = diff.a_blob.data_stream.read()
        if should_skip_file(a_content):
            return set()
        b_content = diff.b_blob.data_stream.read()
        if should_skip_file(b_content):
            return set()
        a_tree = java_parser.parse(a_content)
        b_tree = java_parser.parse(b_content)
        if _has_error(a_tree) or _has_error(b_tree):
            return {path}  # I guess just the file changed, no more details available
        a_repo_tree = walk_tree(a_tree, a_content, path)
        if a_repo_tree is None:
            return {path}
        b_repo_tree = walk_tree(b_tree, b_content, path)
        if b_repo_tree is None:
            return {path}
        return a_repo_tree.calculate_diff_to(b_repo_tree, a_content, b_content)

    c1 = repo.get_commit(commit_hash)
    if len(c1.parents) == 1:
        c2 = c1.parents[0]
        # t4 = timer()
        diff = c1.diff(c2)
        # t5 = timer()
        if not (MIN_COMMIT_FILES <= len(diff) <= MAX_COMMIT_FILES):
            return None
        diffs = {result for d in diff for result in blob_diff(d)}  # if repo_tree.has_node(result)
        # t6 = timer()
        # print("Diff: " + str(len(diff)) + " / " + str(len(diffs)) + " changes")

        # print("Time taken (ms):", round((t5-t4)*1000), "(getting git diff)", round((t6-t5)*1000), "(parsing sub-file diffs)", round((t6-t4)*1000), "(total)")
    elif len(c1.parents) == 2:
        return None  # TODO how to do sub-file diffs for merge commits?
        # c2 = c1.parents[0]
        # diff_1 = c1.diff(c2)
        # c3 = c1.parents[1]
        # diff_2 = c1.diff(c3)

        # diffs_1 = [ d.a_path for d in diff_1 ]
        # diffs_2 = [ d.a_path for d in diff_2 ]
        # diffs = list(set(diffs_1).intersection(set(diffs_2)))
    else:
        return None
    if not (MIN_COMMIT_METHODS <= len(diffs) <= MAX_COMMIT_METHODS):
        return None
    return diffs


def old_couple_by_same_commits(repo: LocalRepo, coupling_graph: ExplicitCouplingGraph):
    def processDiffs(diffs: Set[str]):
        score = 2 / len(diffs)
        diffs = [d for d in diffs if repo.get_tree().has_node(d)]
        for f1, f2 in all_pairs(diffs):
            coupling_graph.add(f1, f2, score)
        for node in diffs:
            coupling_graph.add_support(node, 1)

    print("Discovering commits...")
    all_commits = list(repo.get_all_commits())
    # shuffle(all_commits)
    print("Done!")
    repo.get_tree()
    print("Commits to analyze: " + str(len(all_commits)))

    map_parallel(
        all_commits,
        partial(get_commit_diff, repo=repo),
        processDiffs,
        "Analyzing commits",
        force_non_parallel=False
    )


#########################################


#########################################


def find_changed_methods(repo: LocalRepo, parent_diffs: List[List[Diff]]) -> Set[str]:
    """return the list of all method names (name after commit) that have changed in this commit"""
    ignored_ast_node_types = {
        "import_declaration", "comment", "package_declaration", "modifiers", "superclass", "super_interfaces", "identifier", "field_access", "type_identifier", "formal_parameters"
    }  # just for performance

    def walk_tree_cursor(cursor, prefix, content_bytes, node_handler):
        if not cursor.node.is_named or cursor.node.type in ignored_ast_node_types:
            return

        def node_text(node):
            return decode(content_bytes[node.start_byte:node.end_byte])

        # cursor.current_field_name() is the role that this node has in its parent
        tree_node_names = []  # TODO keep in sync with references and linguistic view as well as RepoFile class
        if cursor.node.type == "class_declaration" or cursor.node.type == "interface_declaration" or cursor.node.type == "enum_declaration":
            tree_node_names.append(node_text(cursor.node.child_by_field_name("name")))
        elif cursor.node.type == "field_declaration":
            declarators = [child for child in cursor.node.children if child.type == "variable_declarator"]
            tree_node_names += [node_text(d.child_by_field_name("name")) for d in declarators]
        elif cursor.node.type == "method_declaration":
            tree_node_names.append(node_text(cursor.node.child_by_field_name("name")))
        elif cursor.node.type == "constructor_declaration":
            tree_node_names.append("constructor")

        if len(tree_node_names) > 0:
            for tree_node_name in tree_node_names:
                node_handler(prefix + "/" + tree_node_name, cursor.node)
            prefix = prefix + "/" + tree_node_names[0]

        if cursor.goto_first_child():
            walk_tree_cursor(cursor, prefix, content_bytes, node_handler)
            while cursor.goto_next_sibling():
                walk_tree_cursor(cursor, prefix, content_bytes, node_handler)
            cursor.goto_parent()

    def walk_tree(tree, content_bytes, base_path) -> Optional[RepoTree]:
        """ node_handler gets the current logic-path and node for each ast node"""
        if should_skip_file(content_bytes):
            return None
        try:
            found_nodes = RepoTree(None, "")

            def handle(logic_path, ts_node):
                found_nodes.register(logic_path, ts_node)

            walk_tree_cursor(tree.walk(), base_path, content_bytes, handle)
            return found_nodes
        except Exception as e:
            print("Failed to parse file:", base_path, "Error:", e)
            return None

    error_query = JA_LANGUAGE.query("(ERROR) @err")

    def _has_error(tree) -> bool:
        errors = error_query.captures(tree.root_node)
        return len(errors) > 1

    def blob_diff(diff: Diff) -> Set[str]:
        if diff.a_blob is None:
            return {diff.b_path}  # newly created
        elif diff.b_blob is None:
            return set()  # deleted -> not interested
        path = diff.b_path
        if not path.endswith("." + repo.type_extension()):
            return {path}
        a_content = diff.a_blob.data_stream.read()
        if should_skip_file(a_content):
            return set()
        b_content = diff.b_blob.data_stream.read()
        if should_skip_file(b_content):
            return set()
        a_tree = java_parser.parse(a_content)
        b_tree = java_parser.parse(b_content)
        if _has_error(a_tree) or _has_error(b_tree):
            return {path}  # I guess just the file changed, no more details available
        a_repo_tree = walk_tree(a_tree, a_content, path)
        if a_repo_tree is None:
            return {path}
        b_repo_tree = walk_tree(b_tree, b_content, path)
        if b_repo_tree is None:
            return {path}
        return a_repo_tree.calculate_diff_to(b_repo_tree, a_content, b_content)

    result: Set[str] = set()
    for diff in parent_diffs:
        for d in diff:
            result.update(blob_diff(d))
    return result


class FutureMapping:
    # FMs are chained FM, where each FM object only does
    # the renamings of one commit, and points to the next FM objects, and modern name translation
    # happens by iterating this DAG of mappers to the modern end.
    def __init__(self, next_futures: List['FutureMapping'] = None):
        self.renamings: Dict[str, str] = {}  # mapping historical method paths to one-step-closer-to-modern ones, both must not end with a slash
        self.next_futures: List[FutureMapping] = next_futures or []

    def add_renaming(self, older_name, newer_name):
        """apply the given renaming before the current state of this object"""

        if older_name.endswith("/") or newer_name.endswith("/"):
            print("Names end wit slash! Please stop that!")
            if older_name.endswith("/"):
                older_name = older_name[:-1]
            if newer_name.endswith("/"):
                newer_name = newer_name[:-1]

        if self.has_information_for(older_name):
            print(f"Single-Step FM collision: {list(self.renamings.keys())} - {older_name}! Please come and fix this!")

        self.renamings[older_name] = newer_name

    def has_information_for(self, potential_older_name):
        for existing_older_name in self.renamings.keys():
            if existing_older_name.startswith(potential_older_name) or potential_older_name.startswith(existing_older_name):
                return True
        return False

    def get_modern_names_for(self, name: str) -> Set[str]:
        """given the full path of a method, what will this method be called in the HEAD of the project?"""
        # since the FM objects form a DAG, we can do some topological sorting iteration,
        # deduplicating same names that appear through multiple paths at the same FM

        fm_open_input_counts: Dict[FutureMapping, int] = defaultdict(lambda: 0)
        for fm in self.self_and_all_descendants():
            for child in fm.next_futures:
                fm_open_input_counts[child] += 1

        waiting_before_names: Dict[FutureMapping, Set[str]] = defaultdict(lambda: set())
        ready_ends: Dict[FutureMapping, Set[str]] = {self: {name}}
        after_names = set()
        while len(ready_ends) > 0:
            fm, before_names = ready_ends.popitem()
            after_names = {fm.get_single_step_future_name_of(name) for name in before_names}
            for next_fm in fm.next_futures:
                fm_open_input_counts[next_fm] -= 1
                if fm_open_input_counts[next_fm] == 0:
                    ready_ends[next_fm] = after_names.union(waiting_before_names.pop(next_fm, set()))
                else:
                    waiting_before_names[next_fm].update(after_names)
        if len(waiting_before_names) > 0 or any(value != 0 for value in fm_open_input_counts.values()):
            print("FM DAG traversal error!")
            pdb.set_trace()
        if len(after_names) > 1 and name in after_names:
            after_names.remove(name)
        if len(after_names) != 1:
            print("Multiple after names found: ", name, after_names)
        return after_names  # we know that the last one from that loop is the FM of the HEAD commit

    def get_single_step_future_name_of(self, name: str) -> str:
        """given the full path of a method, what will this method be called after this FM?"""
        if name in self.renamings:
            return self.renamings[name]
        for old, new in self.renamings.items():
            if name.startswith(old):
                return new + name[len(old):]  # this string splice should still include the slash
        return name  # if no renaming for no part of the path has been found, maybe it has not been renamed ever :D

    def self_and_all_descendants(self):
        # return me and all my recursive next FMs
        result: Set[FutureMapping] = set()
        open_fms: Set[FutureMapping] = {self}
        while len(open_fms) > 0:
            current_fm = open_fms.pop()
            if current_fm in result:
                continue
            result.add(current_fm)
            for next_fms in current_fm.next_futures:
                if next_fms not in result:
                    open_fms.add(next_fms)
        return result

    def compress(self):
        """if I can be merged with my single next FM object, merge it into me"""
        if len(self.next_futures) != 1:
            return
        next_fm = self.next_futures[0]
        if any(next_fm.has_information_for(my_older_key) for my_older_key in self.renamings.keys()):
            return  # cannot merge safely
        for next_older_name, next_newer_name in next_fm.renamings.items():
            self.add_renaming(next_older_name, next_newer_name)
        self.next_futures = list(next_fm.next_futures)

    @staticmethod
    def create_for(next_futures: List['FutureMapping'] = None):
        # in that moment, the passed objects are finished, so we can try to compress them each
        for fm in next_futures:
            fm.compress()
        return FutureMapping(next_futures)


def find_renamings(parent_diffs: List[List[Diff]]) -> Set[Tuple[str, str]]:
    """return the list of all renamings that happened in this commit, in the form (name before this commit, name after this commit)"""
    deleted: List[Diff] = []
    created: List[Diff] = []

    result: Set[Tuple[str, str]] = set()
    for diff in parent_diffs:
        for d in diff:
            if d.a_path is not None and d.b_path is not None and d.a_path != d.b_path:
                result.add((d.a_path, d.b_path))
            elif d.a_path is None:
                created.append(d)
            elif d.b_path is None:
                deleted.append(d)
    # TODO try to match up things from the created and deleted entries
    #  extra task: also look within the modified-diffs (if within a modified file only one method is added / removed)
    #  to match those up as well, not only per-file renamings
    if len(created) > 0 and len(deleted) > 0:
        pdb.set_trace()
    return result


def get_commit_diffs(commit: Commit, create_patch=False) -> List[List[Diff]]:
    if len(commit.parents) == 0:
        return [commit.diff(create_patch=create_patch)]  # just diff it to the empty repo to get the diff content
    return [p.diff(commit, create_patch=create_patch) for p in commit.parents]


def evo_new_analyze_commit(repo: LocalRepo, commit_sha: str, future_mapping: FutureMapping, result: Dict[str, Set[str]],
                           all_changed_methods_and_renamings: Dict[str, Tuple[Set[str], Set[Tuple[str, str]]]]) -> FutureMapping:
    if commit_sha not in all_changed_methods_and_renamings:
        raise Exception(f"missing commit! {commit_sha=}, {repo.name=}")
    changed_methods, renamings = all_changed_methods_and_renamings[commit_sha]
    modern_changed_methods: Set[str] = {name for m in changed_methods for name in future_mapping.get_modern_names_for(m)}
    result[commit_sha] = {m for m in modern_changed_methods if m is not None and repo.get_tree().has(m)}

    new_future = FutureMapping([future_mapping])
    for older_name, newer_name in renamings:
        new_future.add_renaming(older_name, newer_name)
    return new_future


def get_changed_methods_for_commit(data):
    repo_name, commit_sha = data
    repo = LocalRepo(repo_name)
    parent_diffs = get_commit_diffs(repo.get_commit(commit_sha))
    return commit_sha, (find_changed_methods(repo, parent_diffs), find_renamings(parent_diffs))


def evo_calc_new(repo: LocalRepo):
    """end result: for each commit, which methods have changed in it?"""
    result: Dict[str, Set[str]] = {}

    """first, for all the commits, find out which / how many children they have"""
    print("discovering commit children information")
    commit_children: Dict[str, List[str]] = {}
    all_commits = repo.get_commit_history_of_head()
    for commit_sha in all_commits:
        for parent_sha in [p.hexsha for p in repo.get_commit(commit_sha).parents]:
            if parent_sha not in commit_children:
                commit_children[parent_sha] = []
            commit_children[parent_sha].append(commit_sha)

    """ find all the diffs for each commit in parallel """
    all_changed_methods_and_renamings: Dict[str, Tuple[Set[str], Set[Tuple[str, str]]]] = dict()
    map_parallel(
        [(repo.name, c) for c in all_commits],
        get_changed_methods_for_commit,
        lambda data: (all_changed_methods_and_renamings.setdefault(data[0], data[1])),
        "Finding all commit diffs",
    )

    """iterate back through time, only handling commits once and when all their future has been handled"""
    head_commit_sha = repo.get_head_commit().hexsha

    todo_list: List[Tuple[str, FutureMapping]] = [(head_commit_sha, FutureMapping())]  # those that could be done next
    commit_futures: Dict[str, FutureMapping] = {}  # for each commit sha, which future comes after it?

    bar = log_progress(total=len(commit_children) + 1, desc="Iterating git Graph")
    while len(todo_list) > 0:
        bar.update()
        current_sha, prev_mapping = todo_list.pop()
        new_mapping = evo_new_analyze_commit(repo, current_sha, prev_mapping, result, all_changed_methods_and_renamings)
        commit_futures[current_sha] = new_mapping
        for parent in repo.get_commit(current_sha).parents:
            parent_children_shas = commit_children.get(parent.hexsha, [])
            if all(c in commit_futures for c in parent_children_shas):
                # this parent now has mappings for all its children! Let's handle it!
                todo_list.append((parent.hexsha, FutureMapping.create_for([commit_futures[c] for c in parent_children_shas])))
    bar.close()
    return result


def new_couple_by_same_commits(repo: LocalRepo, coupling_graph: ExplicitCouplingGraph):
    changes_per_commit = evo_calc_new(repo)
    # TODO consider commits
    #   within a time window (max one day?)
    #   or with similar messages (next to each other and named "foo" and "foo part 2")
    #  to be (somewhat) related, and couple methods of those within each other (somewhat)
    for changes in log_progress(list(changes_per_commit.values()), desc="creating coupling graph"):
        usable_changes = [d for d in changes if repo.get_tree().has_node(d)]
        if MIN_COMMIT_METHODS <= len(usable_changes) <= MAX_COMMIT_METHODS:
            score = 2 / len(changes)
            for f1, f2 in all_pairs(usable_changes):
                coupling_graph.add(f1, f2, score)
            for node in usable_changes:
                coupling_graph.add_support(node, 1)
