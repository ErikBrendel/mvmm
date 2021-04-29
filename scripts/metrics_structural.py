from parsing import *
from util import *
from local_repo import *

builtin_types = ['void', 'String', 'byte', 'short', 'int', 'long', 'float', 'double', 'boolean', 'char', 'Byte', 'Short', 'Integer', 'Long', 'Float', 'Double', 'Boolean', 'Character']
stl_types = ['Override', 'ArrayList', 'List', 'LinkedList', 'Map', 'HashMap', 'Object', 'Throwable', 'Exception']
obj_methods = ['getClass', 'hashCode', 'equals', 'clone', 'toString', 'notify', 'notifyAll', 'wait', 'finalize']  # https://www.javatpoint.com/object-class
ignored_types = set(builtin_types + stl_types + obj_methods)


error_query = JA_LANGUAGE.query("(ERROR) @err")
def _has_error(file) -> List[str]:
    errors = error_query.captures(file.get_tree().root_node)
    return len(errors) > 1


STRENGTH_FILE_IMPORT = 1
STRENGTH_ACCESS = 1
STRENGTH_CALL = 1
STRENGTH_CLASS_INHERITANCE = 3
STRENGTH_MEMBER_OVERRIDE = 3

unresolvable_vars = set()
def flush_unresolvable_vars():
    output = list(unresolvable_vars)
    unresolvable_vars.clear()
    output.sort(key=lambda x: len(x))
    for var in output:
        print("Unknown type for var:", var)


class Env:
    """an identifier-lookup environment"""
    def __init__(self, context, path):
        self.context = context
        self.path = path
    
    def get_env_for_name(self, compound_name):
        if compound_name in ignored_types:
            return None
        if compound_name.endswith("]") and "[" in compound_name:
            [base, array_rest] = compound_name.rsplit("[", 1)
            #if array_rest != "]":  # there is more inbetween?
            #    pdb.set_trace()
            return ArrayEnv(self.context, base, self)
        elif compound_name.endswith(">") and "<" in compound_name:
            [base, parameter] = compound_name[:-1].split("<", 1)
            parameter_types = regex.split(r",(?![^<]*>)", parameter)  # TODO this regex is not quite right: We want to match all commas that are not nested within <> brackets
            return GenericEnv(self.context, base, parameter_types, self)
        elif "." in compound_name:
            [first_step, rest] = compound_name.split(".", 1)
            step_result = self.get_env_for_single_name(first_step)
            if step_result is None: return None
            return step_result.get_env_for_name(rest)
        else:
            return self.get_env_for_single_name(compound_name)
        
        
    def get_env_for_single_name(self, name):
        print("Abstract env cannot resolve a name!")
        return None
    
    def get_env_for_array_access(self):
        print("This env cannot be array-accessed")
        return None
    
    def get_result_type_env(self):
        """For methods: the return type. For fields: their variable type. For classes: self"""
        print("Abstract env does not have a return value!")
        return None
    
    def get_self_paths(self):
        """return all the paths that are present in this envs definition"""
        """Might be zero (nested env), one (class / method) or multiple (compound generic type)"""
        return []
    
    def get_ungeneric_env(self):
        return self

class EnvWrapper(Env):
    def __init__(self, wrapped):
        Env.__init__(wrapped.context, wrapped.path)
        self.wrapped = wrapped
        
    def get_env_for_single_name(self, name):
        return self.wrapped.get_env_for_single_name(name)
    
    def get_env_for_array_access(self):
        return self.wrapped.get_env_for_array_access()
    
    def get_result_type_env(self):
        return self.wrapped.get_result_type_env()
    
    def get_self_paths(self):
        return self.wrapped.get_self_paths()
    
    def get_ungeneric_env(self):
        return self.wrapped.get_ungeneric_env()

