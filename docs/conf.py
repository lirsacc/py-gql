# -*- coding: utf-8 -*-
# flake8: noqa

from pygments import token
from pygments.lexer import RegexLexer
from pygments_graphql import GraphqlLexer
from sphinx.highlighting import lexers

from pygments import token
from pygments.lexer import RegexLexer
from pygments_graphql import GraphqlLexer
from sphinx.highlighting import lexers

from py_gql import _pkg


# Project information


# Project information
project = _pkg.__title__
copyright = _pkg.__copyright__
author = _pkg.__author__
version = _pkg.__version__
release = _pkg.__version__

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
    "sphinx_markdown_tables",
]

master_doc = "index"
# language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

templates_path = ["_templates"]

# HTML Config & Theme config
html_theme = "theme"
html_theme_path = ["."]

# html_logo = "..."

html_add_permalinks = "#"
html_static_path = ["_static"]
html_last_updated_fmt = ""

html_use_index = True
html_domain_indices = True
html_show_sourcelink = True

html_title = project
html_short_title = project

html_theme_options = {
    # "description": _pkg.__description__,
    "sidebar_links": [
        ("PyPI", "https://pypi.org/project/py-gql/"),
        ("Github", "https://github.com/lirsacc/py-gql/"),
    ],
}

# Autodoc
# autodoc_member_order = "bysource"
autoclass_content = "both"
set_type_checking_flag = True
intersphinx_mapping = {"python": ("https://docs.python.org/3/", None)}
napoleon_use_param = True

# Spelling suggestions
spelling_show_suggestions = True

# Custom GraphQL lexer
lexers["graphql"] = GraphqlLexer(startinline=True)
