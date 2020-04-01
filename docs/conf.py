# -*- coding: utf-8 -*-
# flake8: noqa

import os

from pygments import token
from pygments.lexer import RegexLexer
from pygments_graphql import GraphqlLexer
from sphinx.highlighting import lexers

from py_gql import _pkg


# Project information

project = _pkg.__title__
copyright = _pkg.__copyright__
author = _pkg.__author__
version = _pkg.__version__
release = _pkg.__version__

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

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
# language = "en"
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML Config & Theme config
html_theme = "documenteer"
html_theme_path = ["."]
html_static_path = ["_static"]
templates_path = ["_templates"]
html_last_updated_fmt = ""

html_use_index = True
html_domain_indices = True
html_show_sourcelink = True

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

# autodoc_member_order = "bysource"
autoclass_content = "both"
set_type_checking_flag = True
intersphinx_mapping = {"python": ("https://docs.python.org/3/", None)}
html_add_permalinks = "#"
napoleon_use_param = True

# Spelling checks
spelling_show_suggestions = True

lexers["graphql"] = GraphqlLexer(startinline=True)
