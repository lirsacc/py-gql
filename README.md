py-gql
======

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/lirsacc/py-gql/ci?logo=GitHub)](https://github.com/lirsacc/py-gql/actions?query=workflow%3Aci) [![Codecov](https://img.shields.io/codecov/c/github/lirsacc/py-gql.svg?logo=CodeCov)](https://codecov.io/gh/lirsacc/py-gql) [![PyPI](https://img.shields.io/pypi/v/py-gql.svg?logo=PyPi&logoColor=white)](https://pypi.org/project/py-gql/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/py-gql.svg?logo=python&logoColor=white) ![Wheel](https://img.shields.io/pypi/wheel/py-gql.svg) [![Read the Docs (version)](https://img.shields.io/readthedocs/pip/latest.svg?logoColor=white&logo=read-the-docs)](https://py-gql.readthedocs.io/)

py-gql is a pure python [GraphQL](http://facebook.github.io/graphql/) implementation aimed at creating GraphQL servers and providing common tooling.

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
def resolve_hello(*, value):
    return f"Hello {value}!"


result = graphql_blocking(schema, '{ hello(value: "Foo") }')
assert result.response() == {
    "data": {
        "hello": "Hello Foo!"
    }
}
```

For more usage examples, you can refer to the [User Guide](https://py-gql.readthedocs.io/en/latest/usage/index.html) and some more involved examples available in the [examples](./examples) folder.

The [tests](./tests) should also provide some contrived examples.

Goals & Status
--------------

This project was initially born as an experiment / learning project following some frustration with [graphql-core](https://github.com/graphql-python/graphql-core/) and [Graphene](https://github.com/graphql-python/graphene/) I encountered at work.

The main goals were originally to:

- Get a deeper understanding of GraphQL
- Provide an alternative to `graphql-core` which:

  - tracks the latest version of the spec (which `graphql-core` didn't at the time)
  - does so without being a port of the JS code which leads to some weird edge case when we tried to extend the library
  - keeps support for Python 2
  - (subjective) attempts to be a bit more usable for our use cases, the ideal result would sit somewhere in between `Graphene` and `graphql-core`
  - makes it easier for us to build / include some extra tooling such as custom tracing, custom validation and SDL based tools as well as builder infrastructure to support easily implementing graphql layers over existing data layers (such as ORM)

Not all these points are satisfied yet, and some have been changed over time, but py-gql should be ready for general use. It is however still in a fairly experimental phase and to reflect that versions are still in the `0.x.y`.The API is still subject to change as different part of the codebase are iterated on and are getting more use against production codebases.

Development setup
-----------------

Make sure you are using Python 3.6+ (you can run the tests under 3.5 but `other development tasks such as black are not guaranteed to work).

Clone this repo and create a virtualenv before installing the development dependencies:

```bash
git clone git@github.com:lirsacc/py-gql.git
python -m venv $WORKON_HOME/py-gql --copies
pip install -U -r dev-requirements.txt
pip install -e .
```

Development tasks are available through [invoke](http://www.pyinvoke.org/). Check [`tasks.py`](./tasks.py) or use `inv -l` to list all available tasks and `inv --help {TASK}` to get help on a specific task. Most of the tools used should be usable directly, but the tasks provide some common aliases and targets.

As a shortcut, `inv check` will run all checks that are normally run on CI (lint, typecheck and tests).

CI is done on [Github Actions](https://github.com/lirsacc/py-gql/actions).

### Branches

- The last tag should correspond to the latest release version
- `master` contains unreleased changes that are planned to be released
- `dev` is used for experimenting and hard changes such as rebase and force pushed should be expected. For now this is the branch I used in side projects and where most of the iteration happens.
