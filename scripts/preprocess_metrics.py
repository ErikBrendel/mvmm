import random
import sys
from time import sleep

from local_repo import LocalRepo
from util import map_parallel
from repos import repos_and_versions


def preprocess(job_info: str):
    try:
        from local_repo import LocalRepo
        import psutil

        if len(repos_and_versions) > 3:
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

        r = LocalRepo.for_name(job_info[1])
        if job_info[0] == "analyze":
            from study_common import TAXONOMY
            from analysis import analyze_disagreements, ALL_VIEWS
            all_patterns = [p for p, n, d in TAXONOMY]
            analyze_disagreements(r, ALL_VIEWS, all_patterns, "classes", random_shuffled_view_access=True)
            analyze_disagreements(r, ALL_VIEWS, all_patterns, "methods", random_shuffled_view_access=True)
        if job_info[0] == "views":
            from analysis import analyze_disagreements, ALL_VIEWS
            from metrics import MetricManager
            views_shuffled = ALL_VIEWS[:]
            random.shuffle(views_shuffled)
            for v in views_shuffled:
                MetricManager.get(r, v, ignore_post_processing=True)
        elif job_info[0] == "bb":
            from blue_book_metrics import BBContext
            BBContext.for_repo(r).find_all_disharmonies()
        elif job_info[0] == "ref":
            from refactorings_detection import get_classes_being_refactored_in_the_future
            get_classes_being_refactored_in_the_future(r, job_info[2], use_filter=False)
    except Exception as e:
        print("Exception!:")
        print(e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


# this loop also ensures in sync that they are all cloned
jobs = []
for new_name, older_versions in repos_and_versions:
    new_repo = LocalRepo.for_name(new_name)
    # new_repo.update()
    for old_version in older_versions:
        old_repo = new_repo.get_old_version(old_version)
        jobs.append(("ref", new_name, old_version))
        jobs.append(("analyze", old_repo.name))
        jobs.append(("bb", old_repo.name))
    jobs.append(("analyze", new_repo.name))
    jobs.append(("views", new_repo.name))

print(jobs)
map_parallel(jobs, preprocess, lambda foo: foo,
             f"Preprocessing all {len(repos_and_versions)} repos",
             force_non_parallel=False)
