import json
import os
import subprocess
import tempfile
from collections import defaultdict

from cachier import cachier

from custom_types import *
from util import decode
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


REFACTORING_WEIGHTS: Dict[str, int] = {
    "Collapse Hierarchy": 10,
    "Extract And Move Method": 10,
    "Extract Class": 10,
    "Extract Method": 10,
    "Extract Subclass": 10,
    "Extract Superclass": 10,
    "Merge Package": 10,
    "Move And Rename Class": 10,
    "Move And Rename Method": 10,
    "Move Class": 10,
    "Split Package": 10,
    "Move And Inline Method": 6,
    "Move And Rename Attribute": 6,
    "Move Method": 6,
    "Pull Up Method": 6,
    "Push Down Method": 6,
    "Extract Interface": 4,
    "Inline Method": 4,
    "Localize Parameter": 4,
    "Merge Attribute": 4,
    "Merge Parameter": 4,
    "Parameterize Variable": 4,
    "Replace Variable With Attribute": 4,
    "Change Attribute Type": 3,
    "Change Type Declaration Kind": 3,
    "Extract Attribute": 3,
    "Move Attribute": 3,
    "Parameterize Attribute": 3,
    "Pull Up Attribute": 3,
    "Push Down Attribute": 3,
    "Replace Attribute": 3,
    "* Parameter": 2,
    "Change Parameter Type": 2,
    "Change Return Type": 2,
    "Change Variable Type": 2,
    "Merge Variable": 2,
    "Rename Package": 2,
    "Split Attribute": 2,
    "Split Variable": 2,
    "* Attribute Annotation": 1,
    "* Class Annotation": 1,
    "* Method Annotation": 1,
    "* Parameter Annotation": 1,
    "* Variable Annotation": 1,
    "Change Attribute Access Modifier": 1,
    "Change Class Access Modifier": 1,
    "Change Method Access Modifier": 1,
    "Extract Variable": 1,
    "Move Package": 1,
    "Move Source Folder": 1,
    "Rename Attribute": 1,
    "Rename Class": 1,
    "Rename Method": 1,
    "Rename Parameter": 1,
    "Rename Variable": 1,
    "Replace Attribute With Variable": 1,
    "Split Parameter": 1,
    "* Attribute Modifier": 0,
    "* Class Modifier": 0,
    "* Method Modifier": 0,
    "* Parameter Modifier": 0,
    "* Thrown Exception Type": 0,
    "* Variable Modifier": 0,
    "Encapsulate Attribute": 0,
    "Inline Variable": 0,
    "Reorder Parameter": 0,
    "Replace Anonymous With Lambda": 0,
    "Replace Loop With Pipeline": 0,
}
MIN_REFACTORING_WEIGHT = 1
def get_refactoring_weight(type_name: str) -> int:
    if type_name not in REFACTORING_WEIGHTS and any(type_name.startswith(w + " ") for w in ["Add", "Remove", "Change", "Modify"]):
        type_name = "* " + type_name.split(" ", 1)[1]
    if type_name not in REFACTORING_WEIGHTS:
        print(f"UNKNOWN REFACTORING TYPE: {type_name} (it will be ignored)")
        return 0
    return 1 if REFACTORING_WEIGHTS[type_name] >= 6 else 0


def is_hexsha(identifier: str) -> bool:
    try:
        int(identifier, 16)
        return True
    except ValueError:
        return False


@cachier(separate_files=True)
def get_raw_refactorings_per_commit(repo: LocalRepo, old: str, new: str):
    print(f"Starting refactoring analysis for {repo.name} from {old} to {new}...")
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
            return json.load(result_file)["commits"]
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
                        # can happen when a later version of the class has a constructor, and then refactorings happen within it
                        # print("Cannot find the constructor in " + location["filePath"])
                        continue
                    concrete_node = concrete_node.children["constructor"]
                if concrete_node.get_simple_type() not in ["method", "attribute"]:
                    print("wow")
                results.add(concrete_node.get_path())
    return results


def get_classes_being_refactored_in_the_future(new_repo: LocalRepo, old_version: str, use_filter: bool = True) -> Set[str]:
    old_repo = new_repo.get_old_version(old_version)
    old_tree = old_repo.get_tree()
    old = old_repo.get_head_commit().hexsha
    new = new_repo.get_head_commit().hexsha

    results: Dict[str, List[str]] = defaultdict(lambda: [])  # old class -> refactoring type names
    for commit in get_raw_refactorings_per_commit(new_repo, old, new):
        for ref in commit["refactorings"]:
            type_name = ref["type"]
            old_paths = refactoring_process_path(old_repo, ref["leftSideLocations"]) | refactoring_process_path(old_repo, ref["rightSideLocations"])
            old_class_paths = set(old_tree.find_node(old_path).get_containing_class_node().get_path() for old_path in old_paths)
            for old_class_path in old_class_paths:
                results[old_class_path].append(type_name)
    return set(
        name for name, refactorings in results.items()
        if not use_filter or sum(get_refactoring_weight(r) for r in refactorings) >= MIN_REFACTORING_WEIGHT
    )


if __name__ == "__main__":
    # res = get_processed_refactorings_data(LocalRepo.for_name("jfree/jfreechart"), "b7cccc63890b0789357a63c4f652dbcdbbfda177", "1f1a39ba311472fa9c9e19c4e5ad9221ece63185")
    # res = get_processed_refactorings_data(LocalRepo.for_name("jfree/jfreechart"), "v1.5.3", "master")
    # print(res)
    print(get_classes_being_refactored_in_the_future(LocalRepo.for_name("jfree/jfreechart:v1.5.3"), "v1.5.0"))