class RepoTreeEnv(Env):
    """the identifier-lookup environment of a whole file"""
    def __init__(self, context, node):
        Env.__init__(self, context, node.get_path())
        self.node = node
        root_node = self.node.get_root()
        self.base_envs = self.context.get_base_types(self.path)
        
    def get_env_for_single_name(self, name):
        if name == self.node.name:
            return self
        
        effective_children = self.node.effective_children()
        if name in effective_children:
            return RepoTreeEnv(self.context, effective_children[name])
        
        for import_path in self.context.get_imports(self.path):
            if import_path.endswith("/" + name):
                return RepoTreeEnv(self.context, self.node.get_root().find_node(import_path))
            
        for base_env in self.base_envs:
            base_result = base_env.get_env_for_single_name(name)
            if base_result is not None:
                return base_result
            
        parent_env = self._get_parent_env()
        if parent_env is not None:
            return parent_env.get_env_for_single_name(name)
        
        return None
        
    def _get_parent_env(self):
        if self.node.parent is None:
            return None
        else:
            return RepoTreeEnv(self.context, self.node.parent)
    
    def get_result_type_env(self):
        result_type_env = self.context.get_result_type(self.path)
        if result_type_env is None:
            return self  # if we don't know our type, we might as well be our own (happens e.g. in "Util.foo()")
        return result_type_env
    
    def get_self_paths(self):
        """it's just this class"""
        return [self.path]

class NestedEnv(Env):
    """used for a class, a method, a for loop etc"""
    def __init__(self, context, parent_env):
        Env.__init__(self, context, None)  # has no path - should never be referenced
        self.parent_env = parent_env
        self.local_vars = {}
        
    def add_local_var(self, name, type_text):
        type_env = self.get_env_for_name(type_text)
        if type_env is None and type_text not in ignored_types:
            unresolvable_vars.add(type_text + " " + name)
        self.local_vars[name] = type_env
        
    def get_env_for_single_name(self, name):
        if name in self.local_vars:
            return self.local_vars[name]
        return self.parent_env.get_env_for_single_name(name)
    
    def get_result_type_env(self):
        print("Nested Env does not have a result type!")
        return None
    
    def get_self_paths(self):
        print("Nested Env does not have a path!")
        return []

class ArrayEnv(Env):
    def __init__(self, context, base_type, containing_env):
        Env.__init__(self, context, base_type + "[]")
        self.base_type = base_type
        self.containing_env = containing_env
        
    def _get_base_env(self):
        return self.containing_env.get_env_for_name(self.base_type)
        
    def get_env_for_single_name(self, name):
        if name in ["length"]:
            return None  # primitive values like int are ignored
        pdb.set_trace()
        print("Array env cannot resolve a name!")
        return None
    
    def get_env_for_array_access(self):
        return self._get_base_env()
    
    def get_result_type_env(self):
        return self
    
    def get_self_paths(self):
        base_env = self._get_base_env()
        if base_env is None:
            return []
        else:
            return base_env.get_self_paths()

class GenericEnv(Env):
    def __init__(self, context, base_type, generic_parameter_types, containing_env):
        Env.__init__(self, context, base_type + "<" + ",".join(generic_parameter_types) + ">")
        self.base_type = base_type
        self.generic_parameter_types = generic_parameter_types
        self.containing_env = containing_env
        
    def _get_base_env(self):
        return self.containing_env.get_env_for_name(self.base_type)
        
    def _get_generic_parameter_envs(self):
        return [self.containing_env.get_env_for_name(par) for par in self.generic_parameter_types]
        
    def get_env_for_single_name(self, name):
        if name == "get":
            pass  # TODO this is important!
        base_env = self._get_base_env()
        if base_env is None:
            return None
        # TODO add a wrapper env that replaces the generic type names with the concrete types we know
        return base_env.get_env_for_single_name(name)
    
    def get_result_type_env(self):
        return self
    
    def get_self_paths(self):
        base_env = self._get_base_env()
        base_paths = [] if base_env is None else base_env.get_self_paths()
        
        generic_parameter_envs = self._get_generic_parameter_envs()
        generic_parameter_paths = [[] if par_env is None else par_env.get_self_paths() for par_env in generic_parameter_envs]
        return [path for sublist in [base_paths, *generic_parameter_paths] for path in sublist]
    
    def get_ungeneric_env(self):
        return self._get_base_env()



