# -*- coding: utf-8 -*-
""" Context visitor to track current types and parent while
traversing an ast.
"""


from py_gql._utils import find_one
from py_gql.exc import UnknownEnumValue, UnknownType
from py_gql.lang.visitor import DispatchingVisitor
from py_gql.schema import (
    EnumType,
    InputObjectType,
    InterfaceType,
    ListType,
    ObjectType,
    is_composite_type,
    is_input_type,
    is_output_type,
    nullable_type,
    unwrap_type,
)
from py_gql.schema.introspection import schema_field, type_field, type_name_field


def _peek(lst, count=1, default=None):
    return lst[-1 * count] if len(lst) >= count else default


def _or_none(value, predicate=bool):
    return value if predicate(value) else None


def get_field_def(schema, parent_type, field):
    name = field.name.value
    if parent_type is schema.query_type:
        if name == schema_field.name:
            return schema_field
        if name == type_field.name:
            return type_field

    if is_composite_type(parent_type) and name == type_name_field.name:
        return type_name_field

    if isinstance(parent_type, (ObjectType, InterfaceType)):
        return parent_type.field_map.get(name, None)

    return None


class TypeInfoVisitor(DispatchingVisitor):
    """ Keep track of current type context while visiting a document.

    Simple visitor made to maintain a stack of current types in order to
    inspect types with regards to a schema while traversing a parse tree.
    Very basic re-implementation of the JS version that can most likley be
    improved.

    When using this alongside other visitors (such as when using
    `ParallelVisitor`), this visitor needs to be the firt one to visit the
    nodes in order for the information provided to be accurate donwstream.
    """

    slots = (
        "_schema",
        "_type_stack",
        "_input_type_stack",
        "_get_field_def_fn",
        "_parent_type_stack",
        "_field_stack",
        "directive",
        "argument",
        "enum_value",
    )

    def __init__(self, schema, _get_field_def=None):
        self._schema = schema
        self._get_field_def_fn = _get_field_def or get_field_def

        self._type_stack = []
        self._parent_type_stack = []
        self._input_type_stack = []
        self._field_stack = []

        self.directive = None
        self.argument = None
        self.enum_value = None

    @property
    def type(self):
        return _peek(self._type_stack)

    @property
    def parent_type(self):
        return _peek(self._parent_type_stack, 1)

    @property
    def input_type(self):
        return _peek(self._input_type_stack, 1)

    @property
    def parent_input_type(self):
        return _peek(self._input_type_stack, 2)

    @property
    def field(self):
        return _peek(self._field_stack)

    def _get_field_def(self, node):
        parent_type = self.parent_type
        return (
            self._get_field_def_fn(self._schema, parent_type, node)
            if parent_type
            else None
        )

    def _type_from_ast(self, type_node):
        try:
            return self._schema.get_type_from_literal(type_node)
        except UnknownType:
            return None

    def enter_selection_set(self, node):
        named_type = unwrap_type(self.type)
        self._parent_type_stack.append(_or_none(named_type, is_composite_type))

    def leave_selection_set(self, node):
        self._parent_type_stack.pop()

    def enter_field(self, node):
        field_def = self._get_field_def(node)
        self._field_stack.append(field_def)
        if field_def:
            self._type_stack.append(_or_none(field_def.type, is_output_type))
        else:
            self._type_stack.append(None)

    def leave_field(self, node):
        self._type_stack.pop()
        self._field_stack.pop()

    def enter_directive(self, node):
        self.directive = self._schema.directives.get(node.name.value)

    def leave_directive(self, node):
        self.directive = None

    def enter_operation_definition(self, node):
        typ = {
            "query": self._schema.query_type,
            "mutation": self._schema.mutation_type,
            "subscription": self._schema.subscription_type,
        }.get(node.operation, None)
        self._type_stack.append(typ if isinstance(typ, ObjectType) else None)

    def leave_operation_definition(self, node):
        self._type_stack.pop()

    def enter_fragment_definition(self, node):
        self._type_stack.append(
            _or_none(self._type_from_ast(node.type_condition), is_output_type)
        )

    def leave_fragment_definition(self, node):
        self._type_stack.pop()

    def enter_inline_fragment(self, node):
        if node.type_condition:
            self._type_stack.append(
                _or_none(self._type_from_ast(node.type_condition), is_output_type)
            )
        else:
            self._type_stack.append(_or_none(self.type, is_output_type))

    def leave_inline_fragment(self, node):
        self._type_stack.pop()

    def enter_variable_definition(self, node):
        self._input_type_stack.append(
            _or_none(self._type_from_ast(node.type), is_input_type)
        )

    def leave_variable_definition(self, node):
        self._input_type_stack.pop()

    def enter_argument(self, node):
        ctx = self.directive or self.field
        if ctx:
            name = node.name.value
            self.argument = find_one(ctx.args, lambda a: a.name == name)
            self._input_type_stack.append(
                self.argument.type
                if self.argument and is_input_type(self.argument.type)
                else None
            )
        else:
            self.argument = None
            self._input_type_stack.append(None)

    def leave_argument(self, node):
        self.argument = None
        self._input_type_stack.pop()

    def enter_list_value(self, node):
        list_type = nullable_type(self.input_type)
        item_type = unwrap_type(list_type) if isinstance(list_type, ListType) else None
        self._input_type_stack.append(_or_none(item_type, is_input_type))

    def leave_list_value(self, node):
        self._input_type_stack.pop()

    def enter_object_field(self, node):
        object_type = unwrap_type(self.input_type)
        if isinstance(object_type, InputObjectType):
            name = node.name.value
            field_def = find_one(object_type.fields, lambda f: f.name == name)
            self._input_type_stack.append(
                field_def.type if field_def and is_input_type(field_def.type) else None
            )
        else:
            self._input_type_stack.append(None)

    def leave_object_field(self, node):
        self._input_type_stack.pop()

    def enter_enum_value(self, node):
        enum = unwrap_type(self.input_type)
        if isinstance(enum, EnumType):
            try:
                self.enum_value = enum.get_value(node.value)
            except UnknownEnumValue:
                self.enter_enum_value = None

    def leave_enum_value(self, node):
        self.enum_value = None
