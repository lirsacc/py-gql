Changelog
=========

Unreleased
----------

py_gql has been refactored significantly for this release.

Notable changes
~~~~~~~~~~~~~~~

- Dropped Python 2 support.
- :func:`py_gql.build_schema` is now the preferred way to define executable
  GraphQL schema (instead of using the :class:`py_gql.schema.Schema` class).
- Fully implemented schema directives for :func:`py_gql.build_schema`.
- Resolver can now be assigned with the :meth:`~py_gql.schema.Schema.resolver`
  decorator.
- Added type hints for most exposed apis, however some types are still too open.
- :func:`py_gql.graphql` now defaults to working with :py:mod:`asyncio`. Use
  :func:`py_gql.graphql_blocking` for synchronous use cases. This should make
  things more obvious concerning implementing subscriptions
- Dropped middleware support and tracers. This is temporary and should come back
  at some point once we've found a nicer interface for them.
- Multiple internal performance improvements.
- Returning callables to lazily resolve values has been deprecated.
- Fixed custom scalars support during execution.
- Updated some error messages to match the reference implementation more closely.
- Implementing custom :class:`py_gql.execution.Executor` is a bit more involved
  in order to simplify the internal implementations.

0.1.0
-----

Initial release.
