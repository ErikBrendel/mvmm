from local_repo import LocalRepo
from metrics import MetricManager

repos = [
    "ErikBrendel/LudumDare:e77400a84a77c0cf8cf8aea128b78c5c9c8ad81e",  # earlier
    "ErikBrendel/LudumDare:d2701514c871f5efa3ae5c9766c0a887c1f12252",  # later
]

metrics = ["structural", "evolutionary", "linguistic", "module_distance"]

for repo in repos:
    r = LocalRepo(repo)
    r.update()
    print(str(len(r.get_all_commits())) + " known commits, " + str(len(r.get_future_commits())) + " yet to come.")
    metric_graphs = [MetricManager.get(r, m) for m in metrics]
    for g in metric_graphs:
        g.print_statistics()
