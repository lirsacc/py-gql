# -*- coding: utf-8 -*-


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
from py_gql.schema.introspection import (
    schema_field,
    type_field,
    type_name_field,
)


def _peek(lst, count=1, default=None):
    return lst[-1 * count] if len(lst) >= count else default


def _or_none(value, predicate=bool):
    return value if predicate(value) else None


def _get_field_def(schema, parent_type, field):
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
    """ Visitor that tracks current types while traversing a Document.

    All tracked types are considered with regards to the provided schema,
    however unknown types and other unexpected errors will be downgraded to
    null values in order to not crash the traversal. This leaves the consumer
    responsible to handle such cases.

    .. note::

        This is a very basic re-implementation of the reference javascript
        implementation which is compatible with our version of AST visitors
        and it can most likley be improved.

    .. warning::

        When using this alongside other visitors (such as when using
        :class:`py_gql.lang.visitor.ParallelVisitor`), this visitor **needs**
        to be the first one to visit the nodes in order for the information
        provided donwstream to be accurate.
    """

    __slots__ = (
        "_schema",
        "_type_stack",
        "_input_type_stack",
        "_parent_type_stack",
        "_field_stack",
        "_input_value_def_stack",
        "directive",
        "argument",
        "enum_value",
    )

    def __init__(self, schema, _get_field_def=None):
        self._schema = schema

        self._type_stack = []
        self._parent_type_stack = []
        self._input_type_stack = []
        self._field_stack = []
        self._input_value_def_stack = []

        #: Optional[py_gql.schema.Directive]: Current directive if applicable
        self.directive = None
        #: Optional[py_gql.schema.Argument]: Current argument if applicable
        self.argument = None
        #: Optional[py_gql.schema.EnumValue]: Current enum value if applicable
        self.enum_value = None

    @property
    def type(self):
        """ Current type if applicable, else ``None``

        :rtype: Optional[py_gql.schema.Type]
        """
        return _peek(self._type_stack)

    @property
    def parent_type(self):
        """ Current type if applicable, else ``None``

        :rtype: Optional[py_gql.schema.Type]
        """
        return _peek(self._parent_type_stack, 1)

    @property
    def input_type(self):
        """ Current input type if applicable, else ``None``
        (when visiting arguments)

        :rtype: Optional[py_gql.schema.Type]
        """
        return _peek(self._input_type_stack, 1)

    @property
    def parent_input_type(self):
        """ Current parent input type if applicable, else ``None``
        (when visiting input objects)

        :rtype: Optional[py_gql.schema.Type]
        """
        return _peek(self._input_type_stack, 2)

    @property
    def field(self):
        """ Current field definition if applicable, else ``None``

        :rtype: Optional[py_gql.schema.Field]
        """
        return _peek(self._field_stack)

    @property
    def input_value_def(self):
        """ Current input value definition (arg def, input field) if
        applicable, else ``None``

        :rtype: Optional[Union[py_gql.schema.Argument, py_gql.schema.InputField]]
        """
        return _peek(self._input_value_def_stack)

    def _get_field_def(self, node):
        parent_type = self.parent_type
        return (
            _get_field_def(self._schema, parent_type, node)
            if parent_type
            else None
        )

    def _type_from_ast(self, type_node):
        try:
            return self._schema.get_type_from_literal(type_node)
        except UnknownType:
            return None

    def _leave_input_value(self):
        self._input_type_stack.pop()
        self._input_value_def_stack.pop()

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
                _or_none(
                    self._type_from_ast(node.type_condition), is_output_type
                )
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
            self._input_value_def_stack.append(self.argument)
            self._input_type_stack.append(
                self.argument.type
                if self.argument and is_input_type(self.argument.type)
                else None
            )
        else:
            self.argument = None
            self._input_type_stack.append(None)
            self._input_value_def_stack.append(None)

    def leave_argument(self, node):
        self.argument = None
        self._leave_input_value()

    def enter_list_value(self, node):
        list_type = nullable_type(self.input_type)
        item_type = (
            unwrap_type(list_type) if isinstance(list_type, ListType) else None
        )
        self._input_type_stack.append(_or_none(item_type, is_input_type))
        # List positions never have a default value.
        self._input_value_def_stack.append(None)

    def leave_list_value(self, node):
        self._leave_input_value()

    def enter_object_field(self, node):
        object_type = unwrap_type(self.input_type)
        if isinstance(object_type, InputObjectType):
            name = node.name.value
            field_def = find_one(object_type.fields, lambda f: f.name == name)
            self._input_value_def_stack.append(field_def)
            self._input_type_stack.append(
                field_def.type
                if field_def and is_input_type(field_def.type)
                else None
            )
        else:
            self._input_type_stack.append(None)
            self._input_value_def_stack.append(None)

    def leave_object_field(self, node):
        self._leave_input_value()

    def enter_enum_value(self, node):
        enum = unwrap_type(self.input_type)
        if isinstance(enum, EnumType):
            try:
                self.enum_value = enum.get_value(node.value)
            except UnknownEnumValue:
                self.enter_enum_value = None

    def leave_enum_value(self, node):
        self.enum_value = None
