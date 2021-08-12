import logging; logging.basicConfig(level=logging.INFO)
import pdb

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *
from cachier import cachier

# "cloc --git master --include-ext=java --json"

@cachier()
def get_cloc_data(repo: str):
    r = LocalRepo(repo)

    process_options = ["cloc",
                       '--git', r.get_head_commit().hexsha,
                       '--include-ext=' + r.type_extension(),
                       '--json',
                       ]
    process = subprocess.Popen(process_options, stdout=subprocess.PIPE, cwd=r.path())
    out_lines = process.stdout.readlines()
    out = "".join([decode(o) for o in out_lines])
    return json.loads(out)["Java"]


print("repo,nFiles,interesting_files,code,comment")
for repo in repos:
    try:
        data = get_cloc_data(repo)
        print("    " + repo + " & $" + str(data["nFiles"]) + "$ & $" + str(data["code"]) + "$ & $" + str(data["comment"]) + "$ \\\\")
    except Exception as e:
        print("Error in " + repo, e)

print("Done")
