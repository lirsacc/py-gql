# -*- coding: utf-8 -*-
""" GraphQL AST representations.
"""

import copy
import json


def node_to_dict(node):
    """ Recrusively convert a ``py_gql.lang.ast.Node`` instance to
    a dict that can be later converted to json. Useful for testing and
    printing in a readable / compatible with JS tooling way.

    :type node: any
    :param node: A node instance or any value used inside nodes (list of nodes
        and primitive values)

    :rtype: dict
    """
    if isinstance(node, Node):
        return dict(
            {
                attr: node_to_dict(getattr(node, attr))
                for attr in node.__slots__
                if attr != "source"
            },
            __kind__=node.__class__.__name__,
        )
    elif isinstance(node, list):
        return [node_to_dict(v) for v in node]
    else:
        return node


class Node(object):
    """ AST node.

    All subclasses encode the language elements describe in
    http://facebook.github.io/graphql/#sec-Language (Schema language related node are
    still part of the draft spec (10 Jun 2018)).
    """

    __slots__ = ("source", "loc")
    __defaults__ = {}

    def __init__(self, *_, **kwargs):
        # [TODO] Does this auto-discovery have a significant perf. impact ?
        # If so the constructor could just be overriden for each subclass.
        for attr in self.__slots__:
            self.__setattr__(attr, kwargs.get(attr, self.__defaults__.get(attr, None)))

    def __eq__(self, rhs):
        return type(rhs) == type(self) and all(
            (
                self.__getattribute__(attr) == rhs.__getattribute__(attr)
                for attr in self.__slots__
                if attr != "source"
            )
        )

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return "<%s %s>" % (
            self.__class__.__name__,
            ", ".join(
                (
                    "%s=%s" % (attr, self.__getattribute__(attr))
                    for attr in self.__slots__
                    if attr != "source"
                )
            ),
        )

    def __getitem__(self, key, default=None):
        if key not in self.__slots__:
            raise KeyError(key)
        return getattr(self, key, default)

    def __copy__(self):
        return self.cls(**{k: getattr(self, k) for k in self.__slots__})

    def __deepcopy__(self):
        return self.cls(**{k: copy.deepcopy(getattr(self, k)) for k in self.__slots__})

    def to_dict(self):
        return node_to_dict(self)

    def to_json(self, **kwargs):
        kwargs.update(sort_keys=True, check_circular=True)
        return json.dumps(self.to_dict(), **kwargs)


class Name(Node):
    """
    :ivar loc: (int, int)
    :ivar value: str
    """

    __slots__ = ("source", "loc", "value")


class Document(Node):
    """
    :ivar loc: (int, int)
    :ivar definitions: list[Definition]
    """

    __slots__ = ("source", "loc", "definitions")
    __defaults__ = {"definitions": []}


class Definition(Node):
    pass


class ExecutableDefinition(Definition):
    pass


class OperationDefinition(ExecutableDefinition):
    """
    :ivar loc: (int, int)
    :ivar operation: str
    :ivar name: Name
    :ivar variable_definitions: list[VariableDefinition]
    :ivar directives: list[Directive]
    :ivar selection_set: SelectionSet
    """

    __slots__ = (
        "loc",
        "operation",
        "name",
        "variable_definitions",
        "directives",
        "selection_set",
    )
    __defaults__ = {"variable_definitions": [], "directives": [], "operation": "query"}


class VariableDefinition(Node):
    """
    :ivar loc: (int, int)
    :ivar variable: Variable
    :ivar type: Type
    :ivar default_value: Optional[Value]
    """

    __slots__ = ("source", "loc", "variable", "type", "default_value")


class Variable(Node):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    """

    __slots__ = ("source", "loc", "name")


class SelectionSet(Node):
    """
    :ivar loc: (int, int)
    :ivar selections: list[Selection]
    """

    __slots__ = ("source", "loc", "selections")
    __defaults__ = {"selections": []}


class Selection(Node):
    pass


class Field(Selection):
    """
    :ivar loc: (int, int)
    :ivar alias: Optional[Name]
    :ivar name: Name
    :ivar arguments: list[Argument]
    :ivar directives: list[Directive]
    :ivar selection_set: Optional[SelectionSet]
    """

    __slots__ = (
        "source",
        "loc",
        "alias",
        "name",
        "arguments",
        "directives",
        "selection_set",
    )
    __defaults__ = {"directives": [], "arguments": []}


class Argument(Node):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    :ivar value: Value
    """

    __slots__ = ("source", "loc", "name", "value")


