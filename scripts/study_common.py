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
TAXONOMY: List[Tuple[PatternType, str, str]] = [
    ([1, 0, 1, _], "Direct Code Clones", "Methods that are doing similar things"),
    ([1, 1, _, 0], "Cross-Cutting Concerns", "strongly related code is scattered across different modules"),
    ([0, _, 1, 0], "Independent Code Duplication", "The same code exists in independent modules"),
    ([0, _, 1, 1], "Parallel Structures", "within a single module, similar code structures for different sub-tasks have been developed"),
    ([0, _, 0, 1], "Mixed Concerns / Low Cohesion", "within a single module, multiple unrelated topics are handled"),
    ([0, 1, 0, 0], "Hidden Relation", "unrelated methods being modified together"),
    ([1, 1, 0, 1], "Inconsistent Language", "close and related code that looks unrelated at first, based on the different vocabulary used"),
]
