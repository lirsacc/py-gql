# -*- coding: utf-8 -*-

# As long as https://github.com/cython/cython/issues/2753 is open Generic[...]
# break when cythonized.
# This file isolates some non performance critical base types used for type
# checking but excluded from cythonization.

# These types should usually not be imported from here but from the types.py
# file located in the same folder.

from typing import Any, Generic, Optional, TypeVar

from .._utils import Lazy, lazy
from ..lang import ast


TGraphQLType = TypeVar("TGraphQLType", bound="GraphQLType")


class GraphQLType:
    """
    Base type class.

    All types used in a :class:`py_gql.schema.Schema` should be instances of
    this class.
    """

    def __eq__(self, lhs: Any) -> bool:
        return self is lhs or (
            isinstance(self, (WrappingType))
            and self.__class__ == lhs.__class__
            and self.type == lhs.type
        )

    def __hash__(self) -> int:
        return id(self)

    def as_list(self: TGraphQLType) -> "ListType[TGraphQLType]":
        """
        Return current type wrapped as a list type.
        """
        return ListType(self)

    def as_non_null(self: TGraphQLType) -> "NonNullType[TGraphQLType]":
        """
        Return current type wrapped as a non nullable type.
        """
        return NonNullType(self)


class NamedType(GraphQLType):
    """
    Named type base class.

    Warning:
        Named types must be unique across a single :class:`~py_gql.schema.Schema`
        instance.

    Attributes:
        name (str): Type name.
    """

    name = NotImplemented  # type: str

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, self.name)


class WrappingType(GraphQLType, Generic[TGraphQLType]):
    def __init__(self, type_: Lazy[TGraphQLType]):
        self._ltype = type_
        self._type = None  # type: Optional[TGraphQLType]

    @property
    def type(self) -> TGraphQLType:
        if self._type is None:
            self._type = lazy(self._ltype)
        return self._type

    @type.setter
    def type(self, type_: TGraphQLType) -> None:
        self._type = self._ltype = type_


class NonNullType(WrappingType[TGraphQLType]):
    """
    Non nullable wrapping type.

    A non-null type is a wrapping type which points to another type.

    Non-null types enforce that their values are never null and can ensure
    an error is raised if this ever occurs during a request. It is useful for
    fields which you can make a strong guarantee on non-nullability, for example
    usually the id field of a database row will never be null.

    Args:
        type_: Wrapped type
        node: Source node used when building type from the SDL

    Attributes:
        type (GraphQLType): Wrapped type
        node (Optional[py_gql.lang.ast.NonNullType]):
            Source node used when building type from the SDL

    """

    __slots__ = ("node", "_ltype", "_type")

    def __init__(
        self, type_: Lazy[TGraphQLType], node: Optional[ast.NonNullType] = None
    ):
        if isinstance(type_, NonNullType):
            raise ValueError("Cannot wrap NonNullType twice")

        super().__init__(type_)
        self.node = node

    def __str__(self) -> str:
        return "%s!" % self.type


class ListType(WrappingType[TGraphQLType]):
    """
    List wrapping type.

    A list type is a wrapping type which points to another type.

    Lists are often created within the context of defining the fields of
    an object type.

    Args:
        type_: Wrapped type
        node: Source node used when building type from the SDL

    Attributes:
        type (GraphQLType): Wrapped type
        node (Optional[py_gql.lang.ast.ListType]):
            Source node used when building type from the SDL
    """

    __slots__ = ("node", "_ltype", "_type")

    def __init__(
        self, type_: Lazy[TGraphQLType], node: Optional[ast.ListType] = None
    ):
        super().__init__(type_)
        self.node = node

    def __str__(self):
        return "[%s]" % self.type
