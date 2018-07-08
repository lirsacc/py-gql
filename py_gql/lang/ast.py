# -*- coding: utf-8 -*-
""" GraphQL AST representations corresponding to the `GraphQL language elements`_.

 .. _GraphQL language elements:
   http://facebook.github.io/graphql/June2018/#sec-Language/#sec-Language
"""

import copy


class Node(object):
    """ Base AST node.

    - All subclasses should implement ``__slots__`` so ``__eq__`` and
      ``__repr__``, ``__copy__``, ``__deepcopy__`` and :meth:`to_dict` can work.
    - The ``source`` attribute is ignored for comparisons and serialization.
    """

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
        """ Convert the current node to a JSON serializable ``dict`` using
        :func:`node_to_dict`.

        Returns:
            dict: Converted value
        """
        return node_to_dict(self)


class Name(Node):
    __slots__ = ("source", "loc", "value")

    def __init__(self, value=None, source=None, loc=None):
        #: str: value
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Document(Node):
    __slots__ = ("source", "loc", "definitions")

    def __init__(self, definitions=None, source=None, loc=None):
        #: List[py_gql.lang.ast.Definition]: Definitions
        self.definitions = definitions or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Definition(Node):
    pass


class ExecutableDefinition(Definition):
    pass


class OperationDefinition(ExecutableDefinition):
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
        operation=None,
        name=None,
        variable_definitions=None,
        directives=None,
        selection_set=None,
        source=None,
        loc=None,
    ):
        #: str:
        self.operation = operation or "query"
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.VariableDefinition]:
        self.variable_definitions = variable_definitions or []
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: py_gql.lang.ast.SelectionSet:
        self.selection_set = selection_set
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class VariableDefinition(Node):
    __slots__ = ("source", "loc", "variable", "type", "default_value")

    def __init__(
        self, variable=None, type=None, default_value=None, source=None, loc=None
    ):
        #: py_gql.lang.ast.Variable:
        self.variable = variable
        #: py_gql.lang.ast.Type:
        self.type = type
        #: py_gql.lang.ast.Value:
        self.default_value = default_value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Variable(Node):
    __slots__ = ("source", "loc", "name")

    def __init__(self, name=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class SelectionSet(Node):
    __slots__ = ("source", "loc", "selections")

    def __init__(self, selections=None, source=None, loc=None):
        #: List[py_gql.lang.ast.Selection]:
        self.selections = selections or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Selection(Node):
    pass


class Field(Selection):
    __slots__ = (
        "source",
        "loc",
        "alias",
        "name",
        "arguments",
        "directives",
        "selection_set",
    )

    def __init__(
        self,
        alias=None,
        name=None,
        arguments=None,
        directives=None,
        selection_set=None,
        source=None,
        loc=None,
    ):
        #: py_gql.lang.ast.Name:
        self.alias = alias
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Argument]:
        self.arguments = arguments or []
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: py_gql.lang.ast.SelectionSet:
        self.selection_set = selection_set
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Argument(Node):
    __slots__ = ("source", "loc", "name", "value")

    def __init__(self, name=None, value=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: py_gql.lang.ast.Value:
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class FragmentSpread(Selection):
    __slots__ = ("source", "loc", "name", "directives")

    def __init__(self, name=None, directives=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class InlineFragment(Selection):
    __slots__ = ("source", "loc", "type_condition", "directives", "selection_set")

    def __init__(
        self,
        type_condition=None,
        directives=None,
        selection_set=None,
        source=None,
        loc=None,
    ):
        #: py_gql.lang.ast.Type:
        self.type_condition = type_condition
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: py_gql.lang.ast.SelectionSet:
        self.selection_set = selection_set
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class FragmentDefinition(ExecutableDefinition):
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
        name=None,
        variable_definitions=None,
        type_condition=None,
        directives=None,
        selection_set=None,
        source=None,
        loc=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.VariableDefinition]:
        self.variable_definitions = variable_definitions or []
        #: py_gql.lang.ast.Type:
        self.type_condition = type_condition
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: py_gql.lang.ast.SelectionSet:
        self.selection_set = selection_set
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Value(Node):
    pass


class IntValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(self, value=None, source=None, loc=None):
        #: str: value
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc

    def __str__(self):
        return str(self.value)


class FloatValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(self, value=None, source=None, loc=None):
        #: str: value
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc

    def __str__(self):
        return str(self.value)


class StringValue(Value):
    __slots__ = ("source", "loc", "value", "block")

    def __init__(self, value=None, block=False, source=None, loc=None):
        #: str: value
        self.value = value
        #: bool:
        self.block = block
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc

    def __str__(self):
        if self.block:
            return '"""%s"""' % self.value
        else:
            return '"%s"' % self.value


class BooleanValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(self, value=None, source=None, loc=None):
        #: str: value
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc

    def __str__(self):
        return str(self.value).lower()


class NullValue(Value):
    __slots__ = ("source", "loc")

    def __init__(self, source=None, loc=None):
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc

    def __str__(self):
        return "null"


class EnumValue(Value):
    __slots__ = ("source", "loc", "value")

    def __init__(self, value=None, source=None, loc=None):
        #: str: value
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc

    def __str__(self):
        return str(self.value)


class ListValue(Value):
    __slots__ = ("source", "loc", "values")

    def __init__(self, values=None, source=None, loc=None):
        #: List[py_gql.lang.ast.Value]: values
        self.values = values or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class ObjectValue(Value):
    __slots__ = ("source", "loc", "fields")

    def __init__(self, fields=None, source=None, loc=None):
        #: List[py_gql.lang.ast.ObjectField]: fields
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class ObjectField(Node):
    __slots__ = ("source", "loc", "name", "value")

    def __init__(self, name=None, value=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: py_gql.lang.ast.Value: value
        self.value = value
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Directive(Node):
    __slots__ = ("source", "loc", "name", "arguments")

    def __init__(self, name=None, arguments=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: py_gql.lang.ast.Argument:
        self.arguments = arguments or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class Type(Node):
    pass


class NamedType(Type):
    __slots__ = ("source", "loc", "name")

    def __init__(self, name=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class ListType(Type):
    __slots__ = ("source", "loc", "type")

    def __init__(self, type=None, source=None, loc=None):
        #: py_gql.lang.ast.Type:
        self.type = type
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class NonNullType(Type):
    __slots__ = ("source", "loc", "type")

    def __init__(self, type=None, source=None, loc=None):
        #: py_gql.lang.ast.Type:
        self.type = type
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class TypeSystemDefinition(Definition):
    pass


class SchemaDefinition(TypeSystemDefinition):
    __slots__ = ("source", "loc", "directives", "operation_types")

    def __init__(self, directives=None, operation_types=None, source=None, loc=None):
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.OperationTypeDefinition]:
        self.operation_types = operation_types or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class OperationTypeDefinition(Node):
    __slots__ = ("source", "loc", "operation", "type")

    def __init__(self, operation=None, type=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.operation = operation
        #: py_gql.lang.ast.NamedType:
        self.type = type
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class TypeDefinition(TypeSystemDefinition):
    pass


class ScalarTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives")

    def __init__(
        self, name=None, directives=None, source=None, loc=None, description=None
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
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
        name=None,
        interfaces=None,
        directives=None,
        fields=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.NamedType]:
        self.interfaces = interfaces or []
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.FieldDefinition]:
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


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

    def __init__(
        self,
        name=None,
        arguments=None,
        type=None,
        directives=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.InputValueDefinition]:
        self.arguments = arguments or []
        #: py_gql.lang.ast.Type:
        self.type = type
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


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

    def __init__(
        self,
        name=None,
        type=None,
        default_value=None,
        directives=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: py_gql.lang.ast.Type:
        self.type = type
        #: py_gql.lang.ast.Value:
        self.default_value = default_value
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


class InterfaceTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")

    def __init__(
        self,
        name=None,
        directives=None,
        fields=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.FieldDefinition]:
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


class UnionTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "types")

    def __init__(
        self,
        name=None,
        directives=None,
        types=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.NamedType]:
        self.types = types or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


class EnumTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "values")

    def __init__(
        self,
        name=None,
        directives=None,
        values=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.EnumValueDefinition]:
        self.values = values or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


class EnumValueDefinition(Node):
    __slots__ = ("source", "loc", "description", "name", "directives")

    def __init__(
        self, name=None, directives=None, source=None, loc=None, description=None
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


class InputObjectTypeDefinition(TypeDefinition):
    __slots__ = ("source", "loc", "description", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}

    def __init__(
        self,
        name=None,
        directives=None,
        fields=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.InputValueDefinition]:
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


class TypeExtension(TypeSystemDefinition):
    pass


class ScalarTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives")

    def __init__(self, name=None, directives=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class ObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "interfaces", "directives", "fields")

    def __init__(
        self,
        name=None,
        interfaces=None,
        directives=None,
        fields=None,
        source=None,
        loc=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.NamedType]:
        self.interfaces = interfaces or []
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.FieldDefinition]:
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class InterfaceTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")

    def __init__(self, name=None, directives=None, fields=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.FieldDefinition]:
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class UnionTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "types")

    def __init__(self, name=None, directives=None, types=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.NamedType]:
        self.types = types or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class EnumTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "values")

    def __init__(self, name=None, directives=None, values=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.EnumValueDefinition]:
        self.values = values or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class InputObjectTypeExtension(TypeExtension):
    __slots__ = ("source", "loc", "name", "directives", "fields")

    def __init__(self, name=None, directives=None, fields=None, source=None, loc=None):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.Directives]:
        self.directives = directives or []
        #: List[py_gql.lang.ast.InputValueDefinition]:
        self.fields = fields or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc


class DirectiveDefinition(TypeSystemDefinition):
    __slots__ = ("source", "loc", "description", "name", "arguments", "locations")

    def __init__(
        self,
        name=None,
        arguments=None,
        locations=None,
        directives=None,
        source=None,
        loc=None,
        description=None,
    ):
        #: py_gql.lang.ast.Name:
        self.name = name
        #: List[py_gql.lang.ast.InputValueDefinition]:
        self.arguments = arguments or []
        #: List[py_gql.lang.ast.Name]:
        self.locations = locations or []
        #: str: source document
        self.source = source
        #: Tuple[int, int]: Node position as (start position, end position)
        self.loc = loc
        #: py_gql.lang.ast.SringValue:
        self.description = description


def node_to_dict(node):
    """ Recrusively convert a ``py_gql.lang.ast.Node`` instance to a dict.

    This is mostly useful for testing and when you need to convert nodes to JSON
    such as interop with other languages, printing and serialisation.

    Nodes are converted based on their `__slots__` adding a `__kind__` key
    corresponding to the node class while primitive values are left as is.
    Lists are converted per-element.

    Argss:
        node (any): A :class:`Node` instance or any node attribute

    Returns:
        Converted value
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
