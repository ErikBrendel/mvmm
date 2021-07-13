import logging;logging.basicConfig(level=logging.INFO)
import sys

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *

print("IDE endpoint script ready")
while True:
    cmd = input()
    sys.stdout.flush()
    if cmd.startswith("gs "):
        print("#result " + graph_manager.execute_string([cmd[len("gs "):]]))
        sys.stdout.flush()
    elif cmd.startswith("gv "):
        graph_manager.execute_void(cmd[len("gv "):])
    else:
        print("Unknown command!", cmd)
