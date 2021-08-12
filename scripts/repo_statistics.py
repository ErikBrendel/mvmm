import logging; logging.basicConfig(level=logging.INFO)
import pdb

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *

# "cloc --git master --include-ext=java --json"

print("repo,nFiles,interesting_files,code,comment")
for repo in repos:
    r = LocalRepo(repo)

    process_options = ["cloc",
                       '--git', r.get_head_commit().hexsha,
                       '--include-ext=' + r.type_extension(),
                       '--json',
                       ]
    process = subprocess.Popen(process_options, stdout=subprocess.PIPE, cwd=r.path())
    out_lines = process.stdout.readlines()
    out = "".join([decode(o) for o in out_lines])
    try:
        data = json.loads(out)["Java"]
        print(repo + "," + str(data["nFiles"]) + "," + str(data["code"]) + "," + str(data["comment"]))
    except:
        print("Error in " + repo + ": " + out)

print("Done")
