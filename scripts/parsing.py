from tree_sitter import Language, Parser, Node
# https://github.com/tree-sitter/py-tree-sitter

from typing import Callable
import pdb
import regex

language_lib_path = '../lib/my-languages.so'
Language.build_library(
    language_lib_path,
    [
        '../lib/tree-sitter-java',
        '../lib/tree-sitter-typescript/typescript',
        '../lib/tree-sitter-python'
    ]
)
JA_LANGUAGE = Language(language_lib_path, 'java')
TS_LANGUAGE = Language(language_lib_path, 'typescript')
PY_LANGUAGE = Language(language_lib_path, 'python')

# methods on node:
# 'child_by_field_id', 'child_by_field_name', 'children', 'end_byte', 'end_point', 'has_changes', 'has_error', 'is_named', 'sexp', 'start_byte', 'start_point', 'type', 'walk'

java_parser = Parser()
java_parser.set_language(JA_LANGUAGE)
