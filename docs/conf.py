# -*- coding: utf-8 -*-
# flake8: noqa

import os

from py_gql import _pkg

# Project information

project = _pkg.__title__
copyright = _pkg.__copyright__
author = _pkg.__author__
version = _pkg.__version__
release = _pkg.__version__

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML Config & Theme config

html_theme = "documenteer"
html_theme_path = ["."]
html_static_path = ["_static"]
templates_path = ["_templates"]
pygments_style = "borland"
html_static_path = ["_static"]

html_context = {
    "project_links": [
        ("PyPI releases", "https://pypi.org/project/py-gql/"),
        ("Source Code", "https://github.com/lirsacc/py-gql/"),
        ("Issue Tracker", "https://github.com/lirsacc/py-gql/issues/"),
    ]
}

CODE_FONT = "Roboto Mono"

html_theme_options = {
    "canonical_url": "",
    "analytics_id": "",
    "github_user": "lirsacc",
    "github_repo": "py-gql",
    # "fixed_sidebar": True,
    "github_corner": True,
    "sidebar_collapse": True,
    "github_star_button": True,
    "github_issue_button": True,
    "show_relbars": False,
    "code_font_family": CODE_FONT,
    "logo_font_family": CODE_FONT,
    "description": _pkg.__description__,
    "show_related": True,
}

# Extensions

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.spelling",
    "recommonmark",
]

# autodoc_member_order = "bysource"
autoclass_content = "both"
set_type_checking_flag = True
intersphinx_mapping = {"python": ("https://docs.python.org/3/", None)}
html_add_permalinks = "#"
napoleon_use_param = True

spelling_show_suggestions = True

# Pygments custom lexer
from pygments.lexer import RegexLexer
from pygments import token
from sphinx.highlighting import lexers


class GraphqlLexer(RegexLexer):

    name = "GraphQL"
    aliases = ["graphql", "gql"]
    filenames = ["*.graphql", "*.gql"]
    mimetypes = ["application/graphql"]

    tokens = {
        "root": [
            (r"#.*", token.Comment.Singline),
            (r"\.\.\.", token.Operator),
            (r'"[\u0009\u000A\u000D\u0020-\uFFFF]*"', token.String.Double),
            (
                r"(-?0|-?[1-9][0-9]*)"
                r"(\.[0-9]+[eE][+-]?[0-9]+|\.[0-9]+|[eE][+-]?[0-9]+)",
                token.Number.Float,
            ),
            (r"(-?0|-?[1-9][0-9]*)", token.Number.Integer),
            (r"\$+[_A-Za-z][_0-9A-Za-z]*", token.Name.Variable),
            (r"[_A-Za-z][_0-9A-Za-z]+\s?:", token.Text),
            (
                r"(type|query|mutation|@[a-z]+|on|true|false|null)\b",
                token.Keyword.Type,
            ),
            (r"[!$():=@\[\]{|}]+?", token.Punctuation),
            (r"[_A-Za-z][_0-9A-Za-z]*", token.Keyword),
            (r"(\s|,)", token.Text),
        ]
    }


lexers["graphql"] = GraphqlLexer(startinline=True)
