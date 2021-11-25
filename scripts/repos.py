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

repos_multiview = [
    "jfree/jfreechart",
    # "apache/ant",  # evo view hangs and crashes
    # "apache/hadoop",  # too big?
    "hunterhacker/jdom",
    "eclipse/aspectj.eclipse.jdt.core",
    "vanzin/jEdit",  # private mirror
    "wumpz/jhotdraw",  # private mirror
    "wrandelshofer/jhotdraw/JHotDraw",
    "wrandelshofer/jhotdraw/jhotdraw6",
    "wrandelshofer/jhotdraw/jhotdraw7",
    "wrandelshofer/jhotdraw/jhotdraw8",
    "junit-team/junit4",
    # "junit-team/junit5",
    "apache/log4j",
    "Waikato/weka-3.8",
]

repos_manual = [
    # "wrandelshofer/jhotdraw/JHotDraw",
    # "wrandelshofer/jhotdraw/jhotdraw6",
    # "wrandelshofer/jhotdraw/jhotdraw7",
    # "wrandelshofer/jhotdraw/jhotdraw8",
    # "wumpz/jhotdraw",
    "ErikBrendel/LudumDare",
    "ErikBrendel/LD35",
    # "jenkinsci/jenkins",
    # "eclipse/aspectj.eclipse.jdt.core",  # from duerschmidt
    # "neuland/jade4j",
    "jfree/jfreechart",
    # "brettwooldridge/HikariCP",
    # "adamfisk/LittleProxy",
    # "dynjs/dynjs",
    # "SonarSource/sonarqube",
    # "eclipse/che",
    # "elastic/elasticsearch",
    # "apache/camel",
    # "jOOQ/jOOQ",
    # "netty/netty",
    # "ErikBrendel/ProgressiveImageEditor",
]

#repos_all = list(set(repos_multiview + repos_small + repos_medium + repos_big + repos_manual))
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

# select which one to use here
repos = repos_all


# those are the ones i'm using for my thesis
repos_and_versions = [
    ("apache/logging-log4j2:rel/2.14.1", [
        "rel/2.12.0",
        "rel/2.9.0",
        "rel/2.6",
        "rel/2.3",
        "rel/2.0",
    ]),
    ("jfree/jfreechart:v1.5.3", [
        "v1.5.0",
        "v1.0.18",
    ]),
    ("junit-team/junit4:r4.13.2", [
        "r4.12",
        "r4.10",
        "r4.8",
        "r4.6",
    ]),
    ("hunterhacker/jdom:JDOM-2.0.6", [
        "JDOM-2.0.3",
        "JDOM-2.0.0",
    ]),
    ("hapifhir/hapi-fhir:v5.6.0", [
        "v5.4.0",
        "v5.2.0",
        "v5.0.0",
    ]),
    ("apache/hadoop:release-0.23.0", [
        "release-0.20.0",
        "release-0.15.0",
        "release-0.10.0",
        "release-0.5.0",
    ]),
    ("PhilJay/MPAndroidChart:v3.0.0", [
        "v2.2.0",
        "v2.1.0",
        "v2.0.0",
    ]),
    ("netty/netty:netty-4.0.0.Final", [
        "netty-3.9.0.Final",
        "netty-3.6.0.Final",
        "netty-3.3.0.Final",
    ]),
]