# -*- coding: utf-8 -*-
# flake8: noqa
# pylint: disable=all
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import imp
import os

about = imp.load_source("about", os.path.join("..", "py_gql", "__version__.py"))


# -- Project information -----------------------------------------------------


project = about.__title__
copyright = about.__copyright__
author = about.__author__

# The short X.Y version
version = about.__version__
# The full version, including alpha/beta/rc tags
release = about.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_parsers = {".md": "recommonmark.parser.CommonMarkParser"}

source_suffix = [".rst", ".md"]

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

html_context = {
    "project_links": [
        ("PyPI releases", "https://pypi.org/project/py-gql/"),
        ("Source Code", "https://github.com/lirsacc/py_gql/"),
        ("Issue Tracker", "https://github.com/lirsacc/py_gql/issues/"),
    ]
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#

FONT = "IBM Plex Sans"
CODE_FONT = "IBM Plex Mono"
HEADING_FONT = FONT

html_theme_options = {
    "canonical_url": "",
    "analytics_id": "",
    "github_user": "lirsacc",
    "github_repo": "py-gql",
    "fixed_sidebar": True,
    "codecov_button": False,
    "github_banner": False,
    "github_button": False,
    "sidebar_collapse": True,
    "show_relbars": False,
    "font_family": FONT,
    "caption_font_family": FONT,
    "head_font_family": HEADING_FONT,
    "code_font_family": CODE_FONT,
    "description": about.__description__,
    "show_related": True,
    # "page_width": "1200px",
    # "sidebar_width": "300px",
}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
html_sidebars = {
    "**": [
        "about.html",
        "sidebarlinks.html",
        "navigation.html",
        "relations.html",
        "sourcelink.html",
        "searchbox.html",
    ]
}


# -- Extension configuration -------------------------------------------------

autodoc_member_order = "bysource"
autoclass_content = "both"

intersphinx_mapping = {"python": ("https://docs.python.org/3/", None)}

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Pygments custom lexer ---------------------------------------------------
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
