import logging; logging.basicConfig(level=logging.INFO)
import pdb

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *
from cachier import cachier


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

for repo in repos:
    try:
        data = get_cloc_data_parallel(repo)
        commits = get_repo_commit_count(repo)
        print("    " + repo + " & $" + fmt(data["nFiles"]) + "$ & $" + fmt(data["code"]) + "$ & $" + fmt(data["comment"]) + "$ & $" + fmt(commits) + "$ \\\\")
    except Exception as e:
        print("Error in " + repo, e)

print("Done")