package_query = JA_LANGUAGE.query("(package_declaration (_) @decl)")
import_query = JA_LANGUAGE.query("(import_declaration (scoped_identifier) @decl)")
class_query = JA_LANGUAGE.query("[(class_declaration name: (identifier) @decl) (interface_declaration name: (identifier) @decl) (enum_declaration name: (identifier) @decl)]")

class StructuralContext:
    def __init__(self, repo):
        self.repo = repo
        self.files = repo.get_all_interesting_files()
        self.full_class_name_to_path = {}
        self.file_path_to_imports = {}
        self.path_to_result_type_env = {}
        self.class_path_to_base_class_envs = {}
        self.class_path_to_generic_names = {}
        
        def _get_package(file) -> List[str]:
            packages = package_query.captures(file.get_tree().root_node)
            # assert len(packages) <= 1
            if len(packages) > 1:
                pdb.set_trace(header="Multiple packet declarations found!")
            if len(packages) == 1:
                return file.node_text(packages[0][0]).split(".")
            else:
                return []
        def _get_import_strings(file) -> List[str]:
            imports = import_query.captures(file.get_tree().root_node)
            result = []
            for import_statement in imports:
                import_string = file.node_text(import_statement[0])
                if not import_string.startswith("java"):  # ignore stl imports
                    result.append(import_string)
            return result
        def _get_main_class_name(file) -> List[str]:
            classes = class_query.captures(file.get_tree().root_node)
            if len(classes) >= 1:
                return file.node_text(classes[0][0])
            else:
                return None
            
        for file in log_progress(self.files, desc="Discovering classes"):
            if _has_error(file):
                continue
            class_name = _get_main_class_name(file)
            if class_name is not None:
                full_class_name = ".".join(_get_package(file) + [class_name])
                self.full_class_name_to_path[full_class_name] = file.get_path()
                class_node = file.get_repo_tree_node().find_node(class_name)
                if class_node is not None:
                    self.full_class_name_to_path[full_class_name] = class_node.get_path()
                else:
                    print("Cannot find a class node for this file!", file.get_path())
            else:
                if not file.get_path().endswith("/package-info.java"):
                    print("Cannot find a class in this file!", file.get_path())
        
        for file in log_progress(self.files, desc="Building Import Graph 2"):
            imports = [self.full_class_name_to_path[i] for i in _get_import_strings(file) if i in self.full_class_name_to_path]
            self.file_path_to_imports[file.get_path()] = imports
            
        for file in log_progress(self.files, desc="Extracting inheritance hierarchy and result types"):
            node = file.get_repo_tree_node()
            if node is None:
                # pdb.set_trace()
                continue  # TODO filter those out / parse @interfaces
                
            # TODO keep in sync with evolutionary and linguistic view as well as RepoFile class
            classes = node.get_descendants_of_type("class") + node.get_descendants_of_type("interface") + node.get_descendants_of_type("enum")
            for class_node in classes:
                # TODO store the names of generic parameters, if any
                generics_ts_node = class_node.ts_node.child_by_field_name("type_parameters")
                if generics_ts_node is not None:
                    self.class_path_to_generic_names[class_node.get_path()] = [file.node_text(child) for child in generics_ts_node.children if child.type == "type_parameter"]
                
                base_class_nodes = []
                superclass_ts_node = class_node.ts_node.child_by_field_name("superclass")
                if superclass_ts_node is not None:
                    assert superclass_ts_node.child_count >= 2 and superclass_ts_node.children[0].type == "extends" and all(c.type == "comment" for c in superclass_ts_node.children[1:-1])
                    base_class_nodes.append(superclass_ts_node.children[-1])
                interfaces_ts_node = class_node.ts_node.child_by_field_name("interfaces")
                if interfaces_ts_node is not None:
                    assert interfaces_ts_node.child_count >= 2 and interfaces_ts_node.children[0].type == "implements" and all(c.type == "comment" for c in interfaces_ts_node.children[1:-1])
                    base_class_nodes += interfaces_ts_node.children[-1].children
                        
                if len(base_class_nodes) > 0:
                    base_envs = []
                    for base_class_node in base_class_nodes:
                        extended_class_type_env = self._resolve_type_env(file.node_text(base_class_node), node)
                        if extended_class_type_env is not None:
                            base_envs.append(extended_class_type_env)
                    if len(base_envs) > 0:
                        self.class_path_to_base_class_envs[class_node.get_path()] = base_envs
                        
                
                fields = class_node.get_children_of_type("field")
                methods = class_node.get_children_of_type("method")
                
                for pathable in (fields + methods):
                    type_node = pathable.ts_node.child_by_field_name("type")
                    if type_node is None:
                        pdb.set_trace(header="field/method has no type?")
                    result_type_text = file.node_text(type_node)
                    result_type_env = self._resolve_type_env(result_type_text, node)
                    if result_type_env is not None:
                        self.path_to_result_type_env[pathable.get_path()] = result_type_env
                
    def couple_files_by_import(self, coupling_graph):
        for file in log_progress(self.files, desc="Connecting files by imports"):
            for imported_class_path in self.file_path_to_imports.get(file.get_path(), []):
                coupling_graph.add_and_support(file.get_path(), imported_class_path, STRENGTH_FILE_IMPORT)

    def couple_by_ineritance(self, coupling_graph):
        for sub_type_path in log_progress(self.class_path_to_base_class_envs.keys(), desc="Connecting classes by inheritance"):
            super_type_envs = self.get_transitive_base_types(sub_type_path)
            sub_type_children_names = self.repo.get_tree().find_node(sub_type_path).children.keys()
            for super_type_env in super_type_envs:
                coupling_graph.add_and_support(sub_type_path, super_type_env.path, STRENGTH_CLASS_INHERITANCE)
                super_type_env_ungeneric = super_type_env.get_ungeneric_env()
                if super_type_env_ungeneric is not None:
                    super_type_node = super_type_env_ungeneric.node
                    for sub_child in sub_type_children_names:
                        if super_type_node.has_child(sub_child):
                            coupling_graph.add_and_support(sub_type_path + "/" + sub_child, super_type_env.path + "/" + sub_child, STRENGTH_MEMBER_OVERRIDE)
                
                
    def couple_members_by_content(self, coupling_graph):
        # TODO make sure that the methods are also coupled to their parameter types and their return type
        # TODO make also sure that fields are coupled to their type (and maybe their init code content?)
        for file in log_progress(self.files, desc="Connecting methods and fields by content"):
            node = file.get_repo_tree_node()
            if node is None:
                # pdb.set_trace()
                continue  # TODO filter those out / parse @interfaces
            classes = node.get_descendants_of_type("class") + node.get_descendants_of_type("interface") + node.get_descendants_of_type("enum")
            for class_node in classes:
                members = class_node.get_children_of_type("field") + class_node.get_children_of_type("method") + class_node.get_children_of_type("constructor")
                for member in members:
                    member_path = member.get_path()
                    def couple_member_to(path, strength):
                        if path is None:
                            pdb.set_trace(header="Cannot couple with nothing!")
                        coupling_graph.add_and_support(path, member_path, strength)
                    def get_text(node):
                        if node is None:
                            pdb.set_trace(header="node is None, cannot get text!")
                        return file.node_text(node)
                    couple_member_by_content(member, couple_member_to, get_text, self)
    
    def get_result_type(self, path):
        return self.path_to_result_type_env.get(path, None)
    
    def get_base_types(self, path):
        return self.class_path_to_base_class_envs.get(path, [])
    
    def get_generic_type_names(self, path):
        return self.class_path_to_generic_names.get(path, [])
    
    def get_transitive_base_types(self, path):
        result = set()
        new_bases = set(self.get_base_types(path))
        while len(new_bases) > 0:
            result.update(new_bases)
            todos = new_bases
            new_bases = set()
            for todo in todos:
                new_bases.update(set(self.get_base_types(todo.path)) - result)
        
        return result
    
    def get_imports(self, path):
        return self.file_path_to_imports.get(path, [])
    
    def _resolve_type_env(self, type_name, context_file_node):
        """return the full path that is meant by that type_name, or None if not known"""
        imports = self.file_path_to_imports.get(context_file_node.get_path(), [])
        for import_path in imports:
            if import_path.endswith("/" + type_name):
                import_node = self.repo.get_tree().find_node(import_path)
                if import_node is not None:
                    return RepoTreeEnv(self, import_node)
        result_env = RepoTreeEnv(self, context_file_node).get_env_for_name(type_name)
        if result_env is None:
            return None
        return result_env







