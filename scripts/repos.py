# import psycopg2
# conn = psycopg2.connect(dbname='github', user='swa', password='squeak', port=5433)
# cur = conn.cursor()
# cur.execute("select url from ght.projects where deleted='f' and language='Java' limit 5")
# result = cur.fetchall()
# repos_db = ["/".join(url[0].split("/")[-2:]) for url in result]

repos_big = [
    # "eclipse/che",  # no java!
    "apache/flink",
    "apache/camel",
    "elastic/elasticsearch",
    "spring-projects/spring-boot",
    "spring-projects/spring-framework",
    "ReactiveX/RxJava",
    "kdn251/interviews",
    "square/retrofit",
    "google/guava",
    "PhilJay/MPAndroidChart",
    "owncloud/android",
    "nextcloud/android",
    "owntracks/android",
    "netty/netty",
    "skylot/jadx",
    "libgdx/libgdx",  # really big
    "chrisbanes/PhotoView",
    "jenkinsci/jenkins",
    # "TheAlgorithms/Java",
]

repos_medium = [
    # "eclipse/che",
    "apache/flink",
    "apache/camel",
    "elastic/elasticsearch",
    "spring-projects/spring-boot",
    "spring-projects/spring-framework",
    "ReactiveX/RxJava",

]

repos_small = [
    "jenkinsci/jenkins",
    # "eclipse/che",
    "elastic/elasticsearch",
]

repos_all = [
    'chrisbanes/PhotoView',
    'ErikBrendel/LD35',
    'ErikBrendel/LudumDare',
    'owntracks/android',
    'owncloud/android',
    'square/retrofit',
    'apache/log4j',
    'hunterhacker/jdom',
    'PhilJay/MPAndroidChart',
    'junit-team/junit4',
    'wrandelshofer/jhotdraw/JHotDraw',
    'wrandelshofer/jhotdraw/jhotdraw6',
    'nextcloud/android',
    # 'wumpz/jhotdraw',  # ignored - duplicate
    'kdn251/interviews',
    'wrandelshofer/jhotdraw/jhotdraw7',
    'skylot/jadx',
    'vanzin/jEdit',
    'jfree/jfreechart',
    'ReactiveX/RxJava',
    'wrandelshofer/jhotdraw/jhotdraw8',
    'jenkinsci/jenkins',
    'netty/netty',
    'google/guava',
    'libgdx/libgdx',
    'eclipse/aspectj.eclipse.jdt.core',
    'Waikato/weka-3.8',
    'spring-projects/spring-boot',
    'spring-projects/spring-framework',
    'apache/flink',
    'apache/camel',
    'elastic/elasticsearch'
]


# those are the ones i am using in my thesis
repos_and_versions = [
    ("hunterhacker/jdom:JDOM-2.0.6", [
        "JDOM-2.0.4",
        "JDOM-2.0.2",
        "JDOM-2.0.0",
    ]),
    ("junit-team/junit4:r4.13.2", [
        "r4.12",
        "r4.10",
        "r4.8",
        "r4.6",
    ]),
    ("PhilJay/MPAndroidChart:v2.2.5", [
        "v2.2.0",
        "v2.1.0",
        "v2.0.0",
    ]),
    ("netty/netty:netty-3.10.6.Final", [
        "netty-3.9.0.Final",
        "netty-3.6.0.Final",
        "netty-3.3.0.Final",
    ]),
    ("jfree/jfreechart:v1.5.3", [
        "v1.5.2",
        "v1.5.1",
        "v1.5.0",
    ]),
    ("apache/logging-log4j2:rel/2.14.1", [
        "rel/2.12.0",
        "rel/2.9.0",
        "rel/2.6",
        "rel/2.3",
        "rel/2.0",
    ]),
    ("hapifhir/hapi-fhir:v5.6.0", [
        "v5.4.0",
        "v5.2.0",
        "v5.0.0",
    ]),
    ("apache/hadoop:release-0.20.0", [
        "release-0.15.0",
        "release-0.10.0",
        "release-0.5.0",
    ]),
]

all_old_repos = [f"{repo.split(':')[0]}:{old_version}" for repo, old_versions in repos_and_versions for old_version in old_versions]
all_new_repos = [repo for repo, _old_versions in repos_and_versions]
