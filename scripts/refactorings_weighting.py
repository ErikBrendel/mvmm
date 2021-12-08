
from refactorings_detection import *


if __name__ == "__main__":
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
                        type_name_star = type_name
                        if any(type_name.startswith(w + " ") for w in ["Add", "Remove", "Change", "Modify"]):
                            type_name_star = "* " + type_name.split(" ", 1)[1]
                        if type_name not in REFACTORING_WEIGHTS.keys() and type_name_star not in REFACTORING_WEIGHTS.keys():
                            print(f"""Which weight should "{type_name}" have?""")
                            print(f"""Example: {ref['description']}""")
                            REFACTORING_WEIGHTS[type_name] = int(input(">>>"))
    except:
        pass
    all_results = [(v, k) for k, v in REFACTORING_WEIGHTS.items()]
    all_results.sort(key=lambda v_k: (-v_k[0], v_k[1]))
    print("""    refactoring_weights: Dict[str, float] = {""")
    for v, k in all_results:
        print(f"""        "{k}": {v},""")
    print("""    }""")

    print("\n" * 3)

    extraordinary_merges = [
        ({"Pull Up Method", "Push Down Method"}, "Pull Up/Push Down Method"),
        ({"Pull Up Attribute", "Push Down Attribute"}, "Pull Up/Push Down Attribute"),
        ({"Split Package", "Merge Package"}, "Split/Merge Package"),
        ({"Move Attribute", "Parameterize Attribute", "Replace Attribute", "Extract Attribute"}, None),
        ({"Move And Inline Method", "Move Method"}, "Move (And Inline) Method"),
        ({"Move Package", "Move Source Folder"}, "Move Package/Source Folder"),
    ]

    print(fr"""    \toprule""")
    print(fr"""    Refactoring Name & Weight\\""")
    for w in range(10, -1, -1):
        names = sorted([k for k, v in REFACTORING_WEIGHTS.items() if v == w])
        if len(names) == 0:
            continue
        print(fr"""    \midrule""")
        last_names: List[List[str]] = []
        results = []

        def flush():
            if len(last_names) == 1:
                results.append(" ".join(last_names[0]))
            elif len(last_names) > 0:
                results.append(" ".join(["/".join(sorted(set(x))) for x in zip(*last_names)]))
            last_names.clear()

        for merge, replacement in extraordinary_merges:
            if all(name in names for name in merge):
                if replacement is None:
                    for name in sorted(merge):
                        last_names.append(name.split(" "))
                    flush()
                else:
                    results.append(replacement)
                names = [name for name in names if name not in merge]

        for name in names:
            name_parts = name.split(" ")
            if len(last_names) > 0:
                equal_word_count = len(name_parts) == len(last_names[0])
                same_first_word = name_parts[0] == last_names[0][0]
                one_word_diff = sum(part != last_part for part, last_part in zip(name_parts, last_names[0])) == 1
                common_merge = same_first_word and one_word_diff
                special_merge = any((name in m and " ".join(last_names[0]) in m) for m in extraordinary_merges)
                should_be_merged = equal_word_count and (common_merge or special_merge)
                if not should_be_merged:
                    flush()
            last_names.append(name_parts)
        flush()
        w_str = w if w == 10 else f"~~{w}"
        for agg_name in sorted(results):
            if agg_name.startswith("* "):
                agg_name = "Modify " + agg_name[len("* "):]
            print(fr"""    {agg_name} & ${w_str}$ \\""")
    print(fr"""    \bottomrule""")
