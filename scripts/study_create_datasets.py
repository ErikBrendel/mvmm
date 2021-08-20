from study_common import *

repos = [
    "junit-team/junit4",
]
SORT_WEIGHTS = [0.175] * 4 + [0.3]  # a bit higher support - only want the results where we are sure!


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


def main():
    for repo in repos:
        print(pyfiglet.figlet_format(repo))
        r = LocalRepo(repo)
        results = analyze_disagreements(r, ALL_VIEWS, ALL_PATTERNS, "methods")
        study_entries: List[STUDY_ENTRY_TYPE] = []
        for p, res in log_progress(list(zip(ALL_PATTERNS, results)), desc="getting data"):
            best = res.get_best(SORT_WEIGHTS)
            unique_best = []
            unique_best_used_paths = set()
            for b in best:
                if b[1][0] not in unique_best_used_paths and b[1][1] not in unique_best_used_paths:
                    unique_best.append(b)
                    unique_best_used_paths.add(b[1][0])
                    unique_best_used_paths.add(b[1][1])
            for elem in unique_best[:2]:
                m0: METHOD_TYPE = make_method_data(r, elem[1][0])
                m1: METHOD_TYPE = make_method_data(r, elem[1][1])
                # TODO swap(m0, m1) if random bool?
                comm = find_commits(repo, m0[0], m1[0])
                study_entries.append((p, m0, m1, comm))
        study: STUDY_TYPE = (repo, study_entries)
        with open(STUDY_RESULTS_PATH + "dataset-" + repo.replace("/", "_") + '.pickle', 'wb') as out:
            pickle.dump(study, out)


main()
print("Done")
