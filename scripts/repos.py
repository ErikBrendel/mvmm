# import psycopg2
# conn = psycopg2.connect(dbname='github', user='swa', password='squeak', port=5433)
# cur = conn.cursor()
# cur.execute("select url from ght.projects where deleted='f' and language='Java' limit 5")
# result = cur.fetchall()
# repos_db = ["/".join(url[0].split("/")[-2:]) for url in result]

repos_big = [
    "square/okhttp",
    "eclipse/che",
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
    "square/okhttp",
    "eclipse/che",
    "apache/flink",
    "apache/camel",
    "elastic/elasticsearch",
    "spring-projects/spring-boot",
    "spring-projects/spring-framework",
    "ReactiveX/RxJava",

]

repos_small = [
    "square/okhttp",
    "jenkinsci/jenkins",
    "eclipse/che",
    "elastic/elasticsearch",
]

repos_multiview = [
    "apache/ant",
    "apache/hadoop",
    "hunterhacker/jdom",
    "eclipse/eclipse.jdt.core",
    "vanzin/jEdit",  # private mirror
    "jfree/jfreechart",
    "wumpz/jhotdraw",  # private mirror
    "junit-team/junit4",
    # "junit-team/junit5",
    "apache/log4j",
    "Waikato/weka-3.8",
]

# select which one to use here
repos = repos_multiview
