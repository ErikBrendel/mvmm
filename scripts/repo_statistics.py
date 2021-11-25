import logging; logging.basicConfig(level=logging.INFO)
import pdb

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *
from cachier import cachier
from datetime import datetime

OVERRIDE_DATES = {
    "apache/hadoop:release-0.5.0": datetime(2006, 8, 5),
    "apache/hadoop:release-0.10.0": datetime(2007, 1, 6),
    "apache/hadoop:release-0.15.0": datetime(2007, 11, 3),
    "apache/hadoop:release-0.20.0": datetime(2009, 4, 22),
}
def get_date(repo):
    if repo.name in OVERRIDE_DATES:
        return OVERRIDE_DATES.get(repo.name)
    return repo.get_head_commit().authored_datetime


@cachier()
def get_repo_commit_count(repo: str) -> int:
    return len(LocalRepo(repo).get_all_commits())


# "cloc --git master --include-ext=java --json"

def mapper(file, repo_path):
    if len(file[1]) == 0:
        return 0, 0
    process_options = ["cloc",
                       '--stdin-name=' + file[0],
                       '--json',
                       '-'
                       ]
    process = subprocess.Popen(process_options, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=repo_path)
    process.stdin.write(file[1].encode("utf-8"))
    process.stdin.close()
    out_lines = process.stdout.readlines()
    out = "".join([decode(o) for o in out_lines])
    try:
        json_loaded = json.loads(out)["Java"]
        return json_loaded["comment"], json_loaded["code"]
    except Exception as e:
        print(e, out)
        raise e

@cachier()
def get_cloc_data_parallel(repo: str):
    r = LocalRepo(repo)
    files = [(f.get_name(), f.get_content_without_copyright()) for f in r.get_all_interesting_files()]
    comment = 0
    code = 0

    def result_handler(res):
        nonlocal comment, code
        comment += res[0]
        code += res[1]

    map_parallel(files, partial(mapper, repo_path=r.path()), result_handler, "cloc-ing")
    return {
        "nFiles": len(files),
        "comment": comment,
        "code": code,
    }
def fmt(num):
    #return str(num)
    #return "{:.1f}".format(num / 1000.0)
    return "{:,}".format(num)

for repo, versions in repos_and_versions:
    try:
        data = get_cloc_data_parallel(repo)
        commits = get_repo_commit_count(repo)
        r = LocalRepo(repo)
        repo_user, repo_name = r.repo_name.split("/")
        repo_display_name = fr"{{\scriptsize {repo_user}/}}{repo_name}~~\emph{{\scriptsize {r.committish}}}"
        print(fr"    {repo_display_name} & ${fmt(data['nFiles'])}$ & ${fmt(data['code'])}$ & ${fmt(data['comment'])}$ & ${fmt(commits)}$ \\")
    except Exception as e:
        print("Error in " + repo, e)

print("\nVersion Table:\n")

for repo, versions in repos_and_versions:
    r = LocalRepo(repo)
    repo_user, repo_name = r.repo_name.split("/")
    repo_header_cell = r"\midrule"'\n'r"    \multirow{" + str(len(versions)) + r"}{*}{\begin{tabular}[c]{@{}l@{}}" + repo_user + r"/\\ " + repo_name + r"\\ (" + r.committish + r")\end{tabular}}"
    for i, version in enumerate(versions):
        old_r = r.get_old_version(version)
        month_count = (get_date(r) - get_date(old_r)).days / (365.25 / 12)
        day_count_footnote = "*" if r.name in OVERRIDE_DATES or old_r.name in OVERRIDE_DATES else ""
        commit_count = len(set(r.get_commit_history_of_head()).difference(set(old_r.get_commit_history_of_head())))
        print(fr"    {repo_header_cell if i == 0 else ''} & {version} & ${round(month_count):,}${day_count_footnote} & ${fmt(commit_count)}$ \\")
