from local_repo import *
import re


def get_path_end_parts(path: str) -> Set[str]:
    path_parts = path.split("/")
    if not any(part.endswith(".java") for part in path_parts):
        path_parts = [path_parts[-1]]
    else:
        while any(part.endswith(".java") for part in path_parts):
            path_parts = path_parts[1:]
    return set(path_parts)


def format_code(content: str, own_path: str = None, other_path: str = None) -> str:
    lines = len(content.splitlines())
    if lines > 1000:
        return f"// Too much content to display: {lines} lines!"
    content_no_html = content.replace("<", "&lt;").replace(">", "&gt;")
    if other_path is None:
        return content_no_html
    own_parts = get_path_end_parts(own_path)
    other_parts = get_path_end_parts(other_path)
    for p in own_parts:
        if p in other_parts:
            other_parts.remove(p)
    # language=HTML
    replacement = r'<mark style="background-color: #b28549">\1</mark>'
    return re.sub(fr"""\b({"|".join(other_parts)})\b""", replacement, content_no_html)


def make_path_overview_html(r: LocalRepo, m0: str, m1: str) -> str:
    m0_parts = m0.split("/")
    m1_parts = m1.split("/")
    common_prefix_length = get_common_prefix_length(m0_parts, m1_parts)
    common_prefix = make_path_html(r, "", m0_parts[:common_prefix_length])
    prefix_path = "/".join(m0_parts[:common_prefix_length]) + "/"
    m0_rest = make_path_html(r, prefix_path, m0_parts[common_prefix_length:])
    m1_rest = make_path_html(r, prefix_path, m1_parts[common_prefix_length:])
    # language=HTML
    result = f"""
        <table style="border-collapse: collapse; font-family: monospace; border: 1px solid black;">
            <tr>
                <td rowspan="2" style="line-height: 100%; background-color: white;">{common_prefix}</td>
                <td style="text-align: left; border: 1px solid black; background-color: white;">{m0_rest}</td>
            </tr>
            <tr><td style="text-align: left; border: 1px solid black; background-color: white;">{m1_rest}</td></tr>
        </table>
    """
    return result


def make_path_html(r: LocalRepo, path_prefix: str, path_parts: List[str]) -> str:
    return " / ".join(
        f"""{"<b>" if part.endswith("." + r.type_extension()) else ""}<a target="_blank"
               href="{r.url_for(path_prefix + "/".join(path_parts[:i+1]))}"
               title="{path_prefix + "/".join(path_parts[:i+1])}">
        {part}
        </a>{"</b>" if part.endswith("." + r.type_extension()) else ""}"""
        for i, part in enumerate(path_parts)
    )


def make_tree_comparison_html(left_node: RepoTree, right_node: RepoTree, get_url: Callable[[str, bool], str]) -> Tuple[str, str]:
    """
    :param get_url: given a path and a bool (left True, right False), get the url for it
    """
    left_children = set(left_node.children.keys())
    right_children = set(right_node.children.keys())
    same_named = left_children.intersection(right_children)
    left_only = left_children.difference(same_named)
    right_only = right_children.difference(same_named)
    unchanged = set([name for name in same_named if left_node.children[name].probably_equals(right_node.children[name])])
    modified = same_named.difference(unchanged)

    def make_result(only: Set[str], base_path: str, is_left: bool) -> str:
        result: List[str] = []

        def add_data(data: Set[str], title: str):
            if len(data) > 0:
                result.append(f"<b>{title} ({len(data)}):</b>")
                for e in sorted(data):
                    result.append(f"""- <a href="{get_url(base_path + "/" + e, is_left)}">{e}</a>""")

        add_data(only, "Only in this version")
        add_data(modified, "Modified")
        add_data(unchanged, "Unchanged")

        return "<br>".join(result)

    return make_result(left_only, left_node.get_path(), True), make_result(right_only, left_node.get_path(), False)


# language=HTML
OWN_STYLE = """
<style>
a {
    color: blue;
}
table {
    border-collapse: collapse;
}
</style>
"""

# language=HTML
ADD_LINKS_TO_RENDERED_IMAGES = """
<script>
function addLinksToImages() {
    const imageContainers = document.getElementsByClassName("jp-RenderedImage");
    for (const container of imageContainers) {
        if (container.childNodes.length > 1) continue; // already handled
        const link = document.createElement("a");
        link.href = container.childNodes[0].src;
        link.target = "_blank";
        link.text = "Open image in new tab";
        container.appendChild(link);
    }
    setTimeout(() => addLinksToImages(), 1000);
}
addLinksToImages();

</script>
"""

# language=HTML
HORIZONTAL_RADIO_BUTTONS = """
<style>
    .widget-radio-box {
        flex-direction: row !important;     
        margin-bottom: 0 !important;
    }
    .widget-radio-box label{
        margin:5px !important;
        /*width: 120px !important;*/
    }
</style>
"""

import requests
import requests_cache
requests_cache.install_cache()
def get_from_web(url: str) -> str:
    return requests.get(url).text

# language=HTML
PRISM_HIGHLIGHTING = f"""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/themes/prism-okaidia.min.css"/>
<style>
{get_from_web("https://raw.githubusercontent.com/PrismJS/prism-themes/master/themes/prism-darcula.css")}
</style>
<script async>
{get_from_web("https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/components/prism-core.min.js")}
{get_from_web("https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/components/prism-clike.min.js")}
{get_from_web("https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/components/prism-java.min.js")}
{get_from_web("https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/plugins/keep-markup/prism-keep-markup.min.js")}
Prism.highlightAll();
//setTimeout(() => Prism.highlightAll(), 1000);
</script>
"""
