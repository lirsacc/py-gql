# Changelog

## Unreleased

- (Re) add support for `copy` and `deepcopy` to `py_gql.lang.ast.Node`.
- Add `py_gql.utilities.ast_transforms.RemoveFieldAliasesVisitor`.
- Add `py_gql.utilities.ast_transforms.CamelCaseToSnakeCaseVisitor` and `py_gql.utilities.ast_transforms.SnakeCaseToCamelCaseVisitor`.

### Fixed

- Fix a bug where selection set indentation was not correct when using `ASTPrinter`.

## 0.3.2

Docs & dev update.

## 0.3.0

### Breaking Changes

- `AsyncExecutor` renamed to `AsyncIOExecutor`
- `allow_type_system` argument to `py_gql.lang.Parser` now defaults to `False`.
- `SchemaDirective` do not support defining their own definition which now has to be defined in the schema.
- `py_gql.utilities.diff_schema` has been moved to its own submodule `py_gql.utilities.diff_schema.diff_schema` (alongside related types and constants).
- `py_gql.utilities.diff_schema.diff_schema` now return instances of `SchemaChange` instead of combining enum values and formatted string in a tuple. The classes contain more context and references to the actual schema objects (Field, Argument, etc.).

### Updated

- Support passing an already parsed ast to `process_graphql_query` and its derivatives.
- `ASTSchemaPrinter` (and `Schema.to_string()`) now supports printing custom schema directives collected when using `build_schema` behind the `include_custom_directives` flag.

### Fixed

- Handle early return from `process_graphql_query` in `py_gql.graphql`.
- Make sure `process_graphql_query` calls `tracer.on_end()` on early returns.
- Fix link in the description of the `UUID` scalar type.
- Fix bug in `Executor.complete_value` which lead to incorrectly ignoring fragment when applied on types implementing an interface.

## 0.2.0

This release follow some extensive internal refactor and legwork in order to make `py_gql` easier to improve and extend moving forward.

### Most notable changes

- **Dropped Python 2 support**; the minimum supported version is now Python 3.5.
- `py_gql.build_schema` is now the preferred way to define executable GraphQL schema (instead of using the `py_gql.schema.Schema` class).
- `py_gql.graphql` now defaults to working with `asyncio`. Use `py_gql.graphql_blocking` for synchronous use cases. This should make things more obvious when implementing subscriptions. `py_gql.process_graphql_query` is still available in order to support custom executors.
- Finalised implementation of schema directives for `py_gql.build_schema`.
- Resolvers can now be assigned with the `py_gql.schema.Schema.resolver` decorator.
- Added type hints for most exposed apis, however some types are still too open and this will be improved moving forward.
- Simplify middleware and tracer implementation: middlewares do not try to be smart and users have to write them against their resolver and executor. Tracers are not based on middlewares anymore.
- Many small performance improvements.
- Returning callables to lazily resolve values has been deprecated.?
- Fixed custom scalars support during execution.
- Updated some error messages to match the reference implementation more closely.
- Implementing custom `py_gql.execution.Executor` is a bit more involved in order to simplify the implementations of the execution layer.
- `py_gql.utilities.diff_schema` added to compare schemas for compatibility.

## 0.1.0

Initial release.
