# -*- coding: utf-8 -*-
""" GraphQL AST representations corresponding to the `GraphQL language elements`_.


 .. _GraphQL language elements:
   http://facebook.github.io/graphql/June2018/#sec-Language/#sec-Language
"""

import copy


class Node(object):
    """ Base AST node.

    Subclasses should not override the constructor but rather define their own
    ``__slots__`` and ``__defaults__`` attributes which are used to create the
    instances.

    The source attribute is ignored for comparisons and serialization.

    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: st
    """

    __slots__ = ("source", "loc")
    __defaults__ = {}

    def __init__(self, *_, **kwargs):
        # [TODO] Does this auto-discovery have a significant perf. impact ?
        # If so the constructor could just be overriden for each subclass.
        for attr in self.__slots__:
            self.__setattr__(
                attr, kwargs.get(attr, self.__defaults__.get(attr, None))
            )

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
        return self.cls(
            **{k: copy.deepcopy(getattr(self, k)) for k in self.__slots__}
        )

    def to_dict(self):
        """ Convert the current node to a JSON serializable ``dict`` using
        :func:`node_to_dict`.

        :rtype: ``dict``
        """
        return node_to_dict(self)


class Name(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: st
    """

    __slots__ = ("source", "loc", "value")


class Document(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar definitions:
    :vartype definitions: List[Definition
    """

    __slots__ = ("source", "loc", "definitions")
    __defaults__ = {"definitions": []}


class Definition(Node):
    pass


class ExecutableDefinition(Definition):
    pass


class OperationDefinition(ExecutableDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar operation:
    :vartype operation: str

    :ivar name:
    :vartype name: Name

    :ivar variable_definitions:
    :vartype variable_definitions: List[VariableDefinition]

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar selection_set:
    :vartype selection_set: SelectionSet
    """

    __slots__ = (
        "loc",
        "operation",
        "name",
        "variable_definitions",
        "directives",
        "selection_set",
    )
    __defaults__ = {
        "variable_definitions": [],
        "directives": [],
        "operation": "query",
    }


class VariableDefinition(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar variable:
    :vartype variable: Variable

    :ivar type:
    :vartype type: Type

    :ivar default_value:
    :vartype default_value: Optional[Value]
    """

    __slots__ = ("source", "loc", "variable", "type", "default_value")


class Variable(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name
    """

    __slots__ = ("source", "loc", "name")


class SelectionSet(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar selections:
    :vartype selections: List[Selection]
    """

    __slots__ = ("source", "loc", "selections")
    __defaults__ = {"selections": []}


class Selection(Node):
    pass


class Field(Selection):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar alias:
    :vartype alias: Optional[Name]

    :ivar name:
    :vartype name: Name

    :ivar arguments:
    :vartype arguments: List[Argument]

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar selection_set:
    :vartype selection_set: Optional[SelectionSet]
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
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name

    :ivar value:
    :vartype value: Value
    """

    __slots__ = ("source", "loc", "name", "value")


class FragmentSpread(Selection):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]
    """

    __slots__ = ("source", "loc", "name", "directives")
    __defaults__ = {"directives": []}


class InlineFragment(Selection):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar type_condition:
    :vartype type_condition: Type

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar selection_set:
    :vartype selection_set: SelectionSet
    """

    __slots__ = (
        "source",
        "loc",
        "type_condition",
        "directives",
        "selection_set",
    )
    __defaults__ = {"directives": []}


class FragmentDefinition(ExecutableDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name

    :ivar variable_definitions:
    :vartype variable_definitions: List[VariableDefinition]

    :ivar type_condition:
    :vartype type_condition: Type

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar selection_set:
    :vartype selection_set: SelectionSet
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
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: str
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value)


class FloatValue(Value):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: str
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value)


class StringValue(Value):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: str

    :ivar block:
    :vartype block: bool
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
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: bool
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value).lower()


class NullValue(Value):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    """

    def __str__(self):
        return "null"


class EnumValue(Value):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: str
    """

    __slots__ = ("source", "loc", "value")

    def __str__(self):
        return str(self.value)


class ListValue(Value):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar value:
    :vartype value: List[Value]
    """

    __slots__ = ("source", "loc", "values")


class ObjectValue(Value):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar fields:
    :vartype fields: List[ObjectField]
    """

    __slots__ = ("source", "loc", "fields")
    __defaults__ = {"fields": []}


class ObjectField(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name

    :ivar value:
    :vartype value: Value
    """

    __slots__ = ("source", "loc", "name", "value")


class Directive(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name

    :ivar arguments:
    :vartype arguments: List[Argument]
    """

    __slots__ = ("source", "loc", "name", "arguments")
    __defaults__ = {"arguments": []}


class Type(Node):
    pass


class NamedType(Type):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar name:
    :vartype name: Name
    """

    __slots__ = ("source", "loc", "name")


class ListType(Type):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar type:
    :vartype type: Type
    """

    __slots__ = ("source", "loc", "type")


class NonNullType(Type):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar type:
    :vartype type: Union[NamedType, ListType]
    """

    __slots__ = ("source", "loc", "type")


class TypeSystemDefinition(Definition):
    pass


class SchemaDefinition(TypeSystemDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar operation_types:
    :vartype operation_types: List[OperationTypeDefinition
    """

    __slots__ = ("source", "loc", "directives", "operation_types")
    __defaults__ = {"directives": [], "operation_types": []}


class OperationTypeDefinition(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar operation:
    :vartype operation: Name

    :ivar type:
    :vartype type: NamedTyp
    """

    __slots__ = ("source", "loc", "operation", "type")


class TypeDefinition(TypeSystemDefinition):
    pass


class ScalarTypeDefinition(TypeDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive
    """

    __slots__ = ("source", "loc", "description", "name", "directives")
    __defaults__ = {"directives": []}


class ObjectTypeDefinition(TypeDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar interfaces:
    :vartype interfaces: List[NamedType]

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar fields:
    :vartype fields: List[FieldDefinition]
    """

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
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar arguments:
    :vartype arguments: List[InputValueDefinition]

    :ivar type:
    :vartype type: NamedType

    :ivar directives:
    :vartype directives: List[Directive]
    """

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
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar type:
    :vartype type: NamedType

    :ivar default_value:
    :vartype default_value: Value

    :ivar directives:
    :vartype directives: List[Directive]
    """

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
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar fields:
    :vartype fields: List[FieldDefinition]
    """

    __slots__ = ("source", "loc", "description", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class UnionTypeDefinition(TypeDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar types:
    :vartype types: List[NamedType]

    :ivar directives:
    :vartype directives: List[Directive]
    """

    __slots__ = ("source", "loc", "description", "name", "directives", "types")
    __defaults__ = {"directives": [], "types": []}


class EnumTypeDefinition(TypeDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar values:
    :vartype values: List[EnumValueDefinition]
    """

    __slots__ = ("source", "loc", "description", "name", "directives", "values")
    __defaults__ = {"directives": [], "values": []}


class EnumValueDefinition(Node):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]
    """

    __slots__ = ("source", "loc", "description", "name", "directives")
    __defaults__ = {"directives": []}


class InputObjectTypeDefinition(TypeDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar fields:
    :vartype fields: List[InputValueDefinition]
    """

    __slots__ = ("source", "loc", "description", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class TypeExtension(TypeSystemDefinition):
    pass


class ScalarTypeExtension(TypeExtension):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]
    """

    __slots__ = ("source", "loc", "name", "directives")
    __defaults__ = {"directives": []}


class ObjectTypeExtension(TypeExtension):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar interfaces:
    :vartype interfaces: List[NamedType]

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar fields:
    :vartype fields: List[FieldDefinition]
    """

    __slots__ = ("source", "loc", "name", "interfaces", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class InterfaceTypeExtension(TypeExtension):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar fields:
    :vartype fields: List[FieldDefinition]
    """

    __slots__ = ("source", "loc", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class UnionTypeExtension(TypeExtension):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar types:
    :vartype types: List[NamedType]

    :ivar directives:
    :vartype directives: List[Directive]
    """

    __slots__ = ("source", "loc", "name", "directives", "types")
    __defaults__ = {"directives": [], "types": []}


class EnumTypeExtension(TypeExtension):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar values:
    :vartype values: List[EnumValueDefinition]
    """

    __slots__ = ("source", "loc", "name", "directives", "values")
    __defaults__ = {"directives": [], "values": []}


class InputObjectTypeExtension(TypeExtension):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar directives:
    :vartype directives: List[Directive]

    :ivar fields:
    :vartype fields: List[InputValueDefinition]
    """

    __slots__ = ("source", "loc", "name", "directives", "fields")
    __defaults__ = {"directives": [], "fields": []}


class DirectiveDefinition(TypeSystemDefinition):
    """
    :ivar loc: Location in the source
    :vartype loc: Tuple[int, int]

    :ivar source: Source document
    :vartype source: str

    :ivar description:
    :vartype description: StringValue

    :ivar name:
    :vartype name: Name

    :ivar arguments:
    :vartype arguments: List[InputValueDefinition]

    :ivar locations:
    :vartype locations: List[Name]
    """

    __slots__ = (
        "source",
        "loc",
        "description",
        "name",
        "arguments",
        "locations",
    )
    __defaults__ = {"arguments": [], "locations": []}


def node_to_dict(node):
    """ Recrusively convert a ``py_gql.lang.ast.Node`` instance to a dict.

    This is mostly useful for testing and when you need to convert nodes to JSON
    such as interop with other languages, printing and serialisation.

    Nodes are converted based on their `__slots__` adding a `__kind__` key
    corresponding to the node class while primitive values are left as is. Lists are
    converted per-element.

    :type node: any
    :param node: A :class:`Node` instance or any value used as a node attribute.

    :rtype: any
    :returns: Converted value
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
