# -*- coding: utf-8 -*-
""" GraphQL AST representations.
"""


def node_to_dict(node):
    """ Recrusively convert a ``py_gql.lang.ast.Node`` instance to
    a dict that can be later converted to json. Useful for testing and
    printing in a readable way.

    :param node:
        A node instance or any value used inside nodes (list of nodes
        and primitive values)

    :rtype: dict
    """
    if isinstance(node, Node):
        d = {attr: node_to_dict(getattr(node, attr)) for attr in node.__slots__}
        d.update(__kind__=node.__class__.__name__)
        return d
    elif isinstance(node, list):
        return [node_to_dict(v) for v in node]
    else:
        return node


class Node(object):
    __slots__ = ('loc')
    __defaults__ = {}

    def __init__(self, *_, **kwargs):
        # [TODO] Does this auto-discovery have a significant perf. impact ?
        # If so the constructor could just be overriden for each subclass.
        for attr in self.__slots__:
            self.__setattr__(
                attr,
                kwargs.get(attr, self.__defaults__.get(attr, None))
            )

    def __eq__(self, rhs):
        return (type(rhs) == self.__class__ and
                all((self.__getattribute__(attr) == rhs.__getattribute__(attr)
                    for attr in self.__slots__)))

    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            ', '.join(('%s=%s'
                       % (attr, self.__getattribute__(attr))
                       for attr in self.__slots__)))


class Name(Node):
    __slots__ = ('loc', 'value')


class Document(Node):
    __slots__ = ('loc', 'definitions')
    __defaults__ = {'definitions': []}


class Definition(Node):
    pass


class ExecutableDefinition(Definition):
    pass


class OperationDefinition(ExecutableDefinition):
    __slots__ = (
        'loc', 'operation', 'name', 'variable_definitions', 'directives',
        'selection_set')
    __defaults__ = {
        'variable_definitions': [], 'directives': [], 'operation': 'query'}


class VariableDefinition(Node):
    __slots__ = ('loc', 'variable', 'type', 'default_value')


class Variable(Node):
    __slots__ = ('loc', 'name')


class SelectionSet(Node):
    __slots__ = ('loc', 'selections')
    __defaults__ = {'selections': []}


class Selection(Node):
    pass


class Field(Selection):
    __slots__ = (
        'loc', 'alias', 'name', 'arguments', 'directives', 'selection_set')
    __defaults__ = {'directives': [], 'arguments': []}


class Argument(Node):
    __slots__ = ('loc', 'name', 'value')


class FragmentSpread(Field):
    __slots__ = ('loc', 'name', 'directives')
    __defaults__ = {'directives': []}


class InlineFragment(Field):
    __slots__ = ('loc', 'type_condition', 'directives', 'selection_set')
    __defaults__ = {'directives': []}


class FragmentDefinition(ExecutableDefinition):
    __slots__ = (
        'loc', 'name', 'variable_defintions', 'type_condition', 'directives',
        'selection_set')
    __defaults__ = {'variable_definitions': [], 'directives': []}


class Value(Node):
    pass


class IntValue(Value):
    __slots__ = ('loc', 'value')


class FloatValue(Value):
    __slots__ = ('loc', 'value')


class StringValue(Value):
    __slots__ = ('loc', 'value', 'block')
    __defaults__ = {'block': False}


class BooleanValue(Value):
    __slots__ = ('loc', 'value')


class NullValue(Value):
    __slots__ = ('loc')


class EnumValue(Value):
    __slots__ = ('loc', 'value')


class ListValue(Value):
    __slots__ = ('loc', 'values')


class ObjectValue(Value):
    __slots__ = ('loc', 'fields')
    __defaults__ = {'fields': []}


class ObjectField(Node):
    __slots__ = ('loc', 'name', 'value')


class Directive(Node):
    __slots__ = ('loc', 'name', 'arguments')
    __defaults__ = {'arguments': []}


class Type(Node):
    pass


class NamedType(Type):
    __slots__ = ('loc', 'name')


class ListType(Type):
    __slots__ = ('loc', 'type')


class NonNullType(Type):
    __slots__ = ('loc', 'type')


class TypeSystemDefinition(Definition):
    pass


class SchemaDefinition(TypeSystemDefinition):
    __slots__ = ('loc', 'directives', 'operation_types')
    __defaults__ = {'directives': [], 'operation_types': []}


class OperationTypeDefinition(Node):
    __slots__ = ('loc', 'operation', 'type')


class TypeDefinition(TypeSystemDefinition):
    pass


class ScalarTypeDefinition(TypeDefinition):
    __slots__ = ('loc', 'description', 'name', 'directives')
    __defaults__ = {'directives': []}


class ObjectTypeDefinition(TypeDefinition):
    __slots__ = (
        'loc', 'description', 'name', 'interfaces', 'directives', 'fields')
    __defaults__ = {'interfaces': [], 'directives': [], 'fields': []}


class FieldDefinition(Node):
    __slots__ = (
        'loc', 'description', 'name', 'arguments', 'type', 'directives')
    __defaults__ = {'arguments': [], 'directives': []}


class InputValueDefinition(Node):
    __slots__ = (
        'loc', 'description', 'name', 'type', 'default_value', 'directives')
    __defaults__ = {'directives': []}


class InterfaceTypeDefinition(TypeDefinition):
    __slots__ = ('loc', 'description', 'name', 'directives', 'fields')
    __defaults__ = {'directives': [], 'fields': []}


class UnionTypeDefinition(TypeDefinition):
    __slots__ = ('loc', 'description', 'name', 'directives', 'types')
    __defaults__ = {'directives': [], 'types': []}


class EnumTypeDefinition(TypeDefinition):
    __slots__ = ('loc', 'description', 'name', 'directives', 'values')
    __defaults__ = {'directives': [], 'values': []}


class EnumValueDefinition(Node):
    __slots__ = ('loc', 'description', 'name', 'directives')
    __defaults__ = {'directives': []}


class InputObjectTypeDefinition(TypeDefinition):
    __slots__ = ('loc', 'description', 'name', 'directives', 'fields')
    __defaults__ = {'directives': [], 'fields': []}


class TypeExtension(TypeSystemDefinition):
    pass


class ScalarTypeExtension(TypeExtension):
    __slots__ = ('loc', 'name', 'directives')
    __defaults__ = {'directives': []}


class ObjectTypeExtension(TypeExtension):
    __slots__ = ('loc', 'name', 'interfaces', 'directives', 'fields')
    __defaults__ = {'directives': [], 'fields': []}


class InterfaceTypeExtension(TypeExtension):
    __slots__ = ('loc', 'name', 'directives', 'fields')
    __defaults__ = {'directives': [], 'fields': []}


class UnionTypeExtension(TypeExtension):
    __slots__ = ('loc', 'name', 'directives', 'types')
    __defaults__ = {'directives': [], 'types': []}


class EnumTypeExtension(TypeExtension):
    __slots__ = ('loc', 'name', 'directives', 'values')
    __defaults__ = {'directives': [], 'values': []}


class InputObjectTypeExtension(TypeExtension):
    __slots__ = ('loc', 'name', 'directives', 'fields')
    __defaults__ = {'directives': [], 'fields': []}


class DirectiveDefinition(TypeSystemDefinition):
    __slots__ = ('loc', 'description', 'name', 'arguments', 'locations')
    __defaults__ = {'arguments': [], 'locations': []}
