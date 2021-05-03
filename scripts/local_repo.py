from git import Git, Repo, RemoteProgress
import os
import subprocess
import pdb
from typing import List
import re

from util import *
from parsing import *

REPO_URL_START = "https://github.com/"
REPO_URL_END = ".git"
REPO_CLONE_PATH = "../repos/"
ADD_LINE_NUMBER_TO_LINK = True


# https://gitpython.readthedocs.io/en/stable/reference.html
class LocalRepo:
    def __init__(self, name):
        self.name = name
        self.repo_name = "/".join(self.name.split("/")[:2])
        self.sub_dir = None if len(self.repo_name) == len(self.name) else self.name[len(self.repo_name) + 1:]
        self.tree = None
        if not self.is_cloned():
            print("cloning " + self.repo_name + ", this may take a while...")
            self.clone()
        self.repo = Repo(self.path())
        self.url_cache = {}
        self.path_to_file_cache = None

    def update(self):
        print("updating " + self.repo_name + "...")
        self.pull()
        print("Repo is up to date!")

    def pull(self):
        # https://github.com/gitpython-developers/GitPython/issues/296#issuecomment-449769231
        self.repo.remote().fetch("+refs/heads/*:refs/heads/*")

    def clone(self):
        Repo.clone_from(self.url(), self.path(), None, None, ["--bare"])

    def is_cloned(self):
        return os.path.isdir(self.path())

    def path(self):
        return REPO_CLONE_PATH + self.repo_name

    def url(self):
        return REPO_URL_START + self.repo_name + REPO_URL_END

    def url_for(self, path):
        if path in self.url_cache:
            return self.url_cache[path]

        ending = "." + self.type_extension()
        file_path = path
        if ending in file_path:
            file_path = file_path[0:file_path.index(ending) + len(ending)]
        file_url = REPO_URL_START + self.repo_name + "/blob/master/" + file_path
        if ADD_LINE_NUMBER_TO_LINK:
            file = self.get_file(file_path)
            if file is None:
                print("Cannot find file anymore:", file_path)
                self.url_cache[path] = file_url
                return file_url
            target_node = self.get_tree().find_node(path)
            if target_node is None or target_node.ts_node is None:
                self.url_cache[path] = file_url
                return file_url
            before_content = decode(file.get_content()[:target_node.ts_node.start_byte])
            result_url = file_url + "#L" + str(len(before_content.split("\n")))
            self.url_cache[path] = result_url
            return result_url
        else:
            self.url_cache[path] = file_url
            return file_url

    def type_extension(self):
        return "java"  # return the file extension that the files of your language have

    def get_file(self, path):
        if self.path_to_file_cache is None:
            self.path_to_file_cache = {}
            for repo_file in self.get_all_files():
                self.path_to_file_cache[repo_file.get_path()] = repo_file
        return self.path_to_file_cache.get(path)

    def get_file_objects(self, commit_hash=None):
        commit = None
        if commit_hash is None:
            commit = self.repo.head.commit
        else:
            commit = self.repo.commit(commit_hash)
        ending = "." + self.type_extension()
        files = []
        for git_object in commit.tree.traverse():
            if git_object.type == "blob":
                if git_object.name.endswith(ending) and not git_object.name.endswith("module-info.java"):
                    files.append(git_object)
        return files

    def get_all_files(self) -> List['RepoFile']:
        if self.sub_dir is None:
            return [RepoFile(self, o) for o in self.get_file_objects()]
        else:
            return [RepoFile(self, o) for o in self.get_file_objects() if o.path.startswith(self.sub_dir)]

    def get_all_interesting_files(self):
        test_skipper = DirectoryExclusionTracker(['test', 'tests', 'samples', 'example', 'examples'])
        all_files = self.get_all_files()
        result = [file for file in all_files if not (file.should_get_skipped() or test_skipper.should_get_skipped(file.get_path()))]
        print("Analyzing", len(result), "of", len(all_files), "files, the rest was skipped as tests or samples")
        print("Skipped", len(test_skipper.get_skipped_roots()), "test and sample roots:", test_skipper.get_skipped_roots())
        return result

    def get_file_object_content(self, git_object):
        return git_object.data_stream.read()

    def get_all_commits(self):
        return Git(self.path()).log("--pretty=%H").split("\n")

    def get_commit(self, sha):
        return self.repo.commit(sha)

    def get_tree(self):
        if self.tree is None:
            self.tree = RepoTree.init_from_repo(self)
        return self.tree

    # to allow for pickling, see https://stackoverflow.com/a/2345985/4354423
    def __getstate__(self):
        """Return state values to be pickled."""
        return (self.name, self.repo_name, self.sub_dir, self.repo)

    def __setstate__(self, state):
        """Restore state from the unpickled state values."""
        self.name, self.repo_name, self.sub_dir, self.repo = state


