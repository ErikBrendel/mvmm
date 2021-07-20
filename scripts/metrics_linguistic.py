import regex  # the cooler "re"
from stop_words import get_stop_words
from nltk.corpus import stopwords
from nltk import WordNetLemmatizer, FreqDist
import string
import numpy as np

from local_repo import *
from graph import SimilarityCouplingGraph
from util import *

# constants
MIN_WORD_LENGTH = 1
MAX_WORD_LENGTH = 50
MIN_WORD_USAGES = 2  # any word used less often will be ignored
MAX_DF = 0.95  # any terms that appear in a bigger proportion of the documents than this will be ignored (corpus-specific stop-words)
MAX_FEATURES = 4000  # the size of the LDA thesaurus - amount of words to consider for topic learning
TOPIC_COUNT = 10  # 40  # 100 according to paper
BTM_ITERATIONS = 1000  # 100 according to docs?
LDA_RANDOM_SEED = 42
DOCUMENT_SIMILARITY_EXP = 8  # higher = lower equality values, lower = equality values are all closer to 1
DOCUMENT_SIMILARITY_CUTOFF = 0.05  # in range [0 .. 1]: everything below this is dropped

CLI_PATH = os.getenv("BTM_EXECUTABLE", "/home/ebrendel/util/btm/btm")


def extract_topic_model_documents(files) -> List[Tuple[RepoTree, List[str]]]:  # List of (RepoTree-Node,wordList) - tuples
    # keywords from python, TS and Java
    custom_stop_words = ["abstract", "and", "any", "as", "assert", "async", "await", "boolean", "break", "byte", "case", "catch", "char", "class", "const", "constructor", "continue", "debugger",
                         "declare", "def", "default", "del", "delete", "do", "double", "elif", "else", "enum", "except", "export", "extends", "false", "False", "final", "finally", "float", "for",
                         "from", "function", "get", "global", "goto", "if", "implements", "import", "in", "instanceof", "int", "interface", "is", "lambda", "let", "long", "module", "new", "None",
                         "nonlocal", "not", "null", "number", "of", "or", "package", "pass", "private", "protected", "public", "raise", "require", "return", "set", "short", "static", "strictfp",
                         "string", "super", "switch", "symbol", "synchronized", "this", "throw", "throws", "transient", "true", "True", "try", "type", "typeof", "var", "void", "volatile", "while",
                         "with", "yield"]
    stop_words = set(list(get_stop_words('en')) + custom_stop_words)  # TODO ignored "list(stopwords.words('english'))" because it had "y" and other weird ones
    splitter = r"(?:[\W_]+|(?<![A-Z])(?=[A-Z])|(?<!^)(?=[A-Z][a-z]))"
    lemma = WordNetLemmatizer()
    printable_characters = set(string.printable)

    def _normalize_word(word):
        return lemma.lemmatize(lemma.lemmatize(word.lower(), pos="n"), pos="v")

    def _get_text(content_string):
        # https://stackoverflow.com/questions/5486337/how-to-remove-stop-words-using-nltk-or-python
        # https://agailloty.rbind.io/en/project/nlp_clean-text/
        content_string = ''.join(c for c in content_string if c in printable_characters)
        words = regex.split(splitter, content_string, flags=regex.VERSION1)  # regex V1 allows splitting on empty matches
        words = [word for word in words if word not in stop_words]
        words = [_normalize_word(word) for word in words]
        words = [word for word in words if MIN_WORD_LENGTH <= len(word) <= MAX_WORD_LENGTH]
        words = [word for word in words if word not in stop_words]
        return words

    # see https://docs.python.org/2/library/collections.html#collections.Counter
    freq_dist = FreqDist()

    node_words: List[Tuple[RepoTree, List[str]]] = []  # List of (RepoTree-Node,wordList) - tuples
    for file in log_progress(files, desc="Extracting language corpus"):
        node = file.get_repo_tree_node()  # TODO unify with references view code
        if node is None:
            continue  # TODO why / when does this happen?

        # TODO keep in sync with evolutionary and references view as well as RepoFile class
        classes = node.get_descendants_of_type("class") + node.get_descendants_of_type("interface") + node.get_descendants_of_type("enum")
        for class_node in classes:
            fields = class_node.get_children_of_type("field")
            methods = class_node.get_children_of_type("method") + class_node.get_children_of_type("constructor")
            # print("Class " + class_node.name + ": " + str(len(methods)) + " methods and " + str(len(fields)) + " fields")

            for member in fields + methods:
                text = member.get_comment_and_own_text(file)
                # words = list(_get_text(class_node.get_path() + " " + text))
                words = list(_get_text(class_node.name + " " + text))
                for word in words:
                    freq_dist[word] += 1
                # TODO: handle the empty list?!?
                node_words.append((member, words))
                # print(" ".join(words))

    # random.seed(LDA_RANDOM_SEED)
    # random.shuffle(node_words)

    for word in freq_dist:
        if freq_dist[word] < MIN_WORD_USAGES:
            del freq_dist[word]

    print("Amount of documents: " + str(len(node_words)))
    print("Total Amount of words: " + str(sum([len(b) for a, b in node_words])))
    print("Vocab size: " + str(len(freq_dist)))
    return node_words


def train_topic_model(node_words: List[Tuple[RepoTree, List[str]]]):
    """returns the document - topic matrix, stating how much of each topic is present in each document"""

    process_options = [CLI_PATH,
                       '--iterations', str(BTM_ITERATIONS),
                       '--maxVocabSize', str(MAX_FEATURES),
                       '--topicCount', str(TOPIC_COUNT),
                       ]
    process = subprocess.Popen(process_options, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for (node, words) in node_words:
        process.stdin.write((" ".join(words) + "\n").encode("utf-8"))
    process.stdin.close()
    # print("\n".join(" ".join(words) for node, words in node_words))

    doctop = []
    with log_progress(desc="BTM Gibbs Sampling", total=BTM_ITERATIONS) as pbar:
        while True:
            from_program = process.stdout.readline().decode("utf-8")
            if not from_program:
                break
            if from_program.startswith("#progress "):
                pbar.n = int(from_program[len("#progress "):].split(" ")[0])
                pbar.update(0)
            elif from_program.startswith("#doctop "):
                data = [float(x) for x in from_program[len("#doctop "):].strip().split(",")]
                doctop.append(data)
            else:
                short_line = (from_program[:100] + '...') if len(from_program) > 102 else from_program
                if short_line[-1] != "\n":
                    short_line += "\n"
                print("[BTM] " + short_line, end="")

    if len(doctop) != len(node_words):
        print("Received wrong number of doctop lines! Exit code: " + str(process.poll()))
        pdb.set_trace()

    return np.array(doctop)


def couple_by_topic_similarity(node_words: List[Tuple[RepoTree, List[str]]], doctop, coupling_graph: SimilarityCouplingGraph):
    for (repo_tree, words), topics in log_progress(zip(node_words, doctop), total=len(node_words), desc="Generating coupling graph"):
        if not all(x < 0.001 for x in topics):  # if it is not topic-less
            coupling_graph.add_node(repo_tree.get_path(), topics, len(words))

    return coupling_graph
