import random
import sys
from time import sleep

from local_repo import LocalRepo
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
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.13.0"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.12.0"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.11.0"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.10.0"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.9.0"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.8"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.7"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.6"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.5"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.4"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.3"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.2"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.1"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.0"),
    ("jfree/jfreechart:v1.5.3", "v1.0.18"),
    ("jfree/jfreechart:v1.5.3", "v1.5.0"),
    ("junit-team/junit4:r4.13.2", "r4.6"),
    ("apache/logging-log4j2:rel/2.14.1", "rel/2.11.2"),
]\
        + [("hapifhir/hapi-fhir:v1.0", f"v0.{v}") for v in range(4, 10)]\
        + [("hapifhir/hapi-fhir:v2.0", f"v1.{v}") for v in range(0, 7)]\
        + [("hapifhir/hapi-fhir:v3.0.0", f"v2.{v}") for v in range(0, 6)]\
        + [("hapifhir/hapi-fhir:v4.0.0", f"v3.{v}.0") for v in range(0, 9)]\
        + [("hapifhir/hapi-fhir:v5.6.0", f"v5.{v}.0") for v in range(0, 6)]\
        + [("apache/hadoop:release-0.15.0", f"release-0.{v}.0") for v in range(1, 16)]\
        + [("apache/hadoop:release-0.23.11", f"release-0.{v}.0") for v in range(1, 24)]


def preprocess(job_info: str):
    try:
        from local_repo import LocalRepo
        import psutil

        # we want to wait until the system is not totally overloaded before starting our job
        # https://www.geeksforgeeks.org/how-to-get-current-cpu-and-ram-usage-in-python/
        sleep(random.randrange(1, 100) / 10.0)
        cpu_usage = psutil.cpu_percent(0.5)
        ram_usage = psutil.virtual_memory()[2]
        while cpu_usage > 85 or ram_usage > 85:
            print(f"Waiting for less CPU load or memory usage before starting job: {cpu_usage=}, {ram_usage=}")
            sleep(random.randrange(10, 100) / 10.0)
            cpu_usage = psutil.cpu_percent(0.5)
            ram_usage = psutil.virtual_memory()[2]

        r = LocalRepo(job_info[1])
        if job_info[0] == "views":
            from study_common import TAXONOMY
            from analysis import analyze_disagreements, ALL_VIEWS
            all_patterns = [p for p, n, d in TAXONOMY]
            analyze_disagreements(r, ALL_VIEWS, all_patterns, "classes", random_shuffled_view_access=True)
            analyze_disagreements(r, ALL_VIEWS, all_patterns, "methods", random_shuffled_view_access=True)
        elif job_info[0] == "bb":
            from blue_book_metrics import BBContext
            BBContext.for_repo(r).find_all_disharmonies()
        elif job_info[0] == "ref":
            from refactorings_detection import get_classes_being_refactored_in_the_future_heuristically_filtered
            get_classes_being_refactored_in_the_future_heuristically_filtered(r, job_info[2])
    except Exception as e:
        print("Exception!:")
        print(e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


# this loop also ensures in sync that they are all cloned
jobs = []
for jobs_repo_info in repos:
    if isinstance(jobs_repo_info, str):
        old_repo = LocalRepo(jobs_repo_info)
    else:
        new_name, old_version = jobs_repo_info
        old_repo = LocalRepo(new_name).get_old_version(old_version)
        jobs.append(("ref", new_name, old_version))
    jobs.append(("views", old_repo.name))
    jobs.append(("bb", old_repo.name))

print(jobs)
map_parallel(jobs, preprocess, lambda foo: foo,
             f"Preprocessing all {len(repos)} repos",
             force_non_parallel=False)
