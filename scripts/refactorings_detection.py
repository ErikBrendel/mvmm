import json
import os
import subprocess
import tempfile
from collections import defaultdict

from cachier import cachier

from custom_types import *
from util import decode, minmax, SerializedWrap
from local_repo import LocalRepo

# To set up repository mining, do the following:
# 0. make sure to have java installed (version 14 did not work, 11 is fine)
# 1. clone the repo from https://github.com/tsantalis/RefactoringMiner.git to your local machine
# 2. If this issue is not yet resolved: https://github.com/tsantalis/RefactoringMiner/issues/222
#    - Open the file RefactoringMiner/src/org/refactoringminer/util/GitServiceImpl.java
#    - edit method openRepository(String) (line 109), and replace '.setGitDir(new File(folder, ".git"))' with '.setGitDir(folder)'
# 3. install the command line program like explained on the github page:
#    - execute './gradlew distZip'
#    - go to 'build/distributions/' and unzip the RefactoringMiner zip
# Your executable is 'bin/RefactoringMiner' of that zip. Create a symlink if you like, and pass the path to this script here
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


@cachier(separate_files=True)
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


# print("Cached values at: " + get_raw_refactorings_per_commit.cache_dpath())


def refactoring_process_path(repo: LocalRepo, locations: List[Dict[str, Any]]) -> Set[str]:
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
                    if "constructor" not in concrete_node.children:
                        print("Cannot find the constructor in " + location["filePath"])
                        print(location)
                        continue
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


def get_nodes_being_refactored_in_the_future(repo: LocalRepo, old_version: str) -> Set[str]:
    old = repo.get_commit(old_version).hexsha
    new = repo.get_head_commit().hexsha

    results: Set[str] = set()
    for c in get_raw_refactorings_per_commit(repo, old, new):
        for ref in c["refactorings"]:
            results.update(refactoring_process_path(repo, ref["leftSideLocations"]))
    return results


def get_classes_being_refactored_in_the_future(repo: LocalRepo, old_version: str, only_verified_ones: bool = False) -> Set[str]:
    if only_verified_ones:
        return set(class_name for class_name, verified in get_confirmed_class_refactorings_dict(repo.name, old_version).data.items() if verified)
    else:
        return set([repo.get_tree().find_node(r).get_containing_class_node().get_path()
                    for r in get_nodes_being_refactored_in_the_future(repo, old_version)])


def get_classes_being_refactored_in_the_future_heuristically_filtered(new_repo: LocalRepo, old_version: str):
    old_repo = new_repo.get_old_version(old_version)

    old_tree = old_repo.get_tree()
    old = old_repo.get_head_commit().hexsha
    new = new_repo.get_head_commit().hexsha
    results: Dict[str, List[str]] = defaultdict(lambda: [])  # old class, old other class, type_name
    for commit in get_raw_refactorings_per_commit(new_repo, old, new):
        for ref in commit["refactorings"]:
            type_name = ref["type"]
            if type_name not in {
                "Add Parameter Modifier",
                "Change Attribute Access Modifier",
                "Change Method Access Modifier",
                "Inline Variable",
                "Modify Method Annotation",
                "Remove Parameter Modifier",
                "Reorder Parameter",
            }:
                left_side_paths = set(refactoring_process_path(old_repo, ref["leftSideLocations"]))
                left_side_class_paths = set(old_tree.find_node(left_side_path).get_containing_class_node().get_path() for left_side_path in left_side_paths)
                for left_side_class_path in left_side_class_paths:
                    results[left_side_class_path].append(type_name)
    refactoring_weights: Dict[str, float] = {
        "Extract Method": 3,
        "Extract And Move Method": 4,
        "Inline Method": 2,
        "Move And Rename Method": 3,
        "Move Method": 3,

        "Merge Parameter": 2,
    }
    return [name for name, refactorings in results.items() if sum(refactoring_weights.get(r, 1) for r in refactorings) >= 5]


def get_confirmed_class_refactorings_dict(repo_name: str, old_version: str):
    info = repo_name + "::" + old_version
    return SerializedWrap(dict(), f"""../refactorings/confirmed_{info.replace("/", "_")}_.pickle""")  # Dict from class_path to bool


if __name__ == "__main__":
    # res = get_processed_refactorings_data(LocalRepo("jfree/jfreechart"), "b7cccc63890b0789357a63c4f652dbcdbbfda177", "1f1a39ba311472fa9c9e19c4e5ad9221ece63185")
    # res = get_processed_refactorings_data(LocalRepo("jfree/jfreechart"), "v1.5.3", "master")
    # print(res)
    repo = LocalRepo("jfree/jfreechart:v1.5.3")
    results = get_classes_being_refactored_in_the_future(repo, "v1.5.0")
    print(results)
    # print(get_nodes_being_refactored_in_the_future(LocalRepo("jfree/jfreechart:b3d63c7148e5bbff621fd01e22db69189f09bf89")))
