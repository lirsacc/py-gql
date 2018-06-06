# -*- coding: utf-8 -*-
""" Validation rules from the spec.
"""

from ..._utils import deduplicate, DefaultOrderedDict, OrderedDict
from ...exc import UnknownType
from ...lang import ast as _ast, print_ast
from ...lang.visitor import SkipNode
from ...schema import (
    is_composite_type, is_input_type, is_leaf_type, unwrap_type, NonNullType)
from ..visitors import ValidationVisitor, VariablesCollector
from .values_of_correct_type import ValuesOfCorrectTypeChecker  # noqa: F401
from .overlapping_fields_can_be_merged import (  # noqa: F401
    OverlappingFieldsCanBeMergedChecker)


class ExecutableDefinitionsChecker(ValidationVisitor):
    """ A GraphQL document is only valid for execution if all definitions
    are either operation or fragment definitions.

    Unnecessary if parser was run with ``allow_type_system=False``.
    """
    def enter_document(self, node):
        for definition in node.definitions:
            if not isinstance(definition, _ast.ExecutableDefinition):
                self.add_error(
                    'Definition "%s" is not executable'
                    % ('schema'
                       if isinstance(definition, _ast.SchemaDefinition)
                       else definition.name.value),
                    definition
                )
                raise SkipNode()


class UniqueOperationNameChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all defined operations have
    unique names. """
    def __init__(self, *args, **kwargs):
        super(UniqueOperationNameChecker, self).__init__(*args, **kwargs)
        self.names = set()

    def enter_operation_definition(self, node):
        op_name = node.name.value if node.name else node.operation
        if op_name in self.names:
            self.add_error('Duplicate operation "%s".' % op_name, node)
            raise SkipNode()
        self.names.add(op_name)


class LoneAnonymousOperationChecker(ValidationVisitor):
    """ A GraphQL document is only valid if when it contains an anonymous
    operation (the query short-hand) that it contains only that one
    operation definition. """
    def enter_document(self, node):
        operation_definitions = [
            d
            for d in node.definitions
            if isinstance(d, _ast.OperationDefinition)
        ]

        has_anonymous = any((d.name is None for d in operation_definitions))
        if has_anonymous and len(operation_definitions) > 1:
            self.add_error(
                'The anonymous operation must be the only defined operation.',
                node
            )
            raise SkipNode()


class SingleFieldSubscriptionsChecker(ValidationVisitor):
    """ A GraphQL subscription is valid only if it contains a single
    root field. """
    def enter_operation_definition(self, node):
        if node.operation == 'subscription':
            if len(node.selection_set.selections) != 1:
                self.add_error(
                    'Subscription "%s" must select only one top level field.'
                    % (node.name.value if node.name else ''),
                    node
                )


class KnownTypeNamesChecker(ValidationVisitor):
    """ A GraphQL document is only valid if referenced types (specifically
    variable definitions and fragment conditions) are defined by the
    type schema. """

    def _skip(self, _):
        raise SkipNode()

    # Ignore type system defs
    enter_object_type_definition = _skip
    enter_interface_type_definition = _skip
    enter_union_type_definition = _skip
    enter_input_object_type_definition = _skip

    def enter_named_type(self, node):
        try:
            print(print_ast(node))
            self.schema.get_type_from_literal(node)
        except UnknownType as err:
            # [TODO] Implement suggestion list?
            print('error')
            self.add_error('Unknown type "%s"' % err.args[0], node)


class FragmentsOnCompositeTypesChecker(ValidationVisitor):
    """ Fragments use a type condition to determine if they apply, since
    fragments can only be spread into a composite type (object, interface, or
    union), the type condition must also be a composite type. """
    def enter_inline_fragment(self, node):
        if node.type_condition:
            typ = self.schema.get_type_from_literal(node.type_condition)
            if not is_composite_type(typ):
                self.add_error(
                    'Fragment type condition cannot be on non-composite '
                    'type "%s"' % (typ.name), node)
                raise SkipNode()

    def enter_fragment_definition(self, node):
        typ = self.schema.get_type_from_literal(node.type_condition)
        if not is_composite_type(typ):
            self.add_error(
                'Fragment "%s" type condition cannot be on non-composite '
                'type "%s"' % (node.name.value, typ.name), node)
            raise SkipNode()


class VariablesAreInputTypesChecker(ValidationVisitor):
    """ A GraphQL operation is only valid if all the variables it defines are of
    input types (scalar, enum, or input object). """
    def enter_variable_definition(self, node):
        try:
            typ = self.schema.get_type_from_literal(node.type)
        except UnknownType:
            typ = None
        if not is_input_type(typ):
            self.add_error(
                'Variable "$%s" must be input type' % node.variable.name.value,
                node)


class ScalarLeafsChecker(ValidationVisitor):
    """ A GraphQL document is valid only if all leaf fields (fields without
    sub selections) are of scalar or enum types. """
    def enter_field(self, node):
        typ = self.type_info.type

        if is_leaf_type(unwrap_type(typ)) and node.selection_set:
            self.add_error(
                'Field "%s" cannot have a selection as type "%s" has no '
                'fields' % (node.name.value, typ), node)

        if is_composite_type(unwrap_type(typ)) and not node.selection_set:
            self.add_error(
                'Field "%s" of type "%s" must have a subselection'
                % (node.name.value, typ), node)


class FieldsOnCorrectTypeChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all fields selected are defined by
    the parent type, or are an allowed meta field such as __typename. """
    def enter_field(self, node):
        if self.type_info.parent_type is None:
            return

        field_def = self.type_info.field
        if field_def is None:
            # [TODO] Implement suggestion list?
            self.add_error(
                'Cannot query field "%s" on type "%r"'
                % (node.name.value, self.type_info.parent_type), node)


class UniqueFragmentNamesChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all defined fragments have unique
    names. """
    def __init__(self, *args, **kwargs):
        super(UniqueFragmentNamesChecker, self).__init__(*args, **kwargs)
        self._names = set()

    def enter_fragment_definition(self, node):
        name = node.name.value
        if name in self._names:
            self.add_error(
                'There can only be one fragment named "%s"' % name,
                node
            )
        self._names.add(name)


class KnownFragmentNamesChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all `...Fragment` fragment spreads
    refer to fragments defined in the same document. """
    def __init__(self, *args, **kwargs):
        super(KnownFragmentNamesChecker, self).__init__(*args, **kwargs)

    def enter_document(self, node):
        self._fragment_names = set([
            definition.name.value
            for definition in node.definitions
            if type(definition) == _ast.FragmentDefinition
        ])

    def enter_fragment_spread(self, node):
        name = node.name.value
        if name not in self._fragment_names:
            self.add_error('Unknown fragment "%s"' % name)


class NoUnusedFragmentsChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all fragment definitions are spread
    within operations, or spread within other fragments spread within
    operations. """
    def __init__(self, *args, **kwargs):
        super(NoUnusedFragmentsChecker, self).__init__(*args, **kwargs)
        self._fragments = set()
        self._used_fragments = set()

    def enter_fragment_definition(self, node):
        self._fragments.add(node.name.value)

    def enter_fragment_spread(self, node):
        self._used_fragments.add(node.name.value)

    def leave_document(self, node):
        unused = self._fragments - self._used_fragments
        if unused:
            self.add_error(
                'Unused fragment(s) %s'
                % ', '.join(['"%s"' % n for n in sorted(unused)]))


class PossibleFragmentSpreadsChecker(ValidationVisitor):
    """ A fragment spread is only valid if the type condition could ever
    possibly be true: if there is a non-empty intersection of the possible
    parent types, and possible types which pass the type condition. """
    def __init__(self, *args, **kwargs):
        super(PossibleFragmentSpreadsChecker, self).__init__(*args, **kwargs)
        self._fragment_types = dict()

    def enter_document(self, node):
        self._fragment_types.update({
            definition.name.value: self.schema.get_type_from_literal(
                definition.type_condition)
            for definition in node.definitions
            if type(definition) == _ast.FragmentDefinition
        })

    def enter_fragment_spread(self, node):
        name = node.name.value
        frag_type = self._fragment_types.get(name, None)
        parent_type = self.type_info.type

        if (is_composite_type(frag_type) and
                is_composite_type(parent_type) and
                not self.schema.overlap(frag_type, parent_type)):
            self.add_error(
                'Fragment "%s" cannot be spread here as types "%s" and "%s"'
                ' do not overlap.' % (name, frag_type, parent_type), node)
            raise SkipNode()

    def enter_inline_fragment(self, node):
        typ = self.type_info.type
        parent_type = self.type_info.parent_type

        if (is_composite_type(typ) and
                is_composite_type(parent_type) and
                not self.schema.overlap(typ, parent_type)):
            self.add_error(
                'Inline fragment cannot be spread here as types "%s" and "%s"'
                ' do not overlap.' % (typ, parent_type), node)
            raise SkipNode()


class NoFragmentCyclesChecker(ValidationVisitor):
    """ A GraphQL Document is only valid if fragment definitions are not cyclic.
    """
    def __init__(self, *args, **kwargs):
        super(NoFragmentCyclesChecker, self).__init__(*args, **kwargs)
        self._spreads = OrderedDict()
        self._current = None

    def enter_fragment_definition(self, node):
        name = node.name.value
        self._current = name
        self._spreads[name] = []

    def leave_fragment_definition(self, node):
        self._current = None

    def enter_fragment_spread(self, node):
        name = node.name.value

        if self._current is not None:
            if self._current and name == self._current:
                self.add_error(
                    'Cannot spread fragment "%s" withing itself' % name, node)
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
                    % (outer, ' > '.join(path)), node)


class UniqueVariableNamesChecker(ValidationVisitor):
    """ A GraphQL operation is only valid if all its variables are uniquely
    named. """
    def enter_operation_definition(self, node):
        self._variables = set()

    def leave_operation_definition(self, node):
        self._variables = None

    def enter_variable_definition(self, node):
        name = node.variable.name.value
        if name in self._variables:
            self.add_error('Duplicate variable "$%s"' % name, node)
        self._variables.add(name)


class NoUndefinedVariablesChecker(VariablesCollector):
    """ A GraphQL operation is only valid if all variables encountered, both
    directly and via fragment spreads, are defined by that operation. """
    def leave_document(self, node):
        self._flatten_fragments()

        for op, fragments in self._op_fragments.items():
            defined = self._op_defined_variables[op]
            for fragment in deduplicate(fragments):
                fragment_variables = self._fragment_variables[fragment].items()
                for var, (node, _) in fragment_variables:
                    if var not in defined:
                        self.add_error(
                            'Variable "$%s" from fragment "%s" is not defined '
                            'on %s operation'
                            % (var,
                               fragment,
                               '"%s"' % op if op != '' else 'anonymous'),
                            node)

        for op, variables in self._op_variables.items():
            defined = self._op_defined_variables[op]
            for var, (node, _) in variables.items():
                if var not in defined:
                    self.add_error(
                        'Variable "$%s" is not defined on %s operation'
                        % (var, '"%s"' % op if op != '' else 'anonymous'), node)


class NoUnusedVariablesChecker(VariablesCollector):
    """ A GraphQL operation is only valid if all variables defined by an
    operation are used, either directly or within a spread fragment. """
    def leave_document(self, node):
        self._flatten_fragments()
        used_variables = DefaultOrderedDict(set)

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
                    self.add_error('Unused variable "$%s"' % var, node)


class KnownDirectivesChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all `@directives` are known by the
    schema and legally positioned. """

    def __init__(self, *args, **kwargs):
        super(KnownDirectivesChecker, self).__init__(*args, **kwargs)
        self._ancestors = []

    def _enter_ancestor(self, node):
        self._ancestors.append(node)

    def _leave_ancestor(self, node):
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
                'query': 'QUERY',
                'mutation': 'MUTATION',
                'subscription': 'SUBSCRIPTION',
            }.get(ancestor.operation, 'QUERY')

        if kind is _ast.InputValueDefinition:
            parent = self._ancestors[-2]
            return ('INPUT_FIELD_DEFINITION'
                    if type(parent) is _ast.InputObjectTypeDefinition
                    else 'ARGUMENT_DEFINITION')

        return {
            _ast.Field: 'FIELD',
            _ast.FragmentSpread: 'FRAGMENT_SPREAD',
            _ast.InlineFragment: 'INLINE_FRAGMENT',
            _ast.FragmentDefinition: 'FRAGMENT_DEFINITION',
            _ast.SchemaDefinition: 'SCHEMA',
            _ast.ScalarTypeDefinition: 'SCALAR',
            _ast.ScalarTypeExtension: 'SCALAR',
            _ast.ObjectTypeDefinition: 'OBJECT',
            _ast.ObjectTypeExtension: 'OBJECT',
            _ast.FieldDefinition: 'FIELD_DEFINITION',
            _ast.InterfaceTypeDefinition: 'INTERFACE',
            _ast.InterfaceTypeExtension: 'INTERFACE',
            _ast.UnionTypeDefinition: 'UNION',
            _ast.UnionTypeExtension: 'UNION',
            _ast.EnumTypeDefinition: 'ENUM',
            _ast.EnumTypeExtension: 'ENUM',
            _ast.EnumValueDefinition: 'ENUM_VALUE',
            _ast.InputObjectTypeDefinition: 'INPUT_OBJECT',
            _ast.InputObjectTypeExtension: 'INPUT_OBJECT',
        }[kind]

    def enter_directive(self, node):
        name = node.name.value
        schema_directive = self.schema.directives.get(name)
        if schema_directive is None:
            self.add_error('Unknown directive "@%s"' % name, node)
        else:
            location = self._current_location()
            if location not in schema_directive.locations:
                self.add_error(
                    'Directive "@%s" may not be used on %s'
                    % (name, location), node)


class UniqueDirectivesPerLocationChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all directives at a given location
    are uniquely named. """

    # [WARN] Type system definition locations are not implemented.

    def _validate_unique_directive_names(self, node):
        seen = set()
        for directive in node.directives:
            name = directive.name.value
            if name in seen:
                self.add_error('Duplicate directive "@%s"' % name, directive)
            seen.add(name)

    enter_operation_definition = _validate_unique_directive_names
    enter_field = _validate_unique_directive_names
    enter_field = _validate_unique_directive_names
    enter_fragment_spread = _validate_unique_directive_names
    enter_inline_fragment = _validate_unique_directive_names
    enter_fragment_definition = _validate_unique_directive_names


class KnownArgumentNamesChecker(ValidationVisitor):
    """ A GraphQL field / directive is only valid if all supplied arguments
    are defined by that field / directive. """

    # [TODO] Implement suggestion lists ?

    def enter_field(self, node):
        field_def = self.type_info.field
        if field_def is not None:
            known = set((a.name for a in field_def.args))
            for arg in node.arguments:
                name = arg.name.value
                if name not in known:
                    self.add_error(
                        'Unknown argument "%s" on field "%s" of type "%s"'
                        % (name, field_def.name, self.type_info.parent_type),
                        arg
                    )

    def enter_directive(self, node):
        directive_def = self.type_info.directive
        if directive_def is not None:
            known = set((a.name for a in directive_def.args))
            for arg in node.arguments:
                name = arg.name.value
                if name not in known:
                    self.add_error('Unknown argument "%s" on directive "@%s"'
                                   % (name, directive_def.name), arg)


class UniqueArgumentNamesChecker(ValidationVisitor):
    """ A GraphQL field or directive is only valid if all supplied arguments
    are uniquely named. """

    def _check_duplicate_args(self, node):
        argnames = set()
        for arg in node.arguments:
            name = arg.name.value
            if name in argnames:
                self.add_error('Duplicate argument "%s"' % name, arg)
            argnames.add(name)

    enter_field = _check_duplicate_args
    enter_directive = _check_duplicate_args


class ProvidedNonNullArgumentsChecker(ValidationVisitor):
    """ A field or directive is only valid if all required (non-null) field
    arguments have been provided.
    """
    # Validate on leave to allow for deeper errors to appear first.
    # TODO: Should this be done in other places.

    def _missing_args(self, arg_defs, node):
        node_args = set((arg.name.value for arg in node.arguments))
        for arg in arg_defs:
            if arg.required and (arg.name not in node_args):
                yield arg

    def leave_field(self, node):
        field_def = self.type_info.field
        if field_def:
            for arg in self._missing_args(field_def.args, node):
                self.add_error(
                    'Field "%s" argument "%s" of type %s is required but '
                    'not provided' % (field_def.name, arg.name, arg.type),
                    node)

    def leave_directive(self, node):
        directive_def = self.type_info.directive
        if directive_def:
            for arg in self._missing_args(directive_def.args, node):
                self.add_error(
                    'Directive "@%s" argument "%s" of type %s is required but '
                    'not provided' % (directive_def.name, arg.name, arg.type),
                    node)


class VariablesDefaultValueAllowedChecker(ValidationVisitor):
    """ A GraphQL document is only valid if all variable default values
    are allowed due to a variable not being required.
    """

    # TODO: Implement suggestion lists ?

    def enter_variable_definition(self, node):
        input_type = self.type_info.input_type
        if isinstance(input_type, NonNullType) and node.default_value:
            self.add_error(
                'Variable "$%s" of type %s is required and will not use the '
                'default value' % (node.variable.name.value, input_type),
                node
            )


class VariablesInAllowedPositionChecker(VariablesCollector):
    """ Variables passed to field arguments conform to type """

    def leave_document(self, node):
        self._flatten_fragments()
        for op, vardefs in self._op_defined_variables.items():
            variables = self._op_variables[op]
            fragments = self._op_fragments[op]

            def iter_variables():
                for name, (node, input_type) in variables.items():
                    yield name, (node, input_type)
                for fragment in fragments:
                    frament_vars = self._fragment_variables[fragment].items()
                    for name, (node, input_type) in frament_vars:
                        yield name, (node, input_type)

            for varname, (varnode, input_type) in iter_variables():
                vardef = vardefs.get(varname)
                if vardef and input_type:

                    try:
                        vartype = self.schema.get_type_from_literal(vardef.type)
                    except UnknownType:
                        vartype = None

                    real_type = (
                        vartype
                        if (isinstance(vartype, NonNullType) or
                            not vardef.default_value)
                        else NonNullType(vartype)
                    )
                    if not self.schema.is_subtype(real_type, input_type):
                        self.add_error(
                            'Variable "$%s" of type %s used in position '
                            'expecting type %s'
                            % (varname, print_ast(vardef.type), input_type),
                            varnode
                        )


class UniqueInputFieldNamesChecker(ValidationVisitor):
    """ A GraphQL input object value is only valid if all supplied fields are
    uniquely named.
    """
    def __init__(self, *args, **kwargs):
        super(UniqueInputFieldNamesChecker, self).__init__(*args, **kwargs)
        self._stack = []

    def enter_object_value(self, node):
        self._stack.append((node, set()))

    def leave_object_value(self, node):
        self._stack.pop()

    def enter_object_field(self, node):
        fieldname = node.name.value
        parent, names = self._stack[-1]
        if fieldname in names:
            self.add_error(
                'There can be only one input field named %s.' % fieldname,
                node)
        names.add(fieldname)