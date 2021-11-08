from util import map_parallel

repos = [
    'ErikBrendel/LudumDare',
    'ErikBrendel/LD35',
    "junit-team/junit4",
    "vanzin/jEdit",
    "jfree/jfreechart",
    "jfree/jfreechart:v1.5.3",
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
repos = [
    # "jfree/jfreechart:v1.5.3",
    # "junit-team/junit4:r4.13.2",
    # "apache/logging-log4j2:rel/2.14.1",
    # "jfree/jfreechart:v1.5.0",
    # "jfree/jfreechart:v1.0.18",
    # "junit-team/junit4:r4.6",
    # "apache/logging-log4j2:rel/2.11.2",
    # "apache/logging-log4j2:rel/2.8",
    # "apache/logging-log4j2:rel/2.4",
    # "apache/logging-log4j2:rel/2.1",
    # "apache/logging-log4j2:rel/2.0",
] + [f"apache/hadoop:release-0.{v}.0" for v in range(1, 16)]


def preprocess(repo_name: str):
    from local_repo import LocalRepo
    from study_common import TAXONOMY
    from analysis import analyze_disagreements, ALL_VIEWS

    repo = LocalRepo(repo_name)
    all_patterns = [p for p, n, d in TAXONOMY]
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "classes", random_shuffled_view_access=True)
    analyze_disagreements(repo, ALL_VIEWS, all_patterns, "methods", random_shuffled_view_access=True)


map_parallel(repos, preprocess, lambda foo: foo, f"Preprocessing all {len(repos)} repos")
