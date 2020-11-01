# -*- coding: utf-8 -*-
# flake8: noqa

from importlib import metadata as _meta

from pygments import token
from pygments.lexer import RegexLexer
from pygments_graphql import GraphqlLexer
from sphinx.highlighting import lexers

from py_gql.version import __version__


# Project information
project = "py_gql"

release = version = __version__
author = _meta.metadata(project)["author"]
copyright = f"Copyright 2019 {author}"

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
