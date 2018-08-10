py-gql
======

![CircleCI](https://img.shields.io/circleci/project/github/lirsacc/py-gql.svg?logo=circleci)
![Codecov](https://img.shields.io/codecov/c/github/lirsacc/py-gql.svg?)
![PyPI](https://img.shields.io/pypi/v/py-gql.svg)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/py-gql.svg?logo=python&logoColor=white)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/Django.svg)
![Read the Docs (version)](https://img.shields.io/readthedocs/pip/latest.svg)


py-gql is a [GraphQL](http://facebook.github.io/graphql/) implementation of for Python aimed at creating GraphQL servers.

It supports:

- Parsing the GraphQL query language and schema definition language
- Building a GraphQL type schema programatically and from Schema Definition
  files (including support for schema directives)
- Validating and Executing a GraphQL request against a type schema

Quick links
-----------

- [Source Code](https://github.com/lirsacc/py-gql)
- [PyPI project](https://pypi.org/project/py-gql/)
- [Read The Docs](https://py-gql.readthedocs.io/)
- [Changelog](./CHANGES.rst)

Installation
------------

```
pip install py-gql
```

For more details see [install.rst](docs/usage/install.rst).

Usage & Examples
----------------

### Hello World

```.python
from py_gql import graphql
from py_gql.schema.build import make_executable_schema

schema = make_executable_schema("""
type Query {
    hello: String!
}
""")

assert graphql(schema, "{ hello }", initial_value={"hello": "world"}).response() == {
    "data": {
        "hello": "world"
    }
}
```

- See the [User Guide](https://py-gql.readthedocs.io/en/latest/usage/index.html)
- You can refer to the [tests](./tests) for some simple usage examples
- Some more involved examples are available in the [examples](./examples) folder.

Goals & Status
--------------

This project was initially born as an experiment / learning project following some frustration with with [graphql-core](https://github.com/graphql-python/graphql-core/) and [Graphene](https://github.com/graphql-python/graphene/) we encountered at work.

The main goals were to:

- Get a deeper understanding of the GraphQL specification and available implementations.
- Provide an alternative to graphql-core that:
  - tracks the lastest version of the GraphQL specification
  - does not strictly attempt to track the reference javascript implementation
  - (subjective) attempts to be a bit more usable for our use cases, the ideal result would sit somewhere in between Graphene and graphql-core
- Make it easier for us to build / include some extra tooling such as custom tracing, custom validation and SDL based tools.
- Maintain Python 2.7 compatibility due to work projects still running it.

**Note:** The [graphql-core-next](https://github.com/graphql-python/graphql-core-next) project is currently working on providing a more up to date alternative to graphql-core. Importantly for us it tracks the specification and includes SDL based schema creation; however it is Python 3+ only for now and aims at closely tracking the JS implementation.

### Current status

So far every aspect of the library that is necessary for us to start using it in production has been implemented; the most notable ommission being subscribtions. For a more detailled roadmap of what remains to be done before calling this a v1, see [Issue #1](https://github.com/lirsacc/py-gql/issues/1).

- This library has been written from scratch but it uses ideas from both [graphql-js](https://github.com/graphql/graphql-js) (built and maintained by Facebook) and [graphql-core](https://github.com/graphql-python/graphql-core/) (built and maintained by Syrus Akbary). While some implementation and design choices are very similar to this prior work, this will most likely diverge in the future.
- The test suite is quite extensive and largely based on the graphql-js's test suite
- Supported Python versions are currently 2.7 and 3.5+ on CPython. I'd like to confirm support for PyPy but haven't had time to test it properly yet as I don't regularly use it.


Development setup
-----------------

Make sure you are using Python 3.6+.

Clone this repo and create a virtualenv before installing the development dependencies:

```
git clone git@github.com:lirsacc/py-gql.git
python -m venv $WORKON_HOME/py-gql --copies
pip install -r dev-requirements.txt
```

From there, most development tasks are available through [invoke](http://www.pyinvoke.org/).

Use `inv -l` to list all available tasks and `inv {TASKS} --help` to get help on a specific task.
