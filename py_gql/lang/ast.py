# -*- coding: utf-8 -*-
"""
GraphQL AST representations corresponding to the `GraphQL language elements
<http://facebook.github.io/graphql/June2018/#sec-Language/#sec-Language>`_.
"""

import copy
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)


class Node:
    """
    Base AST node.
    """

    __slots__ = ()

    source = None  # type: Optional[str]
    loc = None  # type: Optional[Tuple[int, int]]

    def _props(self) -> Iterator[str]:
        for attr in cast(Sequence[str], self.__slots__):
            if attr != "source":
                yield attr

    def __eq__(self, rhs: Any) -> bool:
        return type(rhs) == type(self) and all(
            getattr(self, attr) == getattr(rhs, attr) for attr in self._props()
        )

    def __hash__(self) -> int:
        return id(self)

    def __repr__(self) -> str:
        return "<%s %s>" % (
            self.__class__.__name__,
            ", ".join(
                "%s=%s" % (attr, getattr(self, attr)) for attr in self._props()
            ),
        )

    def __copy__(self):
        return self.__class__(  # type: ignore
            **{k: getattr(self, k) for k in self.__slots__}  # type: ignore
        )

    def __deepcopy__(self, memo):
        return self.__class__(  # type: ignore
            **{  # type: ignore
                k: copy.deepcopy(getattr(self, k), memo) for k in self.__slots__
            }
        )

    copy = __copy__

    def deepcopy(self):
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the current node and all of its children to a JSON serializable
        format.

        This is mostly useful for testing and when you need to convert nodes to
        JSON such as interop with other languages, printing and serialisation.

        The conversion rules are:

        - Each `Node` subclass is converted to a dict of their own converted
          attributes adding a ``__kind__`` key corresponding to the node's
          classname.
        - Primitive values (int, strings, etc.) are left as is.
        - Lists are converted per-element.

        Returns:
            Dict[str, Any]: Converted value
        """
        return cast(Dict[str, Any], _ast_to_json(self))


class Name(Node):
    __slots__ = ("source", "loc", "value")

    def __init__(
        self,
        value: str,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.source = source
        self.loc = loc


class Definition(Node):
    pass


class ExecutableDefinition(Definition):
    pass


class Value(Node):
    pass


class Type(Node):
    pass


class SupportDirectives:
    directives = NotImplemented  # type: List["Directive"]


class NamedType(Type):
    __slots__ = ("source", "loc", "name")

    def __init__(
        self,
        name: Name,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.source = source
        self.loc = loc


class ListType(Type):
    __slots__ = ("source", "loc", "type")

    def __init__(
        self,
        type: Type,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.type = type
        self.source = source
        self.loc = loc


class NonNullType(Type):
    __slots__ = ("source", "loc", "type")

    def __init__(
        self,
        type: Type,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.type = type
        self.source = source
        self.loc = loc


class Document(Node):
    __slots__ = ("source", "loc", "definitions")

    def __init__(
        self,
        definitions: Optional[List[Definition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.definitions = definitions or []  # type: List[Definition]
        self.source = source
        self.loc = loc

    @property
    def fragments(self) -> Dict[str, "FragmentDefinition"]:
        return {
            f.name.value: f
            for f in self.definitions
            if isinstance(f, FragmentDefinition)
        }


class OperationDefinition(SupportDirectives, ExecutableDefinition):
    __slots__ = (
        "source",
        "loc",
        "operation",
        "name",
        "variable_definitions",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        operation: str,
        selection_set,  # type: SelectionSet
        name: Optional[Name] = None,
        variable_definitions=None,  # type: Optional[List[VariableDefinition]]
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.operation = operation
        self.name = name
        self.selection_set = selection_set
        self.variable_definitions = (
            variable_definitions or []
        )  # type: List[VariableDefinition]
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc


class Variable(Node):
    __slots__ = ("source", "loc", "name")

    def __init__(
        self,
        name: Name,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.source = source
        self.loc = loc


class VariableDefinition(SupportDirectives, Node):
    __slots__ = (
        "source",
        "loc",
        "variable",
        "type",
        "default_value",
        "directives",
    )

    def __init__(
        self,
        variable: Variable,
        type: Type,
        default_value=None,  # type: Optional[Value]
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.variable = variable
        self.type = type
        self.default_value = default_value
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc


class Selection(Node):
    pass


class SelectionSet(Node):
    __slots__ = ("source", "loc", "selections")

    def __init__(
        self,
        selections: Optional[List[Selection]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.selections = selections or []  # type: List[Selection]
        self.source = source
        self.loc = loc


class Field(SupportDirectives, Selection):
    __slots__ = (
        "source",
        "loc",
        "name",
        "alias",
        "arguments",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        name: Name,
        alias: Optional[Name] = None,
        arguments=None,  # type: Optional[List[Argument]]
        directives=None,  # type: Optional[List[Directive]]
        selection_set: Optional[SelectionSet] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.alias = alias
        self.name = name
        self.arguments = arguments or []  # type: List[Argument]
        self.directives = directives or []  # type: List[Directive]
        self.selection_set = selection_set
        self.source = source
        self.loc = loc

    @property
    def response_name(self) -> str:
        return self.alias.value if self.alias else self.name.value


class Argument(Node):
    __slots__ = ("source", "loc", "name", "value")

    def __init__(
        self,
        name: Name,
        value: Union[Value, Variable],
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.value = value
        self.source = source
        self.loc = loc


class FragmentSpread(SupportDirectives, Selection):
    __slots__ = ("source", "loc", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc


class InlineFragment(SupportDirectives, Selection):
    __slots__ = (
        "source",
        "loc",
        "type_condition",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        selection_set: SelectionSet,
        type_condition: Optional[Type] = None,
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.type_condition = type_condition
        self.directives = directives or []  # type: List[Directive]
        self.selection_set = selection_set
        self.source = source
        self.loc = loc


class FragmentDefinition(SupportDirectives, ExecutableDefinition):
    __slots__ = (
        "loc",
        "name",
        "variable_definitions",
        "type_condition",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        name: Name,
        type_condition: NamedType,
        selection_set: SelectionSet,
        variable_definitions: Optional[List[VariableDefinition]] = None,
        directives=None,  # type: Optional[List[Directive]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.variable_definitions = (
            variable_definitions or []
        )  # type: List[VariableDefinition]
        self.type_condition = type_condition
        self.directives = directives or []  # type: List[Directive]
        self.selection_set = selection_set
        self.source = source
        self.loc = loc


class _StringValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(
        self,
        value: str,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.source = source
        self.loc = loc

    def __str__(self):
        return str(self.value)


class IntValue(_StringValue):
    pass


class FloatValue(_StringValue):
    pass


class StringValue(Value):
    __slots__ = ("source", "loc", "value", "block")

    def __init__(
        self,
        value: str,
        block: bool = False,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.block = block
        self.source = source
        self.loc = loc

    def __str__(self):
        if self.block:
            return '"""%s"""' % self.value
        else:
            return '"%s"' % self.value


class BooleanValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(
        self,
        value: bool,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.value = value
        self.source = source
        self.loc = loc

    def __str__(self):
        return str(self.value).lower()


class NullValue(Value):
    __slots__ = ("source", "loc")

    def __init__(
        self,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.source = source
        self.loc = loc

    def __str__(self):
        return "null"


class EnumValue(_StringValue):
    pass


class ListValue(Value):
    __slots__ = ("source", "loc", "values")

    def __init__(
        self,
        values: List[Union[Value, Variable]],
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.values = values
        self.source = source
        self.loc = loc


class ObjectValue(Value):
    __slots__ = ("source", "loc", "fields")

    def __init__(
        self,
        fields,  # type: List[ObjectField]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.fields = fields or []
        self.source = source
        self.loc = loc


class ObjectField(Node):
    __slots__ = ("source", "loc", "name", "value")

    def __init__(
        self,
        name: Name,
        value: Value,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.value = value
        self.source = source
        self.loc = loc


class Directive(Node):
    __slots__ = ("source", "loc", "name", "arguments")

    def __init__(
        self,
        name: Name,
        arguments: Optional[List[Argument]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.arguments = arguments or []  # type: List[Argument]
        self.source = source
        self.loc = loc


class SupportDescription:
    description = NotImplemented  # type: Optional[StringValue]


class TypeSystemDefinition(SupportDirectives, Definition):
    pass


class SchemaDefinition(TypeSystemDefinition):
    __slots__ = ("source", "loc", "directives", "operation_types")

    def __init__(
        self,
        directives: Optional[List[Directive]] = None,
        operation_types=None,  # type: Optional[List[OperationTypeDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.directives = directives or []  # type: List[Directive]
        self.operation_types = (
            operation_types or []
        )  # type: List[OperationTypeDefinition]
        self.source = source
        self.loc = loc


class OperationTypeDefinition(Node):
    __slots__ = ("source", "loc", "operation", "type")

    def __init__(
        self,
        operation: str,
        type: NamedType,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.operation = operation
        self.type = type
        self.source = source
        self.loc = loc


class TypeDefinition(SupportDescription, TypeSystemDefinition):
    name = NotImplemented  # type:  Name


class ScalarTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc
        self.description = description


class ObjectTypeDefinition(TypeDefinition):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "interfaces",
        "directives",
        "fields",
    )

    def __init__(
        self,
        name: Name,
        interfaces: Optional[List[NamedType]] = None,
        directives: Optional[List[Directive]] = None,
        fields=None,  # type: Optional[List[FieldDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.interfaces = interfaces or []  # type: List[NamedType]
        self.directives = directives or []  # type: List[Directive]
        self.fields = fields or []  # type: List[FieldDefinition]
        self.source = source
        self.loc = loc
        self.description = description


class FieldDefinition(SupportDirectives, SupportDescription, Node):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "arguments",
        "type",
        "directives",
    )

    def __init__(
        self,
        name: Name,
        type: Type,
        arguments: Optional[List["InputValueDefinition"]] = None,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.arguments = arguments or []  # type: List[InputValueDefinition]
        self.type = type
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc
        self.description = description


class InputValueDefinition(SupportDirectives, SupportDescription, Node):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "type",
        "default_value",
        "directives",
    )

    def __init__(
        self,
        name: Name,
        type: Type,
        default_value: Optional[Value] = None,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.type = type
        self.default_value = default_value
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc
        self.description = description


class InterfaceTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[FieldDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.fields = fields or []  # type: List[FieldDefinition]
        self.source = source
        self.loc = loc
        self.description = description


class UnionTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "types")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[NamedType]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.types = types or []  # type: List[NamedType]
        self.source = source
        self.loc = loc
        self.description = description


class EnumTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "values")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        values=None,  # type: Optional[List[EnumValueDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.values = values or []  # type: List[EnumValueDefinition]
        self.source = source
        self.loc = loc
        self.description = description


class EnumValueDefinition(SupportDirectives, SupportDescription, Node):
    __slots__ = ("source", "loc", "description", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc
        self.description = description


class InputObjectTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[InputValueDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.fields = fields or []  # type: List[InputValueDefinition]
        self.source = source
        self.loc = loc
        self.description = description


class TypeSystemExtension(TypeSystemDefinition):
    pass


class SchemaExtension(TypeSystemExtension):
    __slots__ = ("source", "loc", "directives", "operation_types")

    def __init__(
        self,
        directives: Optional[List[Directive]] = None,
        operation_types: Optional[List[OperationTypeDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.directives = directives or []  # type: List[Directive]
        self.operation_types = (
            operation_types or []
        )  # type: List[OperationTypeDefinition]
        self.source = source
        self.loc = loc


class TypeExtension(TypeSystemExtension):
    name = NotImplemented  # type: Name


class ScalarTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.source = source
        self.loc = loc


class ObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "interfaces", "directives", "fields")

    def __init__(
        self,
        name: Name,
        interfaces: Optional[List[NamedType]] = None,
        directives: Optional[List[Directive]] = None,
        fields=None,  # type: Optional[List[FieldDefinition]]
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.interfaces = interfaces or []  # type: List[NamedType]
        self.directives = directives or []  # type: List[Directive]
        self.fields = fields or []  # type: List[FieldDefinition]
        self.source = source
        self.loc = loc


class InterfaceTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[FieldDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.fields = fields or []  # type: List[FieldDefinition]
        self.source = source
        self.loc = loc


class UnionTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "types")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        types: Optional[List[NamedType]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.types = types or []  # type: List[NamedType]
        self.source = source
        self.loc = loc


class EnumTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "values")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        values: Optional[List[EnumValueDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.values = values or []  # type: List[EnumValueDefinition]
        self.values = values or []
        self.source = source
        self.loc = loc


class InputObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")

    def __init__(
        self,
        name: Name,
        directives: Optional[List[Directive]] = None,
        fields: Optional[List[InputValueDefinition]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
    ):
        self.name = name
        self.directives = directives or []  # type: List[Directive]
        self.fields = fields or []  # type: List[InputValueDefinition]
        self.source = source
        self.loc = loc


class DirectiveDefinition(SupportDescription, TypeSystemDefinition):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "arguments",
        "locations",
    )

    def __init__(
        self,
        name: Name,
        arguments: Optional[List[InputValueDefinition]] = None,
        locations: Optional[List[Name]] = None,
        source: Optional[str] = None,
        loc: Optional[Tuple[int, int]] = None,
        description: Optional[StringValue] = None,
    ):
        self.name = name
        self.arguments = arguments or []  # type: List[InputValueDefinition]
        self.locations = locations or []  # type: List[Name]
        self.source = source
        self.loc = loc
        self.description = description


def _ast_to_json(node):
    if isinstance(node, Node):
        return dict(
            {attr: _ast_to_json(getattr(node, attr)) for attr in node._props()},
            __kind__=node.__class__.__name__,
        )
    elif isinstance(node, list):
        return [_ast_to_json(v) for v in node]
    else:
        return node