# TODOS:
# detect complex generic types (List<Foo>) and at least couple to foo, do not handle list.get(0).foomethod()
# properly handle arrays of things (ignore the .length attribute, but correctly infer type for further method call resolving)





def couple_member_by_content(
    member: RepoTree,
    couple_member_to: Callable[[str, float], None],
    get_text: Callable[[object], str],
    context: StructuralContext,
) -> None:
    """can be used on methods and fields"""
    # print("\n\n=======\nNow handling:\n", get_text(member.ts_node))
    
    this_env = RepoTreeEnv(context, member.parent)
    member_env = RepoTreeEnv(context, member)
    
    def couple_to(resolved_env, strength):
        if resolved_env not in [None, member_env]:
            for path in resolved_env.get_self_paths():
                couple_member_to(path, strength)
            # print("-> Coupled to", resolved_env.path)
        return resolved_env is not None
    
    def get_env_for_name(start_env, name):
        if name.startswith("this."):
            return this_env.get_env_for_name(name[len("this."):])
        else:
            return start_env.get_env_for_name(name)
    
            
    def iterate_tree(cursor, env) -> Env:
        result_env = env
        deeper_env = env
        if cursor.node.type in ["type_identifier", "scoped_type_identifier", "identifier", "scoped_identifier", "field_access"]:
            resolved_type_env = get_env_for_name(env, get_text(cursor.node))
            if couple_to(resolved_type_env, STRENGTH_ACCESS):
                result_env = resolved_type_env.get_result_type_env()
            else:
                result_env = None
        else:
            skip_children_for_iteration = []
            if cursor.node.type == "block":
                deeper_env = NestedEnv(context, result_env)
            elif cursor.node.type == "method_invocation":
                obj = cursor.node.child_by_field_name("object")
                target_env = env
                if obj is not None:  # call on other object than ourselves?
                    rec_cursor = obj.walk()
                    target_env = iterate_tree(rec_cursor, env)
                    skip_children_for_iteration.append(obj)
                if target_env is not None:  # target object resolve success?
                    resolved_method_env = get_env_for_name(target_env, get_text(cursor.node.child_by_field_name("name")))
                    if couple_to(resolved_method_env, STRENGTH_CALL):
                        result_env = resolved_method_env.get_result_type_env()
                    else:
                        result_env = None
            elif cursor.node.type == "local_variable_declaration":
                env.add_local_var(
                    get_text(cursor.node.child_by_field_name("declarator").child_by_field_name("name")),
                    get_text(cursor.node.child_by_field_name("type"))
                )
            elif cursor.node.type == "formal_parameter":
                env.add_local_var(
                    get_text(cursor.node.child_by_field_name("name")),
                    get_text(cursor.node.child_by_field_name("type"))
                )


            # all the rest is structure and needs to be fully iterated
            # TODO if one of those children has the name "body" (or the node type is body?), add a new local env layer
            if cursor.goto_first_child():
                if cursor.node not in skip_children_for_iteration:
                    iterate_tree(cursor, deeper_env)
                while cursor.goto_next_sibling():
                    if cursor.node not in skip_children_for_iteration:
                        iterate_tree(cursor, deeper_env)
                cursor.goto_parent()
        return result_env

    iterate_tree(member.ts_node.walk(), NestedEnv(context, member_env))
