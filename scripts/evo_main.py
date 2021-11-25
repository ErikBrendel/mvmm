import logging; logging.basicConfig(level=logging.INFO)
import pdb
import pyfiglet

from custom_types import *
from local_repo import *
from repos import *
from metrics import *
from analysis import *

r = LocalRepo.for_name("jfree/jfreechart")
print(pyfiglet.figlet_format(r.name))


MetricManager.clear(r, "evolutionary")
MetricManager.get(r, "evolutionary").print_statistics()
