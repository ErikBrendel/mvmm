
from refactorings_detection import *


if __name__ == "__main__":
    refactoring_weights: Dict[str, float] = {
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
        "Pull Up Method": 10,
        "Split Package": 10,
        "Move And Inline Method": 7,
        "Move And Rename Attribute": 6,
        "Push Down Method": 6,
        "Move Method": 5,
        "Pull Up Attribute": 5,
        "Extract Interface": 4,
        "Inline Method": 4,
        "Localize Parameter": 4,
        "Merge Attribute": 4,
        "Merge Parameter": 4,
        "Parameterize Variable": 4,
        "Replace Variable With Attribute": 4,
        "Change Attribute Type": 3,
        "Change Type Declaration Kind": 3,
        "Move Attribute": 3,
        "Parameterize Attribute": 3,
        "Push Down Attribute": 3,
        "Remove Parameter": 3,
        "Replace Attribute": 3,
        "Add Parameter": 2,
        "Change Parameter Type": 2,
        "Change Return Type": 2,
        "Change Variable Type": 2,
        "Extract Attribute": 2,
        "Merge Variable": 2,
        "Rename Package": 2,
        "Split Attribute": 2,
        "Split Variable": 2,
        "Add Attribute Annotation": 1,
        "Add Attribute Modifier": 1,
        "Add Class Annotation": 1,
        "Add Class Modifier": 1,
        "Add Method Modifier": 1,
        "Add Parameter Annotation": 1,
        "Add Variable Annotation": 1,
        "Change Attribute Access Modifier": 1,
        "Change Class Access Modifier": 1,
        "Change Method Access Modifier": 1,
        "Extract Variable": 1,
        "Modify Attribute Annotation": 1,
        "Modify Class Annotation": 1,
        "Modify Method Annotation": 1,
        "Modify Parameter Annotation": 1,
        "Move Package": 1,
        "Move Source Folder": 1,
        "Remove Attribute Annotation": 1,
        "Remove Attribute Modifier": 1,
        "Remove Class Annotation": 1,
        "Remove Class Modifier": 1,
        "Remove Method Annotation": 1,
        "Remove Method Modifier": 1,
        "Remove Parameter Annotation": 1,
        "Remove Variable Annotation": 1,
        "Remove Variable Modifier": 1,
        "Rename Attribute": 1,
        "Rename Class": 1,
        "Rename Method": 1,
        "Rename Parameter": 1,
        "Rename Variable": 1,
        "Replace Attribute With Variable": 1,
        "Split Parameter": 1,
        "Add Method Annotation": 0,
        "Add Parameter Modifier": 0,
        "Add Thrown Exception Type": 0,
        "Add Variable Modifier": 0,
        "Change Thrown Exception Type": 0,
        "Encapsulate Attribute": 0,
        "Inline Variable": 0,
        "Remove Parameter Modifier": 0,
        "Remove Thrown Exception Type": 0,
        "Reorder Parameter": 0,
        "Replace Anonymous With Lambda": 0,
        "Replace Loop With Pipeline": 0,
    }
    from repos import repos_and_versions
    try:
        for new_repo_name, old_versions in repos_and_versions:
            new_repo = LocalRepo.for_name(new_repo_name)
            new_head = new_repo.get_head_commit().hexsha
            for old_version in old_versions:
                old_repo = new_repo.get_old_version(old_version)
                old_head = old_repo.get_head_commit().hexsha
                for commit in get_raw_refactorings_per_commit(new_repo, old_head, new_head):
                    for ref in commit["refactorings"]:
                        type_name = ref["type"]
                        while type_name not in refactoring_weights.keys():
                            print(f"""Which weight should "{type_name}" have?""")
                            print(f"""Example: {ref['description']}""")
                            refactoring_weights[type_name] = int(input(">>>"))
    except:
        pass
    all_results = [(v, k) for k, v in refactoring_weights.items()]
    all_results.sort(key=lambda v_k: (-v_k[0], v_k[1]))
    print("""    refactoring_weights: Dict[str, float] = {""")
    for v, k in all_results:
        print(f"""        "{k}": {v},""")
    print("""    }""")
