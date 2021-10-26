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
SEVERAL = 4  # 2-5
MANY = 7  # TODO this is nowhere defined, I just picked a number that felt good to me!!!!
SHORT_MEMORY_CAPACITY = 8  # 7-8


BB_METRICS = [
    ("god_classes", "classes"),
    ("feature_envy_methods", "methods"),
    ("data_classes", "classes"),
    ("brain_methods", "methods"),
  # ("brain_classes", "classes"),
  # ("significant_duplication_method_pairs", "method_pairs"),
    ("intensive_coupling_methods", "methods"),
    ("dispersed_coupling_methods", "methods"),
    ("shotgun_surgeries", "methods"),
]

_BB_CONTEXT_CACHE: Dict[str, "BBContext"] = dict()


class BBContext:
    repo: LocalRepo
    uses_graph: Dict[str, Set[str]]
    is_used_by_graph: Dict[str, Set[str]]

    @staticmethod
    def for_repo(repo: LocalRepo):
        if repo.name not in _BB_CONTEXT_CACHE:
            _BB_CONTEXT_CACHE[repo.name] = BBContext(repo)
        return _BB_CONTEXT_CACHE[repo.name]

    def __init__(self, repo: LocalRepo):
        self.repo = repo
        self.uses_graph = dict()
        self.is_used_by_graph = dict()

        def handle_reference(a, b, _strength):
            if a not in self.uses_graph:
                self.uses_graph[a] = set()
            self.uses_graph[a].add(b)
            if b not in self.is_used_by_graph:
                self.is_used_by_graph[b] = set()
            self.is_used_by_graph[b].add(a)

        ReferencesContext(self.repo).iterate_all_references(handle_reference, "Extracting code references")

    def all_classes(self):
        return self.all_of_type("classes")

    def all_methods(self):
        return self.all_of_type("methods")

    def all_of_type(self, node_type: NodeFilterMode):
        return get_filtered_nodes(self.repo, node_type)

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

    def find_by_name(self, name: str) -> List[str]:
        return getattr(self, "find_" + name)()

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
        path_type = self._get_type_of(clazz_or_method)
        if path_type == "method":
            return len([a for a in self._get_accessed_by(clazz_or_method) if self._is_attribute_or_accessor_method(a)])
        elif path_type == "class":
            return sum(self._ATFD(m) for m in self._get_methods_of(clazz_or_method))
        raise Exception("cannot compute ATFD for " + str(clazz_or_method))

    def _WMC(self, clazz) -> int:
        """weighted method count (sum of cyclo of all methods)"""
        return sum(self._CYCLO(m) for m in self._get_methods_of(clazz))

    def _TCC(self, clazz) -> float:
        """relative amount of pairs of methods of this class that access a common attribute within this class"""
        count = 0
        total = 0
        for a, b in all_pairs(self._get_methods_of(clazz)):
            intersection_access = set(self._get_accessed_by(a)).intersection(set(self._get_accessed_by(b)))
            if any(a.startswith(clazz + "/") and self._is_attribute_or_accessor_method(a) for a in intersection_access):
                count += 1
            total += 1
        return count / float(total)

    def _LAA(self, method) -> float:
        """Locality of attribute access"""
        accessed_attributes = [a for a in self._get_accessed_by(method) if self._is_attribute_or_accessor_method(a)]
        if len(accessed_attributes) == 0:
            return 1

        containing_class = self._get_containing_class_of(method)
        # TODO there are two varying definitions for the nominator of this calculation:
        #  All class attributes: https://www.simpleorientedarchitecture.com/how-to-identify-feature-envy-using-ndepend/
        #  All accessed class attributes: https://docs.embold.io/locality-of-attribute-accesses/
        #  first one is also used in blue book, but second seems more reasonable to me
        class_attributes = len([a for a in accessed_attributes if a.startswith(containing_class + "/")])
        # class_attributes = len(self._get_attributes_of(self._get_containing_class_of(method)))

        return class_attributes / float(len(accessed_attributes))

    def _FDP(self, method) -> int:
        """foreign data providers"""
        accessed_attributes = [a for a in self._get_accessed_by(method) if self._is_attribute_or_accessor_method(a)]
        attribute_classes = set(self._get_containing_class_of(a) for a in accessed_attributes)
        attribute_classes.discard(self._get_containing_class_of(method))
        return len(attribute_classes)

    def _WOC(self, clazz) -> float:
        """weight of class"""
        public_interface = [m for m in (self._get_methods_of(clazz) + self._get_attributes_of(clazz)) if self._is_public(m)]
        if len(public_interface) == 0:
            return 0  # very light-weight class indeed :D
        functional_public_interface = [m for m in public_interface if not self._is_attribute_or_accessor_method(m)]
        return len(functional_public_interface) / float(len(public_interface))

    def _NOAP(self, clazz) -> int:
        """number of public attributes"""
        return len([a for a in self._get_attributes_of(clazz) if self._is_public(a)])

    def _NOAM(self, clazz) -> int:
        """number of accessor methods"""
        return len([m for m in self._get_methods_of(clazz) if self._is_attribute_or_accessor_method(m)])

    def _LOC(self, clazz_or_method) -> int:
        """lines of code"""
        path_type = self._get_type_of(clazz_or_method)
        if path_type == "method":
            return self._get_line_count_of(clazz_or_method)
        elif path_type == "class":
            return sum(self._LOC(m) for m in self._get_methods_of(clazz_or_method))
        raise Exception("cannot compute LOC for " + str(clazz_or_method))

    def _CYCLO(self, method) -> float:
        """mccabe cyclo complexity"""
        # https://www.theserverside.com/feature/How-to-calculate-McCabe-cyclomatic-complexity-in-Java
        # https://perso.ensta-paris.fr/~diam/java/online/notes-java/principles_and_practices/complexity/complexity-java-method.html
        mccabe = 1

        def handler(node):
            nonlocal mccabe
            if node.type in ["if_statement", "switch_label", "for_statement", "enhanced_for_statement", "while_statement", "do_statement", "break_statement", "continue_statement"]:
                mccabe += 1
        self._iterate_method_ast(method, handler)
        return mccabe

    def _MAXNESTING(self, method) -> int:
        """maximum nesting level"""
        current_nesting = 0
        max_nesting = 0

        def iterate_tree(cursor):
            nonlocal current_nesting
            nonlocal max_nesting
            enhances_nesting = cursor.node.type in ["if_statement", "for_statement", "enhanced_for_statement", "while_statement", "do_statement", "switch_statement"]
            if enhances_nesting:
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            if cursor.goto_first_child():
                iterate_tree(cursor)
                while cursor.goto_next_sibling():
                    iterate_tree(cursor)
                cursor.goto_parent()
            if enhances_nesting:
                current_nesting -= 1
        iterate_tree(self._get_method_body_ast_cursor(method))
        return max_nesting

    def _NOAV(self, method) -> int:
        """number of accessed variables: parameters, instance variables, local variables"""
        accessed_variables = len([a for a in self._get_accessed_by(method) if self._get_type_of(a) == "attribute"])

        def handler(node):
            nonlocal accessed_variables
            if node.type in ["formal_parameter", "local_variable_declaration"]:
                accessed_variables += 1
        self._iterate_method_ast(method, handler)

        return accessed_variables

    def _CINT(self, method) -> int:
        """coupling intensity - amount of unique methods that are called"""
        return len([m for m in self._get_accessed_by(method) if self._get_type_of(m) == "method"])

    def _CDISP(self, method) -> float:
        """amount (relative) of unique classes that this method uses (= of which this methods calls a method)"""
        cint = self._CINT(method)
        if cint == 0:
            return 0  # absolutely no dispersion to see here :D
        accessed_methods = [m for m in self._get_accessed_by(method) if self._get_type_of(m) == "method"]
        accessed_classes = set(self._get_containing_class_of(m) for m in accessed_methods)
        return len(accessed_classes) / float(cint)

    def _CM(self, method) -> int:
        """changing methods - number of caller methods"""
        return len(self._get_callers_of(method))

    def _CC(self, method) -> int:
        """changing classes - number of caller classes"""
        return len(set([self._get_containing_class_of(m) for m in self._get_callers_of(method)]))

    #
    # even lower level methods for working with paths
    #

    def _get_type_of(self, path: str) -> str:
        """returns one of [method, class, attribute, other]"""
        node = self.repo.get_tree().find_node(path)
        raw_type = node.get_type()
        if raw_type in ["class", "enum", "interface"]:
            return "class"
        if raw_type in ["method", "constructor"]:
            return "method"
        if raw_type == "field":
            return "attribute"
        return "other"

    def _get_containing_class_of(self, path: str) -> str:
        """get self or the first parent that is of type class, raising on reaching root"""
        parts = path.split("/")
        while len(parts) > 0:
            potential_result = "/".join(parts)
            if self._get_type_of(potential_result) == "class":
                return potential_result
            parts = parts[:-1]
        raise Exception("Cannot find containing class of other!")

    def _get_methods_of(self, clazz: str) -> List[str]:
        return [m.get_path() for m in self.repo.get_tree().find_node(clazz).get_children_of_type("method")]

    def _get_attributes_of(self, clazz: str) -> List[str]:
        return [m.get_path() for m in self.repo.get_tree().find_node(clazz).get_children_of_type("field")]

    def _get_callers_of(self, path: str) -> Set[str]:
        """get list of methods that call the given method"""
        return set([m for m in self.is_used_by_graph.get(path, []) if self._get_type_of(m) == "method"])

    def _get_accessed_by(self, path: str) -> Set[str]:
        """get list of methods and attributes that are accessed from the given method"""
        return set([ma for ma in self.uses_graph.get(path, []) if ma in ["method", "attribute"]])

    def _get_source_code_of(self, path: str) -> str:
        """get source string (indent reduced) of given method or class"""
        node = self.repo.get_tree().find_node(path)
        return unindent_code_snippet(node.get_text(self.repo.get_file(node.get_containing_file_node().get_path())))

    def _get_method_body_ast_cursor(self, method: str):
        node = self.repo.get_tree().find_node(method)
        if node.ts_node is None:
            raise Exception("No ast for method " + str(method))
        return node.ts_node.walk()

    def _iterate_method_ast(self, method: str, handler: Callable[[Any], None]):
        def iterate_tree(cursor):
            handler(cursor.node)
            if cursor.goto_first_child():
                iterate_tree(cursor)
                while cursor.goto_next_sibling():
                    iterate_tree(cursor)
                cursor.goto_parent()
        iterate_tree(self._get_method_body_ast_cursor(method))

    def _get_line_count_of(self, path: str) -> int:
        return len(self._get_source_code_of(path).split("/"))

    def _is_attribute_or_accessor_method(self, path: str) -> bool:
        path_type = self._get_type_of(path)
        return path_type == "attribute" or (path_type == "method" and self._get_line_count_of(path) <= 3)

    def _is_public(self, member):
        text = self._get_source_code_of(member).lstrip()
        if text.startswith("public"):
            return True
        if text.startswith("private"):
            return False
        lines = [line.strip() for line in text.split("\n")]
        if any(line.startswith("public") for line in lines):
            return True
        if any(line.startswith("private") for line in lines):
            return False
        return True


if __name__ == "__main__":
    for repo in ["jfree/jfreechart:v1.5.1"]:
        r = LocalRepo(repo)
        ctx = BBContext(r)
        all_disharmonies = set(ctx.find_all_disharmonies())
        everything = set(ctx.all_methods() + ctx.all_classes())
        print(f"#Disharmonies: {len(all_disharmonies)} of {len(everything)}, relative: {'{:2.1f}'.format(len(all_disharmonies) / float(len(everything)) * 100)}%")
        print(sorted(list(all_disharmonies)))