class FragmentSpread(Selection):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    :ivar directives: list[Directive]
    """

    __slots__ = ("source", "loc", "name", "directives")
    __defaults__ = {"directives": []}


class InlineFragment(Selection):
    """
    :ivar loc: (int, int)
    :ivar type_condition: Type
    :ivar directives: list[Directive]
    :ivar selection_set: SelectionSet
    """

    __slots__ = ("source", "loc", "type_condition", "directives", "selection_set")
    __defaults__ = {"directives": []}


class FragmentDefinition(ExecutableDefinition):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    :ivar variable_definitions: list[VariableDefinition]
    :ivar type_condition: Type
    :ivar directives: list[Directive]
    :ivar selection_set: SelectionSet
    """

    __slots__ = (
        "loc",
        "name",
        "variable_definitions",
        "type_condition",
        "directives",
        "selection_set",
    )
    __defaults__ = {"variable_definitions": [], "directives": []}


class Value(Node):
    pass


class IntValue(Value):
    """
    :ivar loc: (int, int)
    :ivar value: str
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value)


class FloatValue(Value):
    """
    :ivar loc: (int, int)
    :ivar value: str
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value)


class StringValue(Value):
    """
    :ivar loc: (int, int)
    :ivar value: str
    :ivar block: bool
    """

    __slots__ = ("source", "loc", "value", "block")
    __defaults__ = {"block": False}

    def __str__(self):
        if self.block:
            return '"""%s"""' % self.value
        else:
            return '"%s"' % self.value


class BooleanValue(Value):
    """
    :ivar loc: (int, int)
    :ivar value: bool
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value).lower()


class NullValue(Value):
    """
    :ivar loc: (int, int)
    """

    def __str__(self):
        return "null"


class EnumValue(Value):
    """
    :ivar loc: (int, int)
    :ivar value: str
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value)


class ListValue(Value):
    """
    :ivar loc: (int, int)
    :ivar value: list[Value]
    """

    __slots__ = ("source", "loc", "values")


class ObjectValue(Value):
    """
    :ivar loc: (int, int)
    :ivar fields: list[ObjectField]
    """

    __slots__ = ("source", "loc", "fields")
    __defaults__ = {"fields": []}


class ObjectField(Node):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    :ivar value: Value
    """

    __slots__ = ("source", "loc", "name", "value")


class Directive(Node):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    :ivar arguments: list[Argument]
    """

    __slots__ = ("source", "loc", "name", "arguments")
    __defaults__ = {"arguments": []}


class Type(Node):
    pass


class NamedType(Type):
    """
    :ivar loc: (int, int)
    :ivar name: Name
    """

    __slots__ = ("source", "loc", "name")


class ListType(Type):
    """
    :ivar loc: (int, int)
    :ivar type: Type
    """

    __slots__ = ("source", "loc", "type")


class NonNullType(Type):
    """
    :ivar loc: (int, int)
    :ivar type: NamedType|ListType
    """

    __slots__ = ("source", "loc", "type")


class TypeSystemDefinition(Definition):
    pass


class SchemaDefinition(TypeSystemDefinition):
    __slots__ = ("source", "loc", "directives", "operation_types")
    __defaults__ = {"directives": [], "operation_types": []}


class OperationTypeDefinition(Node):
    __slots__ = ("source", "loc", "operation", "type")


class TypeDefinition(TypeSystemDefinition):
    pass


class ScalarTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives")
    __defaults__ = {"directives": []}


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
    __defaults__ = {"interfaces": [], "directives": [], "fields": []}


class FieldDefinition(Node):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "arguments",
        "type",
        "directives",
    )
    __defaults__ = {"arguments": [], "directives": []}


class InputValueDefinition(Node):
    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "type",
        "default_value",
        "directives",
    )
    __defaults__ = {"directives": []}


class InterfaceTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class UnionTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "types")
    __defaults__ = {"directives": [], "types": []}


class EnumTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "values")
    __defaults__ = {"directives": [], "values": []}


class EnumValueDefinition(Node):
    __slots__ = ("source", "loc", "description", "name", "directives")
    __defaults__ = {"directives": []}


class InputObjectTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class TypeExtension(TypeSystemDefinition):
    pass


class ScalarTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives")
    __defaults__ = {"directives": []}


class ObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "interfaces", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class InterfaceTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class UnionTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "types")
    __defaults__ = {"directives": [], "types": []}


class EnumTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "values")
    __defaults__ = {"directives": [], "values": []}


class InputObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class DirectiveDefinition(TypeSystemDefinition):
    __slots__ = ("source", "loc", "description", "name", "arguments", "locations")
    __defaults__ = {"arguments": [], "locations": []}
