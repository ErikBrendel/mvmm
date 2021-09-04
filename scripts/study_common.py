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
STUDY_ENTRY_TYPE = Tuple[int, METHOD_TYPE, METHOD_TYPE, COMMITS_TYPE]  # first int is taxonomy category index it belongs to
STUDY_TYPE = Tuple[str, List[STUDY_ENTRY_TYPE]]  # repo name and list of entries

_ = None
TAXONOMY: List[Tuple[PatternType, str]] = [
    ([1, 0, 1, _], "direct code clones"),
    ([1, 1, _, 0], "cross cutting concerns"),
    ([0, _, 1, 0], "independent code duplication"),
    ([0, _, 1, 1], "parallel structures within a module"),
    ([0, _, 0, 1], "mixed concerns (maybe not a problem?)"),
    ([0, 1, 0, 0], "Hidden Relation"),
    ([1, 1, 0, 1], "Inconsistent language"),
]