# -*- coding: utf-8 -*-
"""
Validation rules defined in `this section
<http://facebook.github.io/graphql/June2018/#sec-Validation>`_ of the
specification.

These rules are **all** used by default when calling
`~py_gql.validation.validate` and accessible together as
`~py_gql.validatin.SPECIFIED_RULES`.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple

from ..._string_utils import infer_suggestions, quoted_options_list
from ..._utils import OrderedDict, deduplicate
from ...exc import UnknownType
from ...lang import ast as _ast, print_ast
from ...lang.visitor import SkipNode
from ...schema import (
    GraphQLType,
    InterfaceType,
    NonNullType,
    ObjectType,
    UnionType,
    is_composite_type,
    is_input_type,
    is_leaf_type,
    unwrap_type,
)
from ..visitors import ValidationVisitor, VariablesCollector
from .overlapping_fields_can_be_merged import (  # noqa: F401
    OverlappingFieldsCanBeMergedChecker,
)
from .values_of_correct_type import ValuesOfCorrectTypeChecker  # noqa: F401

__all__ = (
    "ExecutableDefinitionsChecker",
    "UniqueOperationNameChecker",
    "LoneAnonymousOperationChecker",
    "SingleFieldSubscriptionsChecker",
    "KnownTypeNamesChecker",
    "FragmentsOnCompositeTypesChecker",
    "VariablesAreInputTypesChecker",
    "ScalarLeafsChecker",
    "FieldsOnCorrectTypeChecker",
    "UniqueFragmentNamesChecker",
    "KnownFragmentNamesChecker",
    "NoUnusedFragmentsChecker",
    "PossibleFragmentSpreadsChecker",
    "NoFragmentCyclesChecker",
    "UniqueVariableNamesChecker",
    "NoUndefinedVariablesChecker",
    "NoUnusedVariablesChecker",
    "KnownDirectivesChecker",
    "UniqueDirectivesPerLocationChecker",
    "KnownArgumentNamesChecker",
    "UniqueArgumentNamesChecker",
    "ValuesOfCorrectTypeChecker",
    "ProvidedRequiredArgumentsChecker",
    "VariablesInAllowedPositionChecker",
    "OverlappingFieldsCanBeMergedChecker",
    "UniqueInputFieldNamesChecker",
)


class ExecutableDefinitionsChecker(ValidationVisitor):
    """
    A GraphQL document is only valid for execution if all definitions
    are either operation or fragment definitions.

    Unnecessary if parser was run with ``allow_type_system=False``.
    """

    def enter_document(self, node):
        skip_doc = False
        for definition in node.definitions:
            if not isinstance(definition, _ast.ExecutableDefinition):
                name = (
                    "schema"
                    if isinstance(
                        definition,
                        (_ast.SchemaDefinition, _ast.SchemaExtension),
                    )
                    else definition.name.value
                )
                self.add_error(
                    "The %s definition is not executable." % name, [definition]
                )
                skip_doc = True

        if skip_doc:
            raise SkipNode()


class UniqueOperationNameChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all defined operations have
    unique names.
    """

    def __init__(self, schema, type_info):
        super(UniqueOperationNameChecker, self).__init__(schema, type_info)
        self._names = set()  # type: Set[str]

    def enter_operation_definition(self, node):
        op_name = node.name.value if node.name else node.operation
        if op_name in self._names:
            self.add_error('Duplicate operation "%s".' % op_name, [node])
            raise SkipNode()
        self._names.add(op_name)


class LoneAnonymousOperationChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if when it contains an anonymous
    operation (the query short-hand) that it contains only that one
    operation definition.
    """

    def enter_document(self, node):
        operation_definitions = [
            d
            for d in node.definitions
            if isinstance(d, _ast.OperationDefinition)
        ]

        has_anonymous = any((d.name is None for d in operation_definitions))
        if has_anonymous and len(operation_definitions) > 1:
            self.add_error(
                "The anonymous operation must be the only defined operation.",
                [node],
            )
            raise SkipNode()


class SingleFieldSubscriptionsChecker(ValidationVisitor):
    """
    A GraphQL subscription is valid only if it contains a single
    root field.
    """

    def enter_operation_definition(self, node):
        if node.operation == "subscription":
            if len(node.selection_set.selections) != 1:
                if node.name:
                    msg = (
                        'Subscription "%s" must select only one top level field.'
                        % node.name.value
                    )
                else:
                    msg = "Subscription must select only one top level field."
                self.add_error(msg, [node])


class KnownTypeNamesChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if referenced types (specifically
    variable definitions and fragment conditions) are defined by the
    type schema.
    """

    def _skip(self, _):
        raise SkipNode()

    # Ignore type system defs
    enter_object_type_definition = _skip
    enter_interface_type_definition = _skip
    enter_union_type_definition = _skip
    enter_input_object_type_definition = _skip

    def _enter_type_literal(self, node):
        try:
            self.schema.get_type_from_literal(node)
        except UnknownType as err:
            self.add_error('Unknown type "%s"' % err, [node])

    enter_named_type = _enter_type_literal
    enter_list_type = _enter_type_literal
    enter_non_null_type = _enter_type_literal


class FragmentsOnCompositeTypesChecker(ValidationVisitor):
    """
    Fragments use a type condition to determine if they apply, since
    fragments can only be spread into a composite type (object, interface, or
    union), the type condition must also be a composite type.
    """

    def enter_inline_fragment(self, node):
        if node.type_condition:
            type_ = self.schema.get_type_from_literal(node.type_condition)
            if not is_composite_type(type_):
                self.add_error(
                    'Fragment cannot condition on non composite type "%s".'
                    % type_.name,
                    [node.type_condition],
                )
                raise SkipNode()

    def enter_fragment_definition(self, node):
        type_ = self.schema.get_type_from_literal(node.type_condition)
        if not is_composite_type(type_):
            self.add_error(
                'Fragment "%s" cannot condition on non composite type "%s".'
                % (node.name.value, type_.name),
                [node.type_condition],
            )
            raise SkipNode()


class VariablesAreInputTypesChecker(ValidationVisitor):
    """
    A GraphQL operation is only valid if all the variables it defines are of
    input types (scalar, enum, or input object).
    """

    def enter_variable_definition(self, node):
        try:
            type_ = self.schema.get_type_from_literal(node.type)
        except UnknownType:
            type_ = None
        if not is_input_type(type_):
            self.add_error(
                'Variable "$%s" must be input type' % node.variable.name.value,
                [node],
            )


class ScalarLeafsChecker(ValidationVisitor):
    """
    A GraphQL document is valid only if all leaf fields (fields without
    sub selections) are of scalar or enum types.
    """

    def enter_field(self, node):
        type_ = self.type_info.type

        if is_leaf_type(unwrap_type(type_)) and node.selection_set:
            self.add_error(
                'Field "%s" must not have a selection since type "%s" has no subfields.'
                % (node.name.value, type_),
                [node],
            )

        if is_composite_type(unwrap_type(type_)) and not node.selection_set:
            self.add_error(
                'Field "%s" of type "%s" must have a selection of subfields. '
                'Did you mean "%s { ... }"?'
                % (node.name.value, type_, node.name.value),
                [node],
            )


class FieldsOnCorrectTypeChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all fields selected are defined by
    the parent type, or are an allowed meta field such as __typename.
    """

    def enter_field(self, node):
        if self.type_info.parent_type is None:
            return

        field_def = self.type_info.field
        if field_def is None:

            if isinstance(
                self.type_info.parent_type, (ObjectType, InterfaceType)
            ):
                fieldnames = [f.name for f in self.type_info.parent_type.fields]
                suggestions = infer_suggestions(node.name.value, fieldnames)
                if suggestions:
                    self.add_error(
                        'Cannot query field "%s" on type "%s". Did you mean %s?'
                        % (
                            node.name.value,
                            self.type_info.parent_type.name,
                            quoted_options_list(suggestions),
                        ),
                        [node],
                    )
                else:
                    self.add_error(
                        'Cannot query field "%s" on type "%s".'
                        % (node.name.value, self.type_info.parent_type.name),
                        [node],
                    )

            elif isinstance(self.type_info.parent_type, UnionType):
                options = quoted_options_list(
                    [t.name for t in self.type_info.parent_type.types]
                )
                self.add_error(
                    'Cannot query field "%s" on type "%s". Did you mean to use '
                    "an inline fragment on %s?"
                    % (
                        node.name.value,
                        self.type_info.parent_type.name,
                        options,
                    ),
                    [node],
                )

            else:
                self.add_error(
                    'Cannot query field "%s" on type "%s"'
                    % (node.name.value, self.type_info.parent_type.name),
                    [node],
                )


class UniqueFragmentNamesChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all defined fragments have unique
    names.
    """

    def __init__(self, schema, type_info):
        super(UniqueFragmentNamesChecker, self).__init__(schema, type_info)
        self._names = set()  # type: Set[str]

    def enter_fragment_definition(self, node):
        name = node.name.value
        if name in self._names:
            self.add_error(
                'There can only be one fragment named "%s"' % name, [node]
            )
        self._names.add(name)


class KnownFragmentNamesChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all `...Fragment` fragment spreads
    refer to fragments defined in the same document.
    """

    def __init__(self, schema, type_info):
        super(KnownFragmentNamesChecker, self).__init__(schema, type_info)

    def enter_document(self, node):
        self._fragment_names = set(
            [
                definition.name.value
                for definition in node.definitions
                if type(definition) == _ast.FragmentDefinition
            ]
        )

    def enter_fragment_spread(self, node):
        name = node.name.value
        if name not in self._fragment_names:
            self.add_error('Unknown fragment "%s"' % name, [node])


class NoUnusedFragmentsChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all fragment definitions are spread
    within operations, or spread within other fragments spread within
    operations.
    """

    def __init__(self, schema, type_info):
        super(NoUnusedFragmentsChecker, self).__init__(schema, type_info)
        self._fragments = set()  # type: Set[str]
        self._used_fragments = set()  # type: Set[str]

    def enter_fragment_definition(self, node):
        self._fragments.add(node.name.value)

    def enter_fragment_spread(self, node):
        self._used_fragments.add(node.name.value)

    def leave_document(self, _node):
        unused = self._fragments - self._used_fragments
        if unused:
            quoted = ", ".join('"%s"' % x for x in sorted(unused))
            self.add_error("Unused fragment(s) %s" % quoted)


class PossibleFragmentSpreadsChecker(ValidationVisitor):
    """
    A fragment spread is only valid if the type condition could ever
    possibly be true: if there is a non-empty intersection of the possible
    parent types, and possible types which pass the type condition.
    """

    def __init__(self, schema, type_info):
        super(PossibleFragmentSpreadsChecker, self).__init__(schema, type_info)
        self._fragment_types = dict()  # type: Dict[str, GraphQLType]

    def enter_document(self, node):
        self._fragment_types.update(
            {
                definition.name.value: self.schema.get_type_from_literal(
                    definition.type_condition
                )
                for definition in node.definitions
                if type(definition) == _ast.FragmentDefinition
            }
        )

    def enter_fragment_spread(self, node):
        name = node.name.value
        frag_type = self._fragment_types.get(name, None)
        parent_type = self.type_info.type

        if (
            is_composite_type(frag_type)
            and is_composite_type(parent_type)
            and not self.schema.types_overlap(frag_type, parent_type)
        ):
            self.add_error(
                'Fragment "%s" cannot be spread here as types "%s" and "%s"'
                " do not overlap." % (name, frag_type, parent_type),
                [node],
            )
            raise SkipNode()

    def enter_inline_fragment(self, node):
        type_ = self.type_info.type
        parent_type = self.type_info.parent_type

        if (
            is_composite_type(type_)
            and is_composite_type(parent_type)
            and not self.schema.types_overlap(type_, parent_type)
        ):
            self.add_error(
                'Inline fragment cannot be spread here as types "%s" and "%s"'
                " do not overlap." % (type_, parent_type),
                [node],
            )
            raise SkipNode()