def should_skip_file(content_bytes):
    content_str = decode(content_bytes)
    lines = content_str.split("\n")
    if len(lines) >= 5000:
        return True
    max_line_length = max((len(line) for line in lines))
    if max_line_length >= 5000:
        return True
    return False


class RepoFile:
    def __init__(self, repo, file_obj):
        self.repo = repo
        self.file_obj = file_obj
        self.content = None
        self.tree = None

    def should_get_skipped(self):
        return should_skip_file(self.get_content())

    def get_path(self):
        return self.file_obj.path

    def get_content(self):
        if self.content is None:
            self.content = self.repo.get_file_object_content(self.file_obj)
        return self.content

    def get_content_without_copyright(self):
        tree = self.get_tree()
        first_root_child = tree.root_node.children[0]
        if first_root_child.type == "comment":
            return decode(self.get_content()[first_root_child.end_byte:])
        else:
            return decode(self.get_content())

    def get_repo_tree_node(self):
        return self.repo.get_tree().find_node(self.get_path())

    def get_tree(self):
        if self.tree is None:
            self.tree = java_parser.parse(self.get_content())
        return self.tree

    def node_text(self, node):
        return decode(self.get_content()[node.start_byte:node.end_byte])

    def walk_tree(self, node_handler):
        """ node_handler gets the current logic-path and node for each ast node"""
        try:
            self.walk_tree_cursor(self.get_tree().walk(), self.get_path(), node_handler)
        except Exception as e:
            print("Failed to parse file:", self.get_path(), "Error:", e)

    def walk_tree_cursor(self, cursor, prefix, node_handler):
        if not cursor.node.is_named:
            return
        # cursor.current_field_name() is the role that this node has in its parent

        # TODO keep in sync with all view code
        tree_node_names = []
        if cursor.node.type == "class_declaration" or cursor.node.type == "interface_declaration" or cursor.node.type == "enum_declaration":
            tree_node_names.append(self.node_text(cursor.node.child_by_field_name("name")))
        elif cursor.node.type == "field_declaration":
            declarators = [child for child in cursor.node.children if child.type == "variable_declarator"]
            tree_node_names += [self.node_text(d.child_by_field_name("name")) for d in declarators]
        elif cursor.node.type == "method_declaration":
            tree_node_names.append(self.node_text(cursor.node.child_by_field_name("name")))
        elif cursor.node.type == "constructor_declaration":
            tree_node_names.append("constructor")

        for tree_node_name in tree_node_names:
            node_handler(prefix + "/" + tree_node_name, cursor.node)
        if len(tree_node_names) > 0:
            prefix = prefix + "/" + tree_node_names[0]

        if cursor.goto_first_child():
            self.walk_tree_cursor(cursor, prefix, node_handler)
            while cursor.goto_next_sibling():
                self.walk_tree_cursor(cursor, prefix, node_handler)
            cursor.goto_parent()


