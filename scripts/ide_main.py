import logging;logging.basicConfig(level=logging.INFO)
import sys

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *

repo_by_name_cache = {}
def get_repo_cached(repo_name: str) -> LocalRepo:
    if repo_name not in repo_by_name_cache:
        repo = LocalRepo(repo_name)
        repo.update()
        repo_by_name_cache[repo_name] = repo
    return repo_by_name_cache[repo_name]


print("IDE endpoint script ready")
while True:
    cmd = input()
    sys.stdout.flush()
    if cmd.startswith("gs "):
        print("#result " + graph_manager.execute_string(cmd[len("gs "):].split("|")))
        sys.stdout.flush()
    elif cmd.startswith("gv "):
        graph_manager.execute_void(cmd[len("gv "):].split("|"))
    elif cmd.startswith("getGraph "):
        repo_name, view_name = cmd[len("getGraph "):].split("|")
        graph_id = MetricManager.get(LocalRepo(repo_name), view_name).id
        print("#result " + str(graph_id))
    else:
        print("Unknown command!", cmd)