class NoFragmentCyclesChecker(ValidationVisitor):
    """
    A GraphQL Document is only valid if fragment definitions are not cyclic.
    """

    def __init__(self, schema, type_info):
        super(NoFragmentCyclesChecker, self).__init__(schema, type_info)
        self._spreads = OrderedDict()  # type: Dict[str, List[str]]
        self._current = None

    def enter_fragment_definition(self, node):
        name = node.name.value
        self._current = name
        self._spreads[name] = []

    def leave_fragment_definition(self, _node):
        self._current = None

    def enter_fragment_spread(self, node):
        name = node.name.value

        if self._current is not None:
            if self._current and name == self._current:
                self.add_error(
                    'Cannot spread fragment "%s" withing itself' % name, [node]
                )
                raise SkipNode()

            if name not in self._spreads[self._current]:
                self._spreads[self._current].append(name)

    def leave_document(self, node):
        def _search(outer, acc=None, path=None):
            acc, path = acc or dict(), path or []

            if outer not in self._spreads:
                return acc

            for inner in self._spreads[outer]:
                # The ref implementation will report multiple distinct cycles
                # for one fragment. This line and the fact that we keep one
                # path per fragment make it so that we only report one.
                if inner in acc:
                    break
                acc[inner] = path
                _search(inner, acc, path + [inner])

            return acc

        flat_spreads = [(outer, _search(outer)) for outer in self._spreads]
        cyclic = set()

        for outer, inner_spreads in flat_spreads:
            if outer in inner_spreads:
                cyclic.add(outer)
                path = inner_spreads[outer]

                # Make sure we do not report redundant cycles, i.e. if A > B
                # has been identified, A > B > A is redundant and will not be
                # reported.
                if path[-1] in cyclic:
                    continue

                self.add_error(
                    'Cannot spread fragment "%s" withing itself (via: %s)'
                    % (outer, " > ".join(path)),
                    [node],
                )


class UniqueVariableNamesChecker(ValidationVisitor):
    """
    A GraphQL operation is only valid if all its variables are uniquely
    named.
    """

    def enter_operation_definition(self, _node):
        self._variables = set()  # type: Set[str]

    def leave_operation_definition(self, _node):
        self._variables = None

    def enter_variable_definition(self, node):
        name = node.variable.name.value
        if name in self._variables:
            self.add_error('Duplicate variable "$%s"' % name, [node])
        self._variables.add(name)


class NoUndefinedVariablesChecker(VariablesCollector):
    """
    A GraphQL operation is only valid if all variables encountered, both
    directly and via fragment spreads, are defined by that operation.
    """

    def leave_document(self, node):
        super(NoUndefinedVariablesChecker, self).leave_document(node)

        for op, fragments in self._op_fragments.items():
            defined = self._op_defined_variables[op]
            for fragment in deduplicate(fragments):
                fragment_variables = self._fragment_variables[fragment].items()
                for var, (node, _, _) in fragment_variables:
                    if var not in defined:
                        self.add_error(
                            'Variable "$%s" from fragment "%s" is not defined '
                            "on %s operation"
                            % (
                                var,
                                fragment,
                                '"%s"' % op if op != "" else "anonymous",
                            ),
                            [node],
                        )

        for op, variables in self._op_variables.items():
            defined = self._op_defined_variables[op]
            for var, (node, _, _) in variables.items():
                if var not in defined:
                    self.add_error(
                        'Variable "$%s" is not defined on %s operation'
                        % (var, '"%s"' % op if op != "" else "anonymous"),
                        [node],
                    )


