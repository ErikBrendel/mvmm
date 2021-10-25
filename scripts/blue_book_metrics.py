from typing import *

from analysis import *
from local_repo import *


# blue book page 16
CYCLO_LOC_LOW = 0.16
CYCLO_LOC_AVERAGE = 0.20
CYCLO_LOC_HIGH = 0.24
CYCLO_LOC_VERY_HIGH = 0.36
LOC_METHOD_LOW = 7
LOC_METHOD_AVERAGE = 10
LOC_METHOD_HIGH = 13
LOC_METHOD_VERY_HIGH = 19.5
NOM_CLASS_LOW = 4
NOM_CLASS_AVERAGE = 7
NOM_CLASS_HIGH = 10
NOM_CLASS_VERY_HIGH = 15
WMC_LOW = 5
WMC_AVERAGE = 14
WMC_HIGH = 31
WMC_VERY_HIGH = 47
AMW_LOW = 1.1
AMW_AVERAGE = 2.0
AMW_HIGH = 3.1
AMW_VERY_HIGH = 4.7
LOC_CLASS_LOW = 28
LOC_CLASS_AVERAGE = 70
LOC_CLASS_HIGH = 130
LOC_CLASS_VERY_HIGH = 195

# following are calculated by how I understood what the book wanted to tell me
CYCLO_METHOD_LOW = CYCLO_LOC_LOW * LOC_METHOD_LOW
CYCLO_METHOD_AVERAGE = CYCLO_LOC_AVERAGE * LOC_METHOD_AVERAGE
CYCLO_METHOD_HIGH = CYCLO_LOC_HIGH * LOC_METHOD_HIGH
CYCLO_METHOD_VERY_HIGH = CYCLO_LOC_VERY_HIGH * LOC_METHOD_VERY_HIGH

# blue book page 17
ONE_QUARTER = 1 / 4.0
ONE_THIRD = 1 / 3.0
HALF = 1 / 2.0
TWO_THIRDS = 2 / 3.0
THREE_QUARTERS = 3 / 4.0

# blue book page 18
NONE = 0
ONE = 1
SHALLOW = 1
TWO = 2
THREE = 3
FEW = 3  # 2-5
SEVERAL = 5  # 2-5
MANY = 7  # TODO this is nowhere defined, I just picked a number that felt good to me!!!!
SHORT_MEMORY_CAPACITY = 8  # 7-8