class RepoTree:

    @staticmethod
    def init_from_repo(repo) -> 'RepoTree':
        found_nodes = RepoTree(None, "")
        files = repo.get_all_interesting_files()
        for file in files:
            def handle(logic_path, ts_node):
                found_nodes.register(logic_path, ts_node)

            file.walk_tree(handle)
        print("Found " + str(found_nodes.node_count()) + " directories, files, classes, methods and fields!")

        # with open("../debug-tree.json", "w") as outfile:
        #     outfile.write(found_nodes.to_json())
        return found_nodes

    def __init__(self, parent, name, ts_node=None):
        self.parent = parent
        self.name = name
        if parent is not None and len(name) == 0:
            print("I have no name! I live in: " + parent.get_path())
            pdb.set_trace()
        self.ts_node = ts_node
        self.children = {}

    # to allow for pickling (for multiprocessing), see https://stackoverflow.com/a/2345985/4354423
    def __getstate__(self):
        """Return state values to be pickled."""  # ignore ts_node, cannot be pickled
        return (self.parent, self.name, self.children)

    def __setstate__(self, state):
        """Restore state from the unpickled state values."""
        self.parent, self.name, self.children = state

    def get_root(self):
        if self.parent is None:
            return self
        return self.parent.get_root()

    def get_path(self):
        if self.parent is None or len(self.parent.name) == 0:
            return self.name
        else:
            # return "/".join(x.name for x in self.self_and_parents_gen())
            return self.parent.get_path() + "/" + self.name

    def self_and_parents_gen(self):
        current = self
        while current is not None:
            yield current
            current = current.parent

    def register(self, path, ts_node):
        self.register_list(path.split("/"), ts_node)

    def register_list(self, path_segments, ts_node):
        if len(path_segments) > 1:
            self.register_child(path_segments[0], None).register_list(path_segments[1:], ts_node)
        elif len(path_segments) == 1:
            self.register_child(path_segments[0], ts_node)
        else:
            raise Exception("Should not reach here!")

    def register_child(self, name, ts_node) -> 'RepoTree':
        if not name in self.children:
            self.children[name] = RepoTree(self, name, ts_node)
        else:
            if ts_node is not None and self.children[name].ts_node is not None and ts_node != self.children[name].ts_node:
                pass  # pdb.set_trace()  # TODO this is a name collision (e.g. java method overloading) - we should handle this somehow!!!
        return self.children[name]

    def has_node(self, path):
        return self.find_node(path) is not None

    def find_node(self, path) -> 'RepoTree':
        if (len(path) == 0):
            return self
        else:
            return self.find_node_list(path.split("/"))

    def find_node_list(self, path_segments) -> 'RepoTree':
        if len(path_segments) == 0:
            return self
        elif path_segments[0] in self.children:
            return self.children[path_segments[0]].find_node_list(path_segments[1:])
        else:
            return None

    def get_type(self) -> str:
        if self.ts_node is None:
            return None
        node_type = self.ts_node.type
        if node_type.endswith("_declaration"):
            node_type = node_type[0:-len("_declaration")]
        return node_type

    def get_children_of_type(self, type_str) -> List['RepoTree']:
        return [c for c in self.children.values() if c.get_type() == type_str]

    def get_descendants_of_type(self, type_str) -> List['RepoTree']:
        children_descendants = [child.get_descendants_of_type(type_str) for child in self.children.values()]
        return self.get_children_of_type(type_str) + [descendant for sublist in children_descendants for descendant in sublist]

    def get_text(self, file):
        if self.ts_node is None:
            return None
        return file.node_text(self.ts_node)

    def get_preceding_comment_text(self, file):
        if self.parent is None or self.parent.ts_node is None:
            return None
        # search down from parent ts_node until we find one that has my own ts_node as child
        parent_ts_node = self.parent.ts_node  # might be too high, since ts_nodes are more finde-grained than this tree
        while not self.ts_node in parent_ts_node.children:
            found_next = False
            for child in parent_ts_node.children:
                if child.start_byte <= self.ts_node.start_byte and child.end_byte >= self.ts_node.end_byte:
                    parent_ts_node = child
                    found_next = True
                    break
            if not found_next:
                return None
        index_in_parent = parent_ts_node.children.index(self.ts_node)
        if index_in_parent < 1:
            return None
        previous_sibling = parent_ts_node.children[index_in_parent - 1]
        if previous_sibling.type != "comment":
            return None
        return file.node_text(previous_sibling)

    def get_comment_and_own_text(self, file):
        return (self.get_preceding_comment_text(file) or "") + "\n" + self.get_text(file)

    def get_line_span(self):
        if self.ts_node is None:
            return None
        return self.ts_node.end_point[0] - self.ts_node.start_point[0] + 1

    def has(self, path) -> bool:
        return self.has_list(path.split("/"))

    def has_list(self, path_segments) -> bool:
        if not self.has_child(path_segments[0]):
            return False
        if len(path_segments) == 1:
            return True
        return self.children(path_segments[0]).has_list(path_segments[1:])

    def has_child(self, name) -> bool:
        return name in self.children

    def effective_children(self):
        """see is_transparent"""
        result = {}
        for name, child in self.children.items():
            if child.is_transparent():
                result.update(child.effective_children())
            result[name] = child
        return result

    def is_transparent(self):
        """when searching for the effective children of a node, the children of transparent children will be included (and recursively down)"""
        """a node is transparent when for the logic of finding things, it does not count as a separate layer. In Java, file nodes are such a thing"""
        return self.name.endswith(".java")

    def to_json(self) -> str:
        if len(self.children) == 0:
            return '{"name":"' + self.name + '"}'
        else:
            child_json = ",".join([c.to_json() for c in self.children.values()])
            return '{"name":"' + self.name + '","children":[' + child_json + ']}'

    def node_count(self) -> int:
        return sum([c.node_count() for c in self.children.values()]) + 1

    def calculate_diff_to(self, other: 'RepoTree', my_content_bytes, other_content_bytes) -> List[str]:
        """return list of pathes of minimal nodes that have changed content or are unmappable"""
        # assumption: self.name == other.name
        results = []
        for my_child in self.children.values():
            if other.has_child(my_child.name):
                results += my_child.calculate_diff_to(other.children[my_child.name], my_content_bytes, other_content_bytes)
            else:
                results.append(my_child.get_path())
        for other_child in other.children.values():
            if not self.has_child(other_child.name):
                results.append(other_child.get_path())
        if len(results) == 0 and self.ts_node is not None and other.ts_node is not None:  # TODO why can they be None?
            # if self.ts_node.
            # TODO: insteadcheck if the treesitter trees are equal!
            my_content = decode(my_content_bytes[self.ts_node.start_byte:self.ts_node.end_byte])
            other_content = decode(other_content_bytes[other.ts_node.start_byte:other.ts_node.end_byte])
            if my_content != other_content:
                results.append(self.get_path())
        return results