class NoUnusedVariablesChecker(VariablesCollector):
    """
    A GraphQL operation is only valid if all variables defined by an
    operation are used, either directly or within a spread fragment.
    """

    def leave_document(self, node):
        super(NoUnusedVariablesChecker, self).leave_document(node)

        used_variables = defaultdict(set)  # type: Dict[str, Set[str]]

        for op, fragments in self._op_fragments.items():
            for fragment in deduplicate(fragments):
                for var in self._fragment_variables[fragment].keys():
                    used_variables[op].add(var)

        for op, variables in self._op_variables.items():
            for var in variables.keys():
                used_variables[op].add(var)

        for op, defined in self._op_defined_variables.items():
            used = used_variables[op]
            for var, node in defined.items():
                if var not in used:
                    self.add_error('Unused variable "$%s"' % var, [node])


class KnownDirectivesChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all `@directives` are known by the
    schema and legally positioned.
    """

    def __init__(self, schema, type_info):
        super(KnownDirectivesChecker, self).__init__(schema, type_info)
        self._ancestors = []  # type: List[_ast.Node]

    def _enter_ancestor(self, node):
        self._ancestors.append(node)

    def _leave_ancestor(self, _node):
        self._ancestors.pop()

    enter_operation_definition = _enter_ancestor
    leave_operation_definition = _leave_ancestor
    enter_field = _enter_ancestor
    leave_field = _leave_ancestor
    enter_field = _enter_ancestor
    leave_field = _leave_ancestor
    enter_fragment_spread = _enter_ancestor
    leave_fragment_spread = _leave_ancestor
    enter_inline_fragment = _enter_ancestor
    leave_inline_fragment = _leave_ancestor
    enter_fragment_definition = _enter_ancestor
    leave_fragment_definition = _leave_ancestor
    enter_schema_definition = _enter_ancestor
    leave_schema_definition = _leave_ancestor
    enter_schema_extension = _enter_ancestor
    leave_schema_extension = _leave_ancestor
    enter_scalar_type_definition = _enter_ancestor
    leave_scalar_type_definition = _leave_ancestor
    enter_scalar_type_extension = _enter_ancestor
    leave_scalar_type_extension = _leave_ancestor
    enter_object_type_definition = _enter_ancestor
    leave_object_type_definition = _leave_ancestor
    enter_object_type_extension = _enter_ancestor
    leave_object_type_extension = _leave_ancestor
    enter_field_definition = _enter_ancestor
    leave_field_definition = _leave_ancestor
    enter_interface_type_definition = _enter_ancestor
    leave_interface_type_definition = _leave_ancestor
    enter_interface_type_extension = _enter_ancestor
    leave_interface_type_extension = _leave_ancestor
    enter_union_type_definition = _enter_ancestor
    leave_union_type_definition = _leave_ancestor
    enter_union_type_extension = _enter_ancestor
    leave_union_type_extension = _leave_ancestor
    enter_enum_type_definition = _enter_ancestor
    leave_enum_type_definition = _leave_ancestor
    enter_enum_type_extension = _enter_ancestor
    leave_enum_type_extension = _leave_ancestor
    enter_enum_value_definition = _enter_ancestor
    leave_enum_value_definition = _leave_ancestor
    enter_input_object_type_definition = _enter_ancestor
    leave_input_object_type_definition = _leave_ancestor
    enter_input_object_type_extension = _enter_ancestor
    leave_input_object_type_extension = _leave_ancestor
    enter_input_value_definition = _enter_ancestor
    leave_input_value_definition = _leave_ancestor

    def _current_location(self):
        ancestor = self._ancestors[-1]
        kind = type(ancestor)
        if kind is _ast.OperationDefinition:
            return {
                "query": "QUERY",
                "mutation": "MUTATION",
                "subscription": "SUBSCRIPTION",
            }.get(ancestor.operation, "QUERY")

        if kind is _ast.InputValueDefinition:
            parent = self._ancestors[-2]
            return (
                "INPUT_FIELD_DEFINITION"
                if type(parent) is _ast.InputObjectTypeDefinition
                else "ARGUMENT_DEFINITION"
            )

        return {
            _ast.Field: "FIELD",
            _ast.FragmentSpread: "FRAGMENT_SPREAD",
            _ast.InlineFragment: "INLINE_FRAGMENT",
            _ast.FragmentDefinition: "FRAGMENT_DEFINITION",
            _ast.SchemaDefinition: "SCHEMA",
            _ast.SchemaExtension: "SCHEMA",
            _ast.ScalarTypeDefinition: "SCALAR",
            _ast.ScalarTypeExtension: "SCALAR",
            _ast.ObjectTypeDefinition: "OBJECT",
            _ast.ObjectTypeExtension: "OBJECT",
            _ast.FieldDefinition: "FIELD_DEFINITION",
            _ast.InterfaceTypeDefinition: "INTERFACE",
            _ast.InterfaceTypeExtension: "INTERFACE",
            _ast.UnionTypeDefinition: "UNION",
            _ast.UnionTypeExtension: "UNION",
            _ast.EnumTypeDefinition: "ENUM",
            _ast.EnumTypeExtension: "ENUM",
            _ast.EnumValueDefinition: "ENUM_VALUE",
            _ast.InputObjectTypeDefinition: "INPUT_OBJECT",
            _ast.InputObjectTypeExtension: "INPUT_OBJECT",
        }[kind]

    def enter_directive(self, node):
        name = node.name.value
        schema_directive = self.schema.directives.get(name)
        if schema_directive is None:
            self.add_error('Unknown directive "%s".' % name, [node])
        else:
            location = self._current_location()
            if location not in schema_directive.locations:
                self.add_error(
                    'Directive "%s" may not be used on %s.' % (name, location),
                    [node],
                )


class UniqueDirectivesPerLocationChecker(ValidationVisitor):
    """
    A GraphQL document is only valid if all directives at a given location
    are uniquely named.
    """

    def _validate_unique_directive_names(self, node):
        seen = set()  # type: Set[str]
        for directive in node.directives:
            name = directive.name.value
            if name in seen:
                self.add_error('Duplicate directive "@%s"' % name, [directive])
            seen.add(name)

    enter_operation_definition = _validate_unique_directive_names
    enter_field = _validate_unique_directive_names
    enter_field = _validate_unique_directive_names
    enter_fragment_spread = _validate_unique_directive_names
    enter_inline_fragment = _validate_unique_directive_names
    enter_fragment_definition = _validate_unique_directive_names


class KnownArgumentNamesChecker(ValidationVisitor):
    """
    A GraphQL field / directive is only valid if all supplied arguments
    are defined by that field / directive.
    """

    def enter_field(self, node):
        field_def = self.type_info.field
        if field_def is not None:
            known = set((a.name for a in field_def.arguments))
            for arg in node.arguments:
                name = arg.name.value
                if name not in known:
                    suggestions = list(infer_suggestions(name, known))
                    if not suggestions:
                        self.add_error(
                            'Unknown argument "%s" on field "%s" of type "%s".'
                            % (
                                name,
                                field_def.name,
                                self.type_info.parent_type,
                            ),
                            [arg],
                        )
                    else:
                        self.add_error(
                            'Unknown argument "%s" on field "%s" of type "%s". '
                            "Did you mean %s?"
                            % (
                                name,
                                field_def.name,
                                self.type_info.parent_type,
                                quoted_options_list(suggestions),
                            ),
                            [arg],
                        )

    def enter_directive(self, node):
        directive_def = self.type_info.directive
        if directive_def is not None:
            known = set((a.name for a in directive_def.arguments))
            for arg in node.arguments:
                name = arg.name.value
                if name not in known:
                    suggestions = infer_suggestions(name, known)
                    if not suggestions:
                        self.add_error(
                            'Unknown argument "%s" on directive "@%s".'
                            % (name, directive_def.name),
                            [arg],
                        )
                    else:
                        self.add_error(
                            'Unknown argument "%s" on directive "@%s". Did you mean %s?'
                            % (
                                name,
                                directive_def.name,
                                quoted_options_list(suggestions),
                            ),
                            [arg],
                        )


class UniqueArgumentNamesChecker(ValidationVisitor):
    """
    A GraphQL field or directive is only valid if all supplied arguments
    are uniquely named.
    """

    def _check_duplicate_args(self, node):
        argnames = set()  # type: Set[str]
        for arg in node.arguments:
            name = arg.name.value
            if name in argnames:
                self.add_error('Duplicate argument "%s"' % name, [arg])
            argnames.add(name)

    enter_field = _check_duplicate_args
    enter_directive = _check_duplicate_args


class ProvidedRequiredArgumentsChecker(ValidationVisitor):
    """
    A field or directive is only valid if all required (non-null without a
    default value) ) field arguments have been provided.
    """

    def _missing_args(self, arg_defs, node):
        node_args = set((arg.name.value for arg in node.arguments))
        for arg in arg_defs:
            if arg.required and (arg.name not in node_args):
                yield arg

    # Validate on leave to allow for deeper errors to appear first.
    def leave_field(self, node):
        field_def = self.type_info.field
        if field_def:
            for arg in self._missing_args(field_def.arguments, node):
                self.add_error(
                    'Field "%s" argument "%s" of type %s is required but '
                    "not provided" % (field_def.name, arg.name, arg.type),
                    [node],
                )

    # Validate on leave to allow for deeper errors to appear first.
    def leave_directive(self, node):
        directive_def = self.type_info.directive
        if directive_def:
            for arg in self._missing_args(directive_def.arguments, node):
                self.add_error(
                    'Directive "@%s" argument "%s" of type %s is required but '
                    "not provided" % (directive_def.name, arg.name, arg.type),
                    [node],
                )


class VariablesInAllowedPositionChecker(VariablesCollector):
    """
    Variables passed to field arguments conform to type """

    def iter_op_variables(self, op):
        for usage in self._op_variables[op].items():
            yield usage
        for fragment in self._op_fragments[op]:
            frament_vars = self._fragment_variables[fragment].items()
            for usage in frament_vars:
                yield usage

    def leave_document(self, node):
        super(VariablesInAllowedPositionChecker, self).leave_document(node)

        for op, vardefs in self._op_defined_variables.items():

            for (varname, usage) in self.iter_op_variables(op):
                varnode, input_type, input_value_def = usage
                vardef = vardefs.get(varname)
                if vardef and input_type:

                    try:
                        var_type = self.schema.get_type_from_literal(
                            vardef.type
                        )
                    except UnknownType:
                        continue

                    var_default = vardef.default_value

                    if isinstance(input_type, NonNullType) and not isinstance(
                        var_type, NonNullType
                    ):
                        non_null_var_default = (
                            var_default is not None
                            and type(var_default) != _ast.NullValue
                        )
                        location_default = (
                            input_value_def is not None
                            and input_value_def.has_default_value
                        )
                        if (
                            not non_null_var_default and not location_default
                        ) or not self.schema.is_subtype(
                            var_type, input_type.type
                        ):
                            self.add_error(
                                'Variable "$%s" of type %s used in position '
                                "expecting type %s"
                                % (varname, print_ast(vardef.type), input_type),
                                [varnode],
                            )
                    else:
                        if not self.schema.is_subtype(var_type, input_type):
                            self.add_error(
                                'Variable "$%s" of type %s used in position '
                                "expecting type %s"
                                % (varname, print_ast(vardef.type), input_type),
                                [varnode],
                            )


class UniqueInputFieldNamesChecker(ValidationVisitor):
    """
    A GraphQL input object value is only valid if all supplied fields are
    uniquely named.
    """

    def __init__(self, schema, type_info):
        super(UniqueInputFieldNamesChecker, self).__init__(schema, type_info)
        self._stack = []  # type: List[Tuple[_ast.ObjectValue, Set[str]]]

    def enter_object_value(self, node):
        self._stack.append((node, set()))

    def leave_object_value(self, _node):
        self._stack.pop()

    def enter_object_field(self, node):
        fieldname = node.name.value
        _, names = self._stack[-1]
        if fieldname in names:
            self.add_error(
                "There can be only one input field named %s." % fieldname,
                [node],
            )
        names.add(fieldname)
