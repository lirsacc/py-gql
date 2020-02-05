# -*- coding: utf-8 -*-

from typing import (
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from .._utils import DefaultOrderedDict, OrderedDict, deduplicate, find_one
from ..exc import UnknownEnumValue, UnknownType, ValidationError
from ..lang import ast as _ast
from ..lang.visitor import DispatchingVisitor
from ..schema import (
    Argument,
    Directive,
    EnumType,
    EnumValue,
    Field,
    GraphQLCompositeType,
    InputObjectType,
    InputValue,
    InterfaceType,
    ListType,
    ObjectType,
    ScalarType,
    Schema,
    is_input_type,
    is_output_type,
    nullable_type,
    unwrap_type,
)
from ..schema.introspection import (
    SCHEMA_INTROSPECTION_FIELD,
    TYPE_INTROSPECTION_FIELD,
    TYPE_NAME_INTROSPECTION_FIELD,
)

T = TypeVar("T")
N = TypeVar("N", bound=_ast.Node)
MMap = Mapping[str, Mapping[str, T]]
LMap = Mapping[str, List[T]]
OptList = List[Optional[T]]
InputType = Union[InputObjectType, EnumType, ScalarType]


VariableUsages = MMap[
    Tuple[
        _ast.Variable,
        Optional[Union[EnumType, ScalarType, InputObjectType]],
        Optional[Union[_ast.Argument, _ast.Field]],
    ]
]


def _peek(
    lst: Sequence[T], count: int = 1, default: Optional[T] = None
) -> Optional[T]:
    return lst[-1 * count] if len(lst) >= count else default


def _get_field_def(schema, parent_type, field):
    name = field.name.value
    if parent_type is schema.query_type:
        if name == SCHEMA_INTROSPECTION_FIELD.name:
            return SCHEMA_INTROSPECTION_FIELD
        if name == TYPE_INTROSPECTION_FIELD.name:
            return TYPE_INTROSPECTION_FIELD

    if (
        isinstance(parent_type, GraphQLCompositeType)
        and name == TYPE_NAME_INTROSPECTION_FIELD.name
    ):
        return TYPE_NAME_INTROSPECTION_FIELD

    if isinstance(parent_type, (ObjectType, InterfaceType)):
        return parent_type.field_map.get(name, None)

    return None


class ValidationVisitor(DispatchingVisitor):
    """ Visitor class used for validating GraphQL documents.

    Subclass this to implement custom validators. Use :meth:`add_error` to
    register errors and :class:`py_gql.lang.visitor.SkipNode` to prevent
    validating child nodes when parent node is invalid.

    Args:
        schema: Schema to validate against (for known types, directives, etc.).
        type_info: Type information collector provided by
            :func:`~py_gql.validation.validate`.

    Attributes:
        schema (py_gql.schema.Schema): Schema to validate against
            (for known types, directives, etc.).
        type_info (TypeInfoVisitor): Type information collector provided by
            :func:`~py_gql.validation.validate`.
        errors (List[ValidationError]): Collected errors.
    """

    def __init__(self, schema: Schema, type_info: "TypeInfoVisitor"):
        super(ValidationVisitor, self).__init__()
        self.schema = schema
        self.type_info = type_info
        self.errors = []  # type: List[ValidationError]

    def add_error(
        self, message: str, nodes: Optional[Sequence[_ast.Node]] = None
    ) -> None:
        """ Register an error

        Args:
            message (str): Error description
            nodes (Optional[List[py_gql.lang.ast.Node]]):
                Nodes where the error comes from
        """
        self.errors.append(ValidationError(message, nodes))

    def enter(self, node: N) -> N:
        super().enter(node)
        return node


class VariablesCollector(ValidationVisitor):
    """
    Custom validation visitor which tracks all variable definitions and
    usage across the document.
    """

    def __init__(self, schema, type_info):
        super(VariablesCollector, self).__init__(schema, type_info)

        self._op = None
        self._op_variables = DefaultOrderedDict(
            OrderedDict
        )  # type: VariableUsages
        self._op_defined_variables = DefaultOrderedDict(
            OrderedDict
        )  # type: MMap[_ast.VariableDefinition]
        self._op_fragments = DefaultOrderedDict(list)  # type: LMap[str]
        self._fragment = None
        self._fragment_variables = DefaultOrderedDict(
            OrderedDict
        )  # type: VariableUsages
        self._fragment_fragments = DefaultOrderedDict(list)  # type: LMap[str]
        self._in_var_def = False

    def enter_operation_definition(self, node):
        self._op = node.name.value if node.name else ""

    def leave_operation_definition(self, _node):
        self._op = None

    def enter_fragment_definition(self, node):
        self._fragment = node.name.value

    def leave_fragment_definition(self, _node):
        self._fragment = None

    def enter_fragment_spread(self, node):
        name = node.name.value
        if self._op is not None:
            self._op_fragments[self._op].append(name)
        elif self._fragment is not None and name != self._fragment:
            self._fragment_fragments[self._fragment].append(name)

    def enter_variable_definition(self, node):
        self._in_var_def = True
        if self._op is not None:
            name = node.variable.name.value
            self._op_defined_variables[self._op][name] = node  # type: ignore

    def leave_variable_definition(self, _node):
        self._in_var_def = False

    def enter_variable(self, node):
        var = node.name.value
        input_type = self.type_info.input_type
        input_value_def = self.type_info.input_value_def
        if self._in_var_def:
            pass
        elif self._op is not None:
            self._op_variables[self._op][var] = (  # type: ignore
                node,
                input_type,
                input_value_def,
            )
        elif self._fragment is not None:
            self._fragment_variables[self._fragment][var] = (  # type: ignore
                node,
                input_type,
                input_value_def,
            )

    def _flatten_fragments(self):
        for parent, children in self._fragment_fragments.items():
            for child in deduplicate(children):
                for op in self._op_fragments.keys():
                    if parent in self._op_fragments[op]:
                        self._op_fragments[op].append(child)

    def leave_document(self, _):
        self._flatten_fragments()


# This is a very basic re-implementation of the reference javascript
# implementation which is compatible with our version of AST visitors
# and it can most likley be improved.
class TypeInfoVisitor(DispatchingVisitor):
    """
    Utility visitor that recurisvely track the current types and field
    definitions while traversing a Document.

    All tracked types are considered with regards to the provided schema,
    however unknown types and other unexpected errors will be downgraded to
    null values in order to not crash the traversal. This leaves the consumer
    responsible to handle such cases.

    Warning:
        When using this alongside other visitors (such as when using
        :class:`py_gql.lang.visitor.ChainedVisitor`), this visitor **must**
        to be the first one to visit the nodes in order for the information
        provided donwstream to be accurate.

    Args:
        schema (py_gql.schema.Schema): Reference schema to extract types from

    Attributes:

        type (Optional[py_gql.schema.ObjectType]):
            Current type if applicable

        parent_type (Optional[py_gql.schema.ObjectType]):
            Current type if applicable_stack, 1)

        input_type (Optional[Union[\
py_gql.schema.InputObjectType, \
py_gql.schema.EnumType, \
py_gql.schema.ScalarType]]):
            Current input type if applicable (when visiting arguments)

        parent_input_type (Optional[py_gql.schema.InputObjectType]):
            Current parent input type if applicable (when visiting input objects)

        fiel (Optional[py_gql.schema.Field]):
            Current field definition if applicable (when visiting object)

        input_value_def (Optional[py_gql.schema.InputValue]):
            Current input value definition (e.g. arg def, input field) if applicable
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

    def __init__(self, schema):
        self._schema = schema

        self._type_stack = []  # type: OptList[ObjectType]
        self._parent_type_stack = []  # type: OptList[ObjectType]
        self._input_type_stack = []  # type: OptList[InputType]
        self._field_stack = []  # type: OptList[Field]
        self._input_value_def_stack = []  # type: OptList[Union[InputValue]]

        self.directive = None  # type: Optional[Directive]
        self.argument = None  # type: Optional[Argument]
        self.enum_value = None  # type: Optional[EnumValue]

    @property
    def type(self) -> Optional[ObjectType]:
        return _peek(self._type_stack)

    @property
    def parent_type(self) -> Optional[ObjectType]:
        return _peek(self._parent_type_stack, 1)

    @property
    def input_type(self) -> Optional[InputType]:
        return _peek(self._input_type_stack, 1)

    @property
    def parent_input_type(self) -> Optional[InputObjectType]:
        t = _peek(self._input_type_stack, 2)
        return t if isinstance(t, InputObjectType) else None

    @property
    def field(self) -> Optional[Field]:
        return _peek(self._field_stack)

    @property
    def input_value_def(self) -> Optional[Union[InputValue]]:
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
        named_type = (
            cast(ObjectType, unwrap_type(self.type)) if self.type else None
        )
        self._parent_type_stack.append(
            named_type if isinstance(named_type, GraphQLCompositeType) else None
        )
        return node

    def leave_selection_set(self, _node):
        self._parent_type_stack.pop()

    def enter_field(self, node):
        field_def = self._get_field_def(node)
        self._field_stack.append(field_def)
        self._type_stack.append(
            field_def.type
            if field_def and is_output_type(field_def.type)
            else None
        )
        return node

    def leave_field(self, _node):
        self._type_stack.pop()
        self._field_stack.pop()

    def enter_directive(self, node):
        self.directive = self._schema.directives.get(node.name.value)
        return node

    def leave_directive(self, _node):
        self.directive = None

    def enter_operation_definition(self, node):
        type_ = {
            "query": self._schema.query_type,
            "mutation": self._schema.mutation_type,
            "subscription": self._schema.subscription_type,
        }.get(node.operation, None)
        self._type_stack.append(
            type_ if isinstance(type_, ObjectType) else None
        )
        return node

    def leave_operation_definition(self, _node):
        self._type_stack.pop()

    def enter_fragment_definition(self, node):
        type_ = self._type_from_ast(node.type_condition)
        self._type_stack.append(type_ if is_output_type(type_) else None)
        return node

    def leave_fragment_definition(self, _node):
        self._type_stack.pop()

    def enter_inline_fragment(self, node):
        if node.type_condition:
            type_ = self._type_from_ast(node.type_condition)
            self._type_stack.append(type_ if is_output_type(type_) else None)
        else:
            self._type_stack.append(
                self.type if self.type and is_output_type(self.type) else None
            )
        return node

    def leave_inline_fragment(self, _node):
        self._type_stack.pop()

    def enter_variable_definition(self, node):
        type_ = self._type_from_ast(node.type)
        self._input_type_stack.append(type_ if is_input_type(type_) else None)
        return node

    def leave_variable_definition(self, _node):
        self._input_type_stack.pop()

    def enter_argument(self, node):
        ctx = self.directive or self.field
        if ctx:
            name = node.name.value
            self.argument = find_one(ctx.arguments, lambda a: a.name == name)
            self._input_value_def_stack.append(self.argument)
            self._input_type_stack.append(
                cast(InputType, self.argument.type)
                if self.argument and is_input_type(self.argument.type)
                else None
            )
        else:
            self.argument = None
            self._input_type_stack.append(None)
            self._input_value_def_stack.append(None)
        return node

    def leave_argument(self, _node):
        self.argument = None
        self._leave_input_value()

    def enter_list_value(self, node):
        list_type = nullable_type(self.input_type) if self.input_type else None
        item_type = (
            unwrap_type(list_type) if isinstance(list_type, ListType) else None
        )
        self._input_type_stack.append(
            cast(InputType, item_type)
            if item_type and is_input_type(item_type)
            else None
        )
        # List positions never have a default value.
        self._input_value_def_stack.append(None)
        return node

    def leave_list_value(self, _node):
        self._leave_input_value()

    def enter_object_field(self, node):
        object_type = unwrap_type(self.input_type) if self.input_type else None
        if isinstance(object_type, InputObjectType):
            name = node.name.value
            field_def = find_one(object_type.fields, lambda f: f.name == name)
            self._input_value_def_stack.append(field_def)
            self._input_type_stack.append(
                cast(InputType, field_def.type)
                if field_def and is_input_type(field_def.type)
                else None
            )
        else:
            self._input_type_stack.append(None)
            self._input_value_def_stack.append(None)
        return node

    def leave_object_field(self, _node):
        self._leave_input_value()

    def enter_enum_value(self, node):
        enum = unwrap_type(self.input_type) if self.input_type else None
        if isinstance(enum, EnumType):
            try:
                self.enum_value = enum.get_value(node.value)
            except UnknownEnumValue:
                self.enum_value = None
        return node

    def leave_enum_value(self, _node):
        self.enum_value = None