class BBContext:
    repo: LocalRepo

    def __init__(self, repo):
        self.repo = repo

    def all_classes(self):
        return get_filtered_nodes(self.repo, "classes")

    def all_methods(self):
        return get_filtered_nodes(self.repo, "methods")

    def find_all_disharmonies(self) -> List[str]:
        return \
            self.find_god_classes() +\
            self.find_feature_envy_methods() +\
            self.find_data_classes() +\
            self.find_brain_methods() +\
            self.find_brain_classes() +\
            self.find_significant_duplication_method_pairs() +\
            self.find_intensive_coupling_methods() +\
            self.find_dispersed_coupling_methods() +\
            self.find_shotgun_surgeries()

    def find_god_classes(self) -> List[str]:
        """page 80"""
        return [c for c in self.all_classes() if
                self._ATFD(c) > FEW and
                self._WMC(c) >= WMC_VERY_HIGH and
                self._TCC(c) < ONE_THIRD
                ]

    def find_feature_envy_methods(self) -> List[str]:
        """page 84"""
        # noinspection PyChainedComparisons
        return [m for m in self.all_methods() if
                self._ATFD(m) > FEW and
                self._LAA(m) < ONE_THIRD and
                self._FDP(m) <= FEW
                ]

    def find_data_classes(self) -> List[str]:
        """page 88"""
        return [c for c in self.all_classes() if
                self._WOC(c) < ONE_THIRD and
                self._class_reveals_many_attributes_and_is_not_complex(c)
                ]

    def find_brain_methods(self) -> List[str]:
        """page 92"""
        return [m for m in self.all_methods() if
                self._LOC(m) > LOC_CLASS_HIGH / 2 and
                self._CYCLO(m) >= CYCLO_METHOD_HIGH and
                self._MAXNESTING(m) >= SEVERAL and
                self._NOAV(m) > MANY
                ]

    def find_brain_classes(self) -> List[str]:
        """page 97"""
        return []  # ignored - is a subset of classes that contain brain methods, and is hard to implement :D

    def find_significant_duplication_method_pairs(self) -> List[str]:
        """page 102"""
        return []  # ignored, since very hard to implement

    def find_intensive_coupling_methods(self) -> List[str]:
        """page 120"""
        return [m for m in self.all_methods() if
                self._method_calls_too_many_methods_from_unrelated_classes(m) and
                self._MAXNESTING(m) > SHALLOW
                ]

    def find_dispersed_coupling_methods(self) -> List[str]:
        """page 127"""
        return [m for m in self.all_methods() if
                self._dispersed_calls_to_unrelated_classes(m) and
                self._MAXNESTING(m) > SHALLOW
                ]

    def find_shotgun_surgeries(self) -> List[str]:
        """page 133"""
        return [m for m in self.all_methods() if
                self._CM(m) > SHORT_MEMORY_CAPACITY and
                self._CC(m) > MANY
                ]

    #
    # helper methods for top-level problems
    #

    def _class_reveals_many_attributes_and_is_not_complex(self, clazz) -> bool:
        """page 89"""
        noap_noam = self._NOAP(clazz) + self._NOAM(clazz)
        wmc = self._WMC(clazz)
        return (noap_noam > FEW and wmc < WMC_HIGH) or (noap_noam > MANY and wmc < WMC_VERY_HIGH)

    def _method_calls_too_many_methods_from_unrelated_classes(self, method) -> bool:
        """page 122"""
        cint = self._CINT(method)
        cdisp = self._CDISP(method)
        return (cint > SHORT_MEMORY_CAPACITY and cdisp < HALF) or (cint > FEW and cdisp < ONE_QUARTER)

    def _dispersed_calls_to_unrelated_classes(self, method) -> bool:
        """page 128"""
        return self._CINT(method) > SHORT_MEMORY_CAPACITY and self._CDISP(method) >= HALF

    #
    # starting from page 167
    #

    def _ATFD(self, clazz_or_method) -> int:
        """access to foreign data (directly reading attributes of other classes)"""
        pass

    def _WMC(self, clazz) -> int:
        """weighted method count (sum of cyclo of all methods)"""
        pass

    def _TCC(self, clazz) -> float:
        """come cohesion stuff?"""
        pass

    def _LAA(self, method) -> float:
        """Locality of attribute access"""
        pass

    def _FDP(self, method) -> float:
        """foreign data providers"""
        pass

    def _WOC(self, clazz) -> float:
        """weight of class"""
        pass

    def _NOAP(self, clazz) -> int:
        """number of public attributes"""
        pass

    def _NOAM(self, clazz) -> int:
        """number of accessor methods"""
        pass

    def _LOC(self, clazz_or_method) -> int:
        """lines of code"""
        pass

    def _CYCLO(self, method) -> float:
        """mccabe cyclo complexity"""
        pass

    def _MAXNESTING(self, method) -> int:
        """maximum nesting level"""
        pass

    def _NOAV(self, method) -> int:
        """number of accessed variables"""
        pass

    def _CINT(self, method) -> int:
        """amount of unique methods that are called that are from other classes"""
        pass

    def _CDISP(self, method) -> float:
        """amount (relative?!?) of unique other classes  that this method uses (= of which this methods calls a method)"""
        pass

    def _CM(self, method) -> int:
        """changing methods - number of caller methods"""
        pass

    def _CC(self, method) -> int:
        """changing classes - number of caller classes"""
        pass


for repo in ["jfree/jfreechart:v1.5.1"]:
    r = LocalRepo(repo)
    ctx = BBContext(r)
    ctx.find_all_disharmonies()

