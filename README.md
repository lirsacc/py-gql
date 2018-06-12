# PyGQL

> Implementation of GraphQL primitives for Python.
>
> This library should always track the latest version of the [spec](http://facebook.github.io/graphql/).

**:construction: WIP! Do not use this in production :construction:**

This is for now a learning project born out of some frustrations with [graphql-core](https://github.com/graphql-python/graphql-core/) and [Graphene](https://github.com/graphql-python/graphene/) I encountered at work and on personal projects. While they work fairly well and we still run with them in production I figured I could tackle the following goals better by starting this.

1.  personnally get a deeper understanding of GraphQL by implementing the spec.

2.  experiment and provide a (albeit subjectively) nicer interface for Python (aiming for something in between graphql-core and Graphene) which tracks the most recent graphql spec (~~graphql-core doesn't, e.g. `null` support which has been in limbo for a while~~, glad to see that doesn't seem to be the case anynmore) and doesn't expose Javascript idioms like returning `undefined` to denote an exception

3.  solve some performance issue we encountered with graphql-core at work (mostly handling of large result sets and making solving the N+1 issue easier + adding some hooks where we were missing them)

4.  (later) Some convenience helpers for generating schemas and generally making working with GraphQL easier. One candidate is [sqlalchemy](https://www.sqlalchemy.org/) integration.

For now, this is largely based on the [GraphQL JS](https://github.com/graphql/graphql-js) implementation and extensive test suite as the first goal is to get a working library covering the current spec and working synchronously. As such naming and implementation might be similar and there are some comments documenting the divergences; but it is not supposed to be a 1-1 port and the internals / api are meant to be iterated upon and diverge more over time once the current spec is implemented.

## TODO

-   [x] First heads down dev round = synchronous version of the spec that supports resolving complex queries ([8ea52113c280](https://github.com/lirsacc/py-gql/tree/8ea52113c280)).

-   **Spec review**

    -   [ ] Make sure we still match the newly releases spec ([June 2018](http://facebook.github.io/graphql/June2018/)), should already be the case but tehe latest changes may not have made it through

    -   [ ] Go over TODO/WARN/REVIEW comments and review marked behaviour

    -   [ ] Review all skipped / xfail tests and resolve issue

-   **Execution / Consuming a GraphQL schema**

    -   [x] Figure out the interface and implement custom execution + support async / parallel resolution of fields. (Done with the `ThreadPoolExecutor` and nested dispatch, still need interface for asyncio)
    -   [ ] Make subscriptions work in a spec compatible way without forcing user in a given observable library
    -   [ ] Support custom directives
    -   [ ] Figure a way to hook into the library (middlewares could be one, decorator on resolvers could also be nice). Main targets for this are custom dircetives and authorization / contextual schemas.
    -   [ ] Implement asyncio executor and entry point
    -   [ ] Review error handling as not all errors provide suggestions (not critical but nice to have) or exact source location.
    -   [ ] Benchmark / trace execution to identify bottlenecks and compare with graphql-core. The first implementation was aimed at correctness and understanding of the specification and not necessarily performance.
    -   [ ] Setup automated benchmark for execution, parsing, etc. to catch regressions
    -   [ ] Implement custom validators (e.g. query depth) and types (Date, Datetime, etc.)
    -   [ ] Provide a nicer interface for resolvers and returning / chaining `Future` objects

-   **SDL support**

    -   [x] Implement schema generation
    -   [ ] Support custom schema directives
    -   [ ] Support full type extension

-   **Documentation**

    -   [ ] Set up sphinx to generate some basic documentation
    -   [ ] Clean up docstrings and standardise on one format so Sphinx can generate consistent docs
    -   [ ] Write some usage examples and readable docs

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
