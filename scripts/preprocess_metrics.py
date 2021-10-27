from util import map_parallel

repos = [
    'ErikBrendel/LudumDare',
    'ErikBrendel/LD35',
    "junit-team/junit4",
    "vanzin/jEdit",
    # "jfree/jfreechart:5ca5d26bb38bafead25f81e88e0938a5d042c2a4",  # May 15
    # "jfree/jfreechart:9020a32e62800916f1897c3eb17c95bf0371230b",  # Mar 7
    # "jfree/jfreechart:99d999395e46f8cf8689724853c9ede89be7c7ea",  # Mar 1
    # "jfree/jfreechart:fc4ddeed916c4cfd6479bf7378c6cdb94f6a19fe",  # Feb 6
    # "jfree/jfreechart:461625fd1f7242a1223f8e73716e9f2b4e9fd8a5",  # Dez 19, 2020
    "jfree/jfreechart",
    # "jfree/jfreechart:v1.5.3",
    # "jfree/jfreechart:v1.5.2",
    # "jfree/jfreechart:v1.5.1",
    # "jfree/jfreechart:v1.5.0",
    # "jfree/jfreechart:v1.0.19",

    "jOOQ/jOOQ",
    "wumpz/jhotdraw",
    "neuland/jade4j",
    "apache/log4j",
    "hunterhacker/jdom",
    "jenkinsci/jenkins",
    "brettwooldridge/HikariCP",
    "adamfisk/LittleProxy",
    "dynjs/dynjs",
    "SonarSource/sonarqube",
    "eclipse/aspectj.eclipse.jdt.core",
]


def preprocess(repo_name: str):
    from local_repo import LocalRepo
    from study_common import TAXONOMY
    from analysis import analyze_disagreements, ALL_VIEWS

    repo = LocalRepo(repo_name)
    all_patterns = [p for p, n, d in TAXONOMY]
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "classes")
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "methods")


map_parallel(repos, preprocess, lambda foo: foo, f"Preprocessing all {len(repos)} repos")
