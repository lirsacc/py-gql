Changelog
=========

Unreleased
----------

[0.5.0](https://github.com/lirsacc/py-gql/releases/tag/0.5.0) - 2020-02-05
--------------------------------------------------------------------------

### Added

- Added `py_gql.schema.transforms` and some useful transformations:

  - `py_gql.utilities.VisibilitySchemaTransform` to dynamically modify schema entities available to a given query.
  - `py_gql.utilities.CamelCaseSchemaTransform` to convert between conventions.

- `py_gql.schema.Argument` and `py_gql.schema.InputField` now inherit from the `py_gql.schema.InputValue` base class. This matches the common language used in the spec and simplifies some internal type handling.
- Add a custom `python_name` attribute for some schema elements:

  - `py_gql.schema.Argument`: when arguments are coerced and passed to a resolver the `python_name` value will be used instead of the exposed argument name.
  - `py_gql.schema.InputField`: the resulting object will use `python_name` as a key instead of the exposed field name.
  - `py_gql.schema.Field`: The default resolver will use `python_name` instead of the exposed name when looking the key or attribute in the root object.

- Added `ResolveInfo.get_directive_arguments`
- Added `ResolveInfo.selected_fields` and `utilities.selected_fields`.

- Support directives on variable definitions: this adds language support for directives on variable definitions following [graphql/graphql-spec#510](https://github.com/graphql/graphql-spec/pull/510). This is **only** language support so servers don't choke when receiving queries using this feature.

- Added `py_gql.utilities.MaxDepthValidationRule`.

### Fixed

- Introducing `pyproject.toml` broke Cython integration through build isolation. The `build-system` block has been dropped for now and cython support hidden behind the `PY_GQL_USE_CYTHON` env variable.

- Support for safely removing types from `Schema` instances:

  - Returning `None` from `SchemaVisitor` methods will now signal that the type should be removed.
  - `fix_type_references` will remove forward references from types that have been removed from the schema (e.g. field and directive arguments).

- `fix_type_references` now correctly updates the `Schema.(query|mutation|subscription)_type` attributes.

### Breaking Changes & Deprecations

- `validate_ast` now takes callables with the signature `Callable[[Schema, _ast.Document, Optional[Dict[str, Any]]], Iterable[ValidationError]]` as input for custom validation. This makes it simpler to define custom validation without having to care about the `ValidationVisitor` implementation. To use custom visitor classes as before, `default_validator` can be wrapped (`validator = lambda s, d, v: default_validator(s, d, v, validators=...)`).

- `Instrumentation` has been refactored:

  - `instrument_*` type hooks have been renamed as they are better served by consumers wrapping values at call sites.
  - `on_*` type hooks have been split between `on_*_start` and `on_*_end` hooks to avoid having to return lambdas.

- Runtime specific concepts have been extracted from `Executor` into a separate `Runtime` abstract class which is now passed in on execution (instead of the executor class). This was done to separate the resolver execution layer (which library consumer may care about) and the graphql query execution layer (which libreary consumers shouldn't care about) which were implemented in the `Executor` class. The main changes are:

  - `Executor` should not be implemented moving forward, use `Runtime` instead.
  - The specific methods haven't changed (to make it easy to migrate, they might be revisited later) but they have become actual method instead of staticmethods.
  - The `Executor.supports_subscriptions` attribute has been replaced by the `SubscriptionRuntime` subclass.

- `SchemaVisitor.(on_field_definition|on_argument_definition|on_input_field_definition)` have become `SchemaVisitor.(on_field|on_argument|on_input_field)` to maintain consistency with other methods.
- Do not expose `GraphQLExtension` on `py_gql`.

- `py_gql.lang.visitors.ParallelVisitor` -> `py_gql.lang.visitors.ChainedVisitor`

- The `py_gql.utilities.diff_schema` module has been moved to `py_gql.schema.differ`.

- `TypeInfoVisitor` and `VariablesCollector` are now kept internal to `py_gql.validation.visitors`.

- Fix Lexer greediness. Some edge cases were not handled as expected. This commit adds test cases from the 2 RFCs clarifying the expected behaviour ([graphql/graphql-spec#601](https://github.com/graphql/graphql-spec/pull/601), [graphql/graphql-spec#599](https://github.com/graphql/graphql-spec/pull/599)) and updates the Lexer to match. This is _technically_ a breaking change but most cases were likely to lead to validation errors (e.g. "0xF1" being parsed as [0, xF1] when expecting a list of integers).

[0.4.0](https://github.com/lirsacc/py-gql/releases/tag/0.4.0) - 2019-10-10
--------------------------------------------------------------------------

### Breaking Changes & Deprecations

- `py_gql.builders` has been moved to `py_gql.sdl` and `build_schema_ignoring_extensions` has been removed.
- `Tracer` has been replaced by the more general concept of `Instrumentation` which is now backing `ApolloTracer`.
- `Directive` is not a subclass of `GraphQLType` anymore.
- It is no longer possible to override specified directives and types when creating a schema.
- Dropped `is_abstract_type`, `is_composite_type` and `is_leaf_type`: use instance checks against `GraphQLAbstractType`, `GraphQLCompositeType`, and `GraphQLLeafType` directly instead.
- Dropped `ObjectType.is_type_of` option for concrete type resolution, use `(UnionType|InterfaceType).resolve_type` instead.

### Added

- Add support for `copy` and `deepcopy` to `py_gql.lang.ast.Node`.
- `py_gql.lang.Visitor` now supports modifying the nodes inline; this supports the implementation of some common AST transformers.
- Add `py_gql.utilities.ast_transforms.RemoveFieldAliasesVisitor` to canonicalise queries from a server's perspective.
- Add `py_gql.utilities.ast_transforms.CamelCaseToSnakeCaseVisitor` and `py_gql.utilities.ast_transforms.SnakeCaseToCamelCaseVisitor` to support interacting with common convetions in the wider GraphQL ecosystem.
- Extended the tracer concept into `Instrumentation` which supports overriding runtime values as well as observing execution stages.
- `(UnionType|InterfaceType).resolve_type` now receives the current resolution data value and `ResolveInfo`.
- Basic subscription support has been added through `py_gql.execution.subscribe`. It's not well documented yet is subject to change. For now refer to the _starlette-ws-subsriptions_ example.

### Fixed

- Fix a bug where selection set indentation was not correct when using `ASTPrinter`.
- Do not import `typing.Deque` outside of type checking context to ensure compatibility with versions `<= 3.5.3`.

[0.3.2](https://github.com/lirsacc/py-gql/releases/tag/0.3.2) - 2019-05-01
--------------------------------------------------------------------------

Docs & dev update.

[0.3.0](https://github.com/lirsacc/py-gql/releases/tag/0.3.0) - 2019-05-01
--------------------------------------------------------------------------

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

[0.2.0](https://github.com/lirsacc/py-gql/releases/tag/0.2.0) - 2019-04-18
--------------------------------------------------------------------------

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

0.1.0
-----

Initial release.
