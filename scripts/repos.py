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
