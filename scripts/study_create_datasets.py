from study_common import *
from analysis import *
import os.path

repos = [
    "junit-team/junit4",
    "jfree/jfreechart",
    "nextcloud/android",
    "skylot/jadx",
    "vanzin/jEdit",
    "jenkinsci/jenkins",
    "libgdx/libgdx",
]
ENTRIES_PER_PATTERN = 4


@cachier()
def get_evo_changes(repo: str) -> Dict[str, List[str]]:
    return evo_calc_new(LocalRepo(repo))


def get_commit_metrics(commit: Commit) -> COMMIT_CHANGES_TYPE:
    parent_diffs = get_commit_diffs(commit, create_patch=True)
    changed_files = set()
    additions = 0
    deletions = 0
    for diffs in parent_diffs:
        for diff in diffs:
            changed_files.add(diff.a_path)
            changed_files.add(diff.b_path)
            patch_lines = decode(diff.diff).split("\n")
            for line in patch_lines:
                if line.startswith("+"):
                    additions += 1
                elif line.startswith("-"):
                    deletions += 1
    return len(changed_files), additions, deletions


# @cachier()
def find_commits(repo: str, m0: str, m1: str) -> COMMITS_TYPE:
    r = LocalRepo(repo)
    result: COMMITS_TYPE = []
    for hexsha, methods in get_evo_changes(repo).items():
        m0_match = m0 in methods
        m1_match = m1 in methods
        if m0_match or m1_match:
            commit = r.get_commit(hexsha)
            message = commit.message.split("\n")[0]
            result.append((message, commit.author.name, commit.committed_date, hexsha, get_commit_metrics(commit), m0_match, m1_match))
    return result


def make_method_data(r: LocalRepo, method_path: str) -> METHOD_TYPE:
    method_node = r.get_tree().find_node(method_path)
    file_path = method_node.get_containing_file_node().get_path()
    file = next(f for f in r.get_all_files() if f.get_path() == file_path)
    content = method_node.get_comment_and_own_text_formatted(file).strip()
    return method_path, content


def get_score(pattern: PatternType, result: BRS_DATA_TYPE):
    weights = make_sort_weights(pattern)
    return sum(w * e * e for w, e in zip(weights, result[0]))


def main():
    for repo in repos:
        study_dataset_result_path = STUDY_RESULTS_PATH + "dataset-" + repo.replace("/", "_") + '.pickle'
        if os.path.isfile(study_dataset_result_path):
            print("Skipping existing " + repo)
            continue
        print(pyfiglet.figlet_format(repo))
        r = LocalRepo(repo)
        results = analyze_disagreements(r, ALL_VIEWS, [p for p, *_ in TAXONOMY], "methods")

        # if a pair of methods appears in multiple taxonomy queries, only assign it to the one where it matched the most
        # algo:
        # first, get the list of results for all the tax patterns
        # then, while there is still a category which has not enough study entries:
        #  pick from those the one where the top result has the highest matching score
        #  remove that top result from the list, add it to the study, mark this pair as being used, and those individual methods as being used for that tax category

        taxonomy_results: List[List[BRS_DATA_TYPE]] = []
        for ti, res in ((cast(int, ti), cast(BestResultsSet, res)) for ti, res in log_progress([x for x in enumerate(results)], desc="Getting Data")):
            res.get_best(make_sort_weights(TAXONOMY[ti][0]))
            taxonomy_results.append(res.data[:])

        active_tax_categories = set(range(len(TAXONOMY)))
        taxonomy_picked_results: List[List[STUDY_ENTRY_TYPE]] = [[] for _ in TAXONOMY]
        used_method_pairs = set()
        used_methods_per_category = [set() for _ in TAXONOMY]
        progress_bar = log_progress(total=ENTRIES_PER_PATTERN * len(TAXONOMY), desc="Creating Dataset")
        while len(active_tax_categories) > 0:
            progress_bar.update()
            ti = max(active_tax_categories, key=lambda ti: get_score(TAXONOMY[ti][0], taxonomy_results[ti][0]))
            while len(taxonomy_results[ti]) > 0:
                candidate = taxonomy_results[ti].pop(0)
                path0 = candidate[1][0]
                path1 = candidate[1][1]
                if path0 in used_methods_per_category[ti] or path1 in used_methods_per_category[ti]:
                    continue
                pair_key = path0 + "+" + path1 if path0 > path1 else path1 + "+" + path0
                if pair_key in used_method_pairs:
                    continue
                # if reached here: this candidate is valid, and shall be used!
                used_methods_per_category[ti].add(path0)
                used_methods_per_category[ti].add(path1)
                used_method_pairs.add(pair_key)

                m0: METHOD_TYPE = make_method_data(r, path0)
                m1: METHOD_TYPE = make_method_data(r, path1)
                # TODO swap(m0, m1) if random bool?
                comm = find_commits(repo, m0[0], m1[0])
                taxonomy_picked_results[ti].append((ti, m0, m1, comm))
                if len(taxonomy_picked_results[ti]) >= ENTRIES_PER_PATTERN:
                    active_tax_categories.remove(ti)
                break
        progress_bar.close()
        study_entries: List[STUDY_ENTRY_TYPE] = [entry for res in taxonomy_picked_results for entry in res]

        study: STUDY_TYPE = (repo, study_entries)
        with open(study_dataset_result_path, 'wb') as out:
            pickle.dump(study, out)


main()
print("Done")
