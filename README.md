PyGQL
=====

> Implementation of GraphQL primitives for Python.

**WARNING: This is not production ready**

This is for now a learning project born out of frustration with graphql-core and Graphene. The main goals for me are in order of importance:

1. personnally get a deeper understanding of GraphQL by implementing the spec.

2. experiment and provide a (albeit subjectively) nicer interface for Python (aiming for something in between graphql-core and Graphene) which tracks the most recent graphql spec (graphql-core doesn't, e.g. `null` support which has been in limbo for a while) and doesn't expose non Python concepts like returning `undefined` to denote an exception

3. solve some performance issue we encountered with graphql-core at work (mostly handling of large result sets and making solving the N+1 issue easier + adding some hooks where we were missing them)

4. (optional) Some kind of sqlalchemy integration / automation for simple table objects (i.e. not relying on the ORM which I tend to not use), most likely as a separate module / extra require

Regardless of points 2 / 3 I am not trying to diminish the work that went into Graphene / graphql-core (which we still use in production) but figured this would be a nice approach at addressing these pet peeves coupled with 1 which I wanted to do anyways. The interface is not meant to be as high level as graphene and provide abstraction around regular classes but mostly meant to work with standard dicts.

For now, this is largely based on the [GraphQL JS](https://github.com/graphql/graphql-js) implementation and extensive test suite as the first goal is to get a working library covering the current spec and working synchronously. As such naming and implementation might be similar and there are some comments documenting the divergences; but it is not supposed to be a 1-1 port and the internals / api are meant to be iterated upon and diverge more over time once the current spec (and some of the draft spec) is implemented. 

This library should always track the latest version of the [spec](http://facebook.github.io/graphql/) which is currently the [October 2016](http://facebook.github.io/graphql/October2016) version.


Note on IDL / Schema definitions
--------------------------------

At the time of writing (25 May 2018) the Schema definition language or IDL is part of the [working draft](http://facebook.github.io/graphql/draft) and not the current spec. Support for it in this library is partial and not guaranteed. Currently supported features are:

- parsing such documents into AST nodes (behind a flag)
- traversing the resulting AST
- validating the resulting AST according to the working draft 

There is currently no mechanism to generate an executable schema from such an AST but most of the tools to implement this should be available.

TODO
----

- [ ] First heads down dev round = synchronous version of the spec that supports resolving complex queries.

- [ ] Go over TODO/WARN/REVIEW comments and review marked behaviour

- [ ] Review all skipped / xfail tests and resolve issue

- [ ] Review error handling as not all errors provide suggestions (not critical but nice to have) or exact source location.

- Execution
  - Figure out the interface and implement custom execution + support async / parallel resolution of fields. 
    - Currently thinking of going with something based on the `concurrent.{Future|Executor}` concepts.
    - Current targetis executing resolvers in threads and in the event loop (`asyncio`, `trio`, etc.)
  - Evaluate solution to expose subsciption behaviour
  - Figure a way to hook into the library (middlewares could be one, decorator on resolvers could also be nice). Main targets for this are custom dircetives and authorization / contextual schemas.

- Documentation
    - [ ] Set up sphinx to generate some basic documentation
    - [ ] Clean up docstrings and standardise on one format so Sphinx can generate docs
    - [ ] Write some usage examples and readable docs

- [ ] Benchmark / trace execution to identify bottlenecks, compare with graphql-core. The first implementation was aimed at correctness and understanding of the specification and not necessarily performance.


Development
-----------

- Create a virtualenv: `python3 -m venv $WORKON_HOME/py-gql`.
- Initially you can install the dependencies with `pip install -r dev-requirements.txt` and then just run `inv deps`.
- All dev tasks are run with [`invoke`](http://www.pyinvoke.org/), use `inv -l` to list all available tasks.
- Tests are run with [`pytest`](https://docs.pytest.org/en/latest/) and live in the `tests` directory.
