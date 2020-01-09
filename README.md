py-gql
======

[![CircleCI](https://img.shields.io/circleci/project/github/lirsacc/py-gql.svg?logo=circleci)](https://circleci.com/gh/lirsacc/workflows/py-gql) [![Codecov](https://img.shields.io/codecov/c/github/lirsacc/py-gql.svg?)](https://codecov.io/gh/lirsacc/py-gql) [![PyPI](https://img.shields.io/pypi/v/py-gql.svg)](https://pypi.org/project/py-gql/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/py-gql.svg?logo=python&logoColor=white) ![PyPI - Wheel](https://img.shields.io/pypi/wheel/py-gql.svg) [![Read the Docs (version)](https://img.shields.io/readthedocs/pip/latest.svg)](https://py-gql.readthedocs.io/)

py-gql is a pure python [GraphQL](http://facebook.github.io/graphql/) implementation aimed at creating GraphQL servers and tooling.

It supports:

- Parsing the GraphQL query language and schema definition language.
- Building a GraphQL type schema programatically and from Schema Definition files (including support for schema directives).
- Validating and Executing a GraphQL request against a type schema.

Quick links
-----------

- [Source Code & Issue Tracker](https://github.com/lirsacc/py-gql)
- [PyPI project](https://pypi.org/project/py-gql/)
- [Read The Docs](https://py-gql.readthedocs.io/)
- [Changelog](./CHANGES.md)

Installation
------------

```bash
pip install py-gql
```

For more details see [install.rst](docs/usage/install.rst).

Usage & Examples
----------------

### Hello World

```python
from py_gql import build_schema, graphql_blocking

schema = build_schema(
    """
    type Query {
        hello(value: String = "world"): String!
    }
    """
)


@schema.resolver("Query.hello")
def resolve_hello(*_, value):
    return f"Hello {value}!"


result = graphql_blocking(schema, '{ hello(value: "Foo") }')
assert result.response() == {
    "data": {
        "hello": "Hello Foo!"
    }
}
```

For more usage examples, you can refer to the [User Guide](https://py-gql.readthedocs.io/en/latest/usage/index.html) and some more involved examples available in the [examples](./examples) folder.

The [tests](./tests) should also provide some contrived exmaples.

Goals & Status
--------------

This project was initially born as an experiment / learning project following some frustration with [graphql-core](https://github.com/graphql-python/graphql-core/) and [Graphene](https://github.com/graphql-python/graphene/) I encountered at work.

The main goals were originally to:

- Get a deeper understanding of GraphQL
- Provide an alternative to `graphql-core` which:

  - tracks the latest version of the spec (which `graphql-core` didn't)
  - does so without being a port of the JS code which leads to some weird edge case when we tried to extend the library
  - keeps support for Python 2 (which `graphql-core-next`) didn't (this isn't a focus anymore and version 0.2 dropped Python 2 support).
  - (subjective) attempts to be a bit more usable for our use cases, the ideal result would sit somewhere in between `Graphene` and `graphql-core`
  - makes it easier for us to build / include some extra tooling such as custom tracing, custom validation and SDL based tools as well as builder infrastructure to support easily implementing graphql layers over existing data layers (such as ORM).

Not all these points are satisfied yet but py-gql should be ready for general use. It is however still in a fairly experimental phase and to reflect that versions are still in the `0.x.y`.The API is still subject to change as different part of the codebase are iterated on and are getting more use against production codebases.

Development setup
-----------------

Make sure you are using Python 3.6+ (you can run the tests under 3.5 but `black` and other development tasks are not guaranteed to work).

Clone this repo and create a virtualenv before installing the development dependencies:

```bash
git clone git@github.com:lirsacc/py-gql.git
python -m venv $WORKON_HOME/py-gql --copies
pip install -U -r dev-requirements.txt
pip install -e .
```

Development tasks are available through [invoke](http://www.pyinvoke.org/) (see: [`tasks.py`](./tasks.py)). Use `inv -l` to list all available tasks and `inv {TASKS} --help` to get help on a specific task:

```bash
$ inv -l
inv -l
Available tasks:

  benchmark          Run benchmarks
  black
  build              Build source distribution and wheel for upload to PyPI
  check              Run all checks (formatting, lint, typecheck and tests)
  clean              Remove test and compilation artifacts
  docs               Generate documentation
  flake8
  fmt (format)       Run formatters
  mypy (typecheck)
  sort-imports
  test               Run test suite (using: py.test)
```

Most tools should be usable directly, but the tasks provide some common aliases and targets. Each task should print the exact commands it runs.

### Branches

- The last tag should correspond to the latest release version
- `master` contains unreleased changes that are planned to be released
- `dev` is used for experimenting and hard changes such as rebase and force pushed should be expected (I plan to move to using specific feature branches for better organisation)
