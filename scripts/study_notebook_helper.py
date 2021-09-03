from local_repo import *
import re


def format_code(content: str, other_path: str) -> str:
    other_path_parts = other_path.split("/")
    if not any(part.endswith(".java") for part in other_path_parts):
        other_path_parts = [other_path_parts[-1]]
    else:
        while any(part.endswith(".java") for part in other_path_parts):
            other_path_parts = other_path_parts[1:]
    content_no_html = content.replace("<", "&lt;").replace(">", "&gt;")
    # language=HTML
    replacement = r'<mark style="background-color: #b28549">\1</mark>'
    return re.sub(fr"""\b({"|".join(other_path_parts)})\b""", replacement, content_no_html)


# language=HTML
OWN_STYLE = """
<style>
a {
    color: blue;
}
</style>
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
