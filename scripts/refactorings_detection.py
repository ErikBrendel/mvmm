import json
import os
import subprocess
import tempfile

from cachier import cachier

from custom_types import *
from util import decode, minmax
from local_repo import LocalRepo

REFACTORING_MINER_CLI_PATH = os.getenv("REFACTORING_MINER_CLI_PATH", "/home/ebrendel/util/RefactoringMiner/cli")

# Those are too trivial to count as a refactoring that might fix a modularity violation, so we ignore them
IGNORED_REFACTORING_TYPES = {
    'Change Class Access Modifier',

    'Rename Package',
    'Rename Variable',
    'Rename Parameter',

    'Add Method Annotation',
    'Remove Method Annotation',
    'Change Method Annotation',

    'Add Class Annotation',
    'Remove Class Annotation',
    'Change Class Annotation',

    'Add Variable Annotation',
    'Remove Variable Annotation',
    'Change Variable Annotation',

    'Add Attribute Modifier',
    'Remove Attribute Modifier',
    'Change Attribute Modifier',

    'Change Attribute Type',

    'Add Class Modifier',
    'Remove Class Modifier',
    'Change Class Modifier',

    'Add Thrown Exception Type',
    'Remove Thrown Exception Type',
    'Change Thrown Exception Type',
}

BIG_REFACTORING_TYPES = {
    'Extract Class',
    'Extract Interface',
}


def is_hexsha(identifier: str) -> bool:
    try:
        int(identifier, 16)
        return True
    except ValueError:
        return False


@cachier()
def get_raw_refactorings_per_commit(repo: LocalRepo, old: str, new: str):
    temp_file_path = None
    try:
        temp_file_path = tempfile.mktemp(".json", "tmp-refactoring-miner-output-")
        args = [
            REFACTORING_MINER_CLI_PATH,
            "-bc" if is_hexsha(old) and is_hexsha(new) else "-bt",
            repo.path(),
            old,
            new,
            "-json",
            temp_file_path
        ]
        output = "\n".join(decode(line) for line in subprocess.Popen(args, stdout=subprocess.PIPE).stdout.readlines())
        print(output)
        with open(temp_file_path, "r") as result_file:
            json_object = json.load(result_file)["commits"]
        for commit in json_object:
            commit["refactorings"] = [r for r in commit["refactorings"] if r["type"] not in IGNORED_REFACTORING_TYPES]
        return json_object
    finally:
        if temp_file_path is not None:
            os.remove(temp_file_path)


print("Cached values at: " + get_raw_refactorings_per_commit.cache_dpath())


def _process_path(repo: LocalRepo, locations: List[Dict[str, Any]]) -> Set[str]:
    results: Set[str] = set()
    for location in locations:
        if location["codeElementType"] not in {"METHOD_DECLARATION", "FIELD_DECLARATION"}:
            continue
        file_node = repo.get_tree().find_node(location["filePath"])
        if file_node is not None:
            name = location["codeElement"].split("(")[0].split(" : ")[0].split(" ")[-1]
            concrete_nodes = file_node.find_descendants_of_name(name)
            for concrete_node in concrete_nodes:
                if concrete_node.get_simple_type() == "class" and location["codeElementType"] == "METHOD_DECLARATION":
                    concrete_node = concrete_node.children["constructor"]
                if concrete_node.get_simple_type() not in ["method", "attribute"]:
                    print("wow")
                results.add(concrete_node.get_path())
    return results


def get_all_refactoring_names(repo: LocalRepo, old: str, new: str):
    names: Set[str] = set()
    for c in get_raw_refactorings_per_commit(repo, old, new):
        for ref in c["refactorings"]:
            names.add(ref["type"])
    return names


def get_nodes_being_refactored_in_the_future(repo: LocalRepo):
    if repo.committish is None:
        raise Exception("This can only be done on repo states from the past. Please supply a branch, tag, or commit")
    old = repo.get_commit(repo.committish).hexsha
    new = repo.get_head_commit(True).hexsha

    results: Set[str] = set()
    for c in get_raw_refactorings_per_commit(repo, old, new):
        for ref in c["refactorings"]:
            results.update(_process_path(repo, ref["leftSideLocations"]))
    return results


def get_classes_being_refactored_in_the_future(repo: LocalRepo):
    return set([repo.get_tree().find_node(r).get_containing_class_node().get_path() for r in get_nodes_being_refactored_in_the_future(repo)])


if __name__ == "__main__":
    # res = get_processed_refactorings_data(LocalRepo("jfree/jfreechart"), "b7cccc63890b0789357a63c4f652dbcdbbfda177", "1f1a39ba311472fa9c9e19c4e5ad9221ece63185")
    # res = get_processed_refactorings_data(LocalRepo("jfree/jfreechart"), "v1.5.3", "master")
    # print(res)
    repo = LocalRepo("jfree/jfreechart:v1.5.3")
    results = get_classes_being_refactored_in_the_future(repo)
    print(results)
    # print(get_nodes_being_refactored_in_the_future(LocalRepo("jfree/jfreechart:b3d63c7148e5bbff621fd01e22db69189f09bf89")))
