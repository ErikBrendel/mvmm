from local_repo import *

OWN_STYLE = """
<style type="text/css">
a {
    color: blue;
}
</style>
"""

# Extracted from here: https://github.com/PrismJS/prism-themes
# https://raw.githubusercontent.com/PrismJS/prism-themes/master/themes/prism-darcula.css
# cannot be used as css link directly, due to "X-Content-Type-Options: nosniff"
PRISM_HIGHLIGHTING = """
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/themes/prism-okaidia.min.css"/>
<style type="text/css">
/**
 * Darcula theme
 *
 * Adapted from a theme based on:
 * IntelliJ Darcula Theme (https://github.com/bulenkov/Darcula)
 *
 * @author Alexandre Paradis <service.paradis@gmail.com>
 * @version 1.0
 */

code[class*="language-"],
pre[class*="language-"] {
    color: #a9b7c6;
    font-family: Consolas, Monaco, 'Andale Mono', monospace;
    direction: ltr;
    text-align: left;
    white-space: pre;
    word-spacing: normal;
    word-break: normal;
    line-height: 1.5;

    -moz-tab-size: 4;
    -o-tab-size: 4;
    tab-size: 4;

    -webkit-hyphens: none;
    -moz-hyphens: none;
    -ms-hyphens: none;
    hyphens: none;
}

pre[class*="language-"]::-moz-selection, pre[class*="language-"] ::-moz-selection,
code[class*="language-"]::-moz-selection, code[class*="language-"] ::-moz-selection {
    color: inherit;
    background: rgba(33, 66, 131, .85);
}

pre[class*="language-"]::selection, pre[class*="language-"] ::selection,
code[class*="language-"]::selection, code[class*="language-"] ::selection {
    color: inherit;
    background: rgba(33, 66, 131, .85);
}

/* Code blocks */
pre[class*="language-"] {
    padding: 1em;
    margin: .5em 0;
    overflow: auto;
}

:not(pre) > code[class*="language-"],
pre[class*="language-"] {
    background: #2b2b2b;
}

/* Inline code */
:not(pre) > code[class*="language-"] {
    padding: .1em;
    border-radius: .3em;
}

.token.comment,
.token.prolog,
.token.cdata {
    color: #808080;
}

.token.delimiter,
.token.boolean,
.token.keyword,
.token.selector,
.token.important,
.token.atrule {
    color: #cc7832;
}

.token.operator,
.token.punctuation,
.token.attr-name {
    color: #a9b7c6;
}

.token.tag,
.token.tag .punctuation,
.token.doctype,
.token.builtin {
    color: #e8bf6a;
}

.token.entity,
.token.number,
.token.symbol {
    color: #6897bb;
}

.token.property,
.token.constant,
.token.variable {
    color: #9876aa;
}

.token.string,
.token.char {
    color: #6a8759;
}

.token.attr-value,
.token.attr-value .punctuation {
    color: #a5c261;
}

.token.attr-value .punctuation:first-child {
    color: #a9b7c6;
}

.token.url {
    color: #287bde;
    text-decoration: underline;
}

.token.function {
    color: #ffc66d;
}

.token.regex {
    background: #364135;
}

.token.bold {
    font-weight: bold;
}

.token.italic {
    font-style: italic;
}

.token.inserted {
    background: #294436;
}

.token.deleted {
    background: #484a4a;
}

code.language-css .token.property,
code.language-css .token.property + .token.punctuation {
    color: #a9b7c6;
}

code.language-css .token.id {
    color: #ffc66d;
}

code.language-css .token.selector > .token.class,
code.language-css .token.selector > .token.attribute,
code.language-css .token.selector > .token.pseudo-class,
code.language-css .token.selector > .token.pseudo-element {
    color: #ffc66d;
}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0//components/prism-core.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/components/prism-clike.js" defer></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.0/components/prism-java.js" defer></script>
<script type="text/javascript" defer async=false>setTimeout(() => Prism.highlightAll(), 1000);</script>
"""
