import logging;logging.basicConfig(level=logging.INFO)
import pdb
import pyfiglet
import pickle
from cachier import cachier

from custom_types import *
from local_repo import *
from metrics import *
from analysis import *
from best_results_set import BRS_DATA_TYPE

STUDY_RESULTS_PATH = "../study/"
METHOD_TYPE = Tuple[str, str]  # path and content
COMMIT_CHANGES_TYPE = Tuple[int, int, int]  # [num changed files, num addition lines, num deletion lines]
COMMITS_TYPE = List[Tuple[str, str, str, str, COMMIT_CHANGES_TYPE, bool, bool]]  # message, author, date, hexsha, changes, belongs to method 1, belongs to method 2
STUDY_ENTRY_TYPE = Tuple[PatternType, METHOD_TYPE, METHOD_TYPE, COMMITS_TYPE]
STUDY_TYPE = Tuple[str, List[STUDY_ENTRY_TYPE]]  # repo name and list of entries