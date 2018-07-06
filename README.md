# PyGQL

> Implementation of GraphQL primitives for Python.
>
> This library should always track the latest version of the [spec](http://facebook.github.io/graphql/).

**:construction: WIP! Do not use this in production :construction:**

[![CircleCI](https://circleci.com/gh/lirsacc/py-gql/tree/master.svg?style=svg)](https://circleci.com/gh/lirsacc/py-gql/tree/master)

**Roadmap**: See issue #1 for roadmap to version 1.

This is for now a learning project born out of some frustrations with [graphql-core](https://github.com/graphql-python/graphql-core/) and [Graphene](https://github.com/graphql-python/graphene/) I encountered at work and on personal projects. While they work fairly well and we still run with them in production I figured I could tackle the following goals better by starting this.

1.  personnally get a deeper understanding of GraphQL by implementing the spec.

2.  experiment and provide a (albeit subjectively) nicer interface for Python (aiming for something in between graphql-core and Graphene) which tracks the most recent graphql spec (~~graphql-core doesn't, e.g. `null` support which has been in limbo for a while~~, glad to see that doesn't seem to be the case anynmore) and doesn't expose Javascript idioms like returning `undefined` to denote an exception

3.  solve some performance issue we encountered with graphql-core at work (mostly handling of large result sets and making solving the N+1 issue easier + adding some hooks where we were missing them)

4.  (later) Some convenience helpers for generating schemas and generally making working with GraphQL easier. One candidate is [sqlalchemy](https://www.sqlalchemy.org/) integration.

For now, this is largely based on the [GraphQL JS](https://github.com/graphql/graphql-js) implementation and extensive test suite as the first goal is to get a working library covering the current spec and working synchronously. As such naming and implementation might be similar and there are some comments documenting the divergences; but it is not supposed to be a 1-1 port and the internals / api are meant to be iterated upon and diverge more over time once the current spec is implemented.

## Examples

Refer to the respective `README.md` in each directory for specific instructions.

To install the dependencies for **all** the examples (should not conflict), run: `pip install -r examples/**/requirements.txt`.

**List of examples:**

-   [SWAPI Proxy](./examples/swapi-proxy): A graphql server example which proxies all requests to [SWPAPI](https://swapi.co) and generates the runtime schema from an SDL.

## Development

-   Create a virtualenv: `python3 -m venv $WORKON_HOME/py-gql`.
-   Initially you can install the dependencies with `pip install -r dev-requirements.txt` and then just run `inv deps`.
-   All dev tasks are run with [`invoke`](http://www.pyinvoke.org/), use `inv -l` to list all available tasks.
-   Tests are run with [`pytest`](https://docs.pytest.org/en/latest/) and live in the `tests` directory.
