from util import *
from local_repo import *

MAX_COMMIT_FILES = 50
from timeit import default_timer as timer

# needs to be separate so that multiprocessing lib can find it
def get_commit_diff(commit_hash, repo):
    # repo_tree = repo.get_tree()
    
    def walk_tree_cursor(cursor, prefix, content_bytes, node_handler):
        if not cursor.node.is_named:
            return
        def node_text(node):
            return decode(content_bytes[node.start_byte:node.end_byte])
            
        # cursor.current_field_name() is the role that this node has in its parent
        tree_node_names = []  # TODO keep in sync with structural and linguistic view as well as RepoFile class
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
    
    def walk_tree(tree, content_bytes, base_path) -> RepoTree:
        """ node_handler gets the current logic-path and node for each ast node"""
        try:
            found_nodes = RepoTree(None, "")
            def handle(logic_path, ts_node):
                found_nodes.register(logic_path, ts_node)
            walk_tree_cursor(tree.walk(), base_path, content_bytes, handle)
            return found_nodes
        except Exception as e:
            print("Failed to parse file:", base_path, "Error:", e)
            pdb.set_trace()
            return None
    
    error_query = JA_LANGUAGE.query("(ERROR) @err")
    def _has_error(tree) -> List[str]:
        errors = error_query.captures(tree.root_node)
        return len(errors) > 1
    
    def blob_diff(diff) -> List[str]:
        # pdb.set_trace()
        if diff.a_blob is None:
            return [diff.b_path] # newly created
        elif diff.b_blob is None:
            return [diff.a_path] # deleted
        path = diff.a_path
        # if not repo_tree.has_node(path):
        #     return []  # ignore changed files that are not part of the interesting project structure
        if not path.endswith("." + repo.type_extension()):
            return [path]
        a_content = diff.a_blob.data_stream.read()
        if should_skip_file(a_content):
            return []
        b_content = diff.b_blob.data_stream.read()
        if should_skip_file(b_content):
            return []
        a_tree = java_parser.parse(a_content)
        b_tree = java_parser.parse(b_content)
        if _has_error(a_tree) or _has_error(b_tree):
            return [path] # I guess just the file changed, no more details available
        a_repo_tree = walk_tree(a_tree, a_content, path)
        if a_repo_tree is None:
            return [path]
        b_repo_tree = walk_tree(b_tree, b_content, path)
        if b_repo_tree is None:
            return [path]
        return a_repo_tree.calculate_diff_to(b_repo_tree, a_content, b_content)
    
    c1 = repo.get_commit(commit_hash)
    if len(c1.parents) == 1:
        c2 = c1.parents[0]
        # t4 = timer()
        diff = c1.diff(c2)
        # t5 = timer()
        if len(diff) > MAX_COMMIT_FILES or len(diff) <= 1:  # this is duplicated here for performance
            return None
        diffs = [result for d in diff for result in blob_diff(d)]  #  if repo_tree.has_node(result)
        # t6 = timer()
        # print("Diff: " + str(len(diff)) + " / " + str(len(diffs)) + " changes")
        
        # print("Time taken (ms):", round((t5-t4)*1000), "(getting git diff)", round((t6-t5)*1000), "(parsing sub-file diffs)", round((t6-t4)*1000), "(total)")
    elif len(c1.parents) == 2:
        return None  # TODO how to do sub-file diffs for merge commits?
        #c2 = c1.parents[0]
        #diff_1 = c1.diff(c2)
        #c3 = c1.parents[1]
        #diff_2 = c1.diff(c3)

        #diffs_1 = [ d.a_path for d in diff_1 ]
        #diffs_2 = [ d.a_path for d in diff_2 ]
        #diffs = list(set(diffs_1).intersection(set(diffs_2)))
    else:
        return None
    if len(diffs) > MAX_COMMIT_FILES or len(diffs) <= 1:
        return None
    return diffs

