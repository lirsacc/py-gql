py-gql
======

[![CircleCI](https://circleci.com/gh/lirsacc/py-gql/tree/master.svg?style=svg)](https://circleci.com/gh/lirsacc/py-gql/tree/master)

py-gql is a [GraphQL](http://facebook.github.io/graphql/) implementation for Python.

**:construction: WIP! Do not use this in production just yet :construction:**

Installation
------------

> TODO after PyPi release

Usage & Examples
----------------

> TODO: Write some simple usage example

- You can refer to the [tests](./tests) for some simple usage examples
- Some more involved examples are available in the [examples](./examples) folder.

Goals & Status
--------------

This project was initially born as an experiment / learning project following some frustration with with [graphql-core](https://github.com/graphql-python/graphql-core/) and [Graphene](https://github.com/graphql-python/graphene/) we encountered at work.

The main goals were to:

- Get a deeper understanding of the GraphQL specification and available implementations.
- Provide an alternative to graphql-core that:
  - tracks the lastest version of the GraphQL specification
  - does not necessarily attempt to track the reference javascript implementation
  - (subjective) attempts to be a bit more usable, the ideal result would sit between Graphene and graphql-core
- Make it easier for us to build / include some extra tooling such as custom tracing, custom validation and SDL based tools.
- Maintain Python 2.7 compatibility due to work projects still running it.

**Note:** The [graphql-core-next](https://github.com/graphql-python/graphql-core-next) project is currently working on providing a more up to date alternative to graphql-core. Importantly for us it tracks the specification and includes SDL based schema creation; however it is Python 3 only for now and still closely tracks the JS implementation.

### Current status

So far every aspect of the library that is necessary for us to start using it in production has been implemented; the most notable ommission being subscribtions. For a more detailled roadmap of what remains to be done before calling this a v1, see [Issue #1](https://github.com/lirsacc/py-gql/issues/1).

- While some parts of the code / design are still very close to the graphql-js / graphql-core implementations, all the code has been re-implemented from scratch and the implementations will most likely diverge in the future.
- The test suite is quite extensive and largely based on the [graphql-js](https://github.com/graphql/graphql-js) one


Development setup
-----------------

> TODO
