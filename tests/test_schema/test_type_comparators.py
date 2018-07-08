# -*- coding: utf-8 -*-


from py_gql.schema.scalars import Float, Int, String
from py_gql.schema.schema import Schema
from py_gql.schema.types import (
    Field,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    UnionType,
)


def test_references_are_equal():
    assert String == String


def test_int_and_float_are_not_equal():
    assert not Int == Float


def test_lists_of_same_type_are_equal():
    assert ListType(Int) == ListType(Int)


def test_lists_is_not_equal_to_item():
    assert not ListType(Int) == Int


def test_non_null_of_same_type_are_equal():
    assert NonNullType(Int) == NonNullType(Int)


def test_non_null_is_not_equal_to_nullable():
    assert not NonNullType(Int) == Int


def test_non_null_is_not_equal_to_list():
    assert not NonNullType(Int) == ListType(Int)


_schema = Schema(ObjectType("Query", [Field("field", String)]))


def test_same_referaence_is_subtype():
    assert _schema.is_subtype(String, String)


def test_int_is_not_subtype_of_float():
    assert not _schema.is_subtype(Int, Float)


def test_non_null_is_subtype_of_nullable():
    assert _schema.is_subtype(NonNullType(Int), Int)


def test_nullable_is_not_subtype_of_non_null():
    assert not _schema.is_subtype(Int, NonNullType(Int))


def test_item_is_not_subtype_of_list():
    assert not _schema.is_subtype(Int, ListType(Int))


def test_list_is_not_subtype_of_item():
    assert not _schema.is_subtype(ListType(Int), Int)


def test_list_of_non_null_is_subtype_of_list_of_nullable():
    assert _schema.is_subtype(ListType(NonNullType(Int)), ListType(Int))


def test_member_is_subtype_of_union():
    member = ObjectType("Object", [Field("field", String)])
    union = UnionType("Union", [member])
    schema = Schema(ObjectType("Query", [Field("field", union)]))
    assert schema.is_subtype(member, union)


def test_not_member_is_not_subtype_of_union():
    member = ObjectType("Object", [Field("field", String)])
    not_member = ObjectType("Object2", [Field("field", String)])
    union = UnionType("Union", [member])
    schema = Schema(ObjectType("Query", [Field("field", union)]))
    assert not schema.is_subtype(not_member, union)


def test_implementation_is_subtype_of_interface():
    iface = InterfaceType("Iface", [Field("field", String)])
    impl = ObjectType("Object", [Field("field", String)], [iface])
    schema = Schema(ObjectType("Query", [Field("field", impl)]))
    assert schema.is_subtype(impl, iface)


def test_not_implementation_is_not_subtype_of_interface():
    iface = InterfaceType("Iface", [Field("field", String)])
    impl = ObjectType("Object", [Field("field", String)])
    schema = Schema(ObjectType("Query", [Field("field", impl)]))
    assert not schema.is_subtype(impl, iface)


def test_references_overlap():
    assert _schema.types_overlap(Int, Int)


def test_int_and_float_do_not_overlap():
    assert not _schema.types_overlap(Int, Float)


def test_disjoint_unions_do_not_overlap():
    member1 = ObjectType("Object1", [Field("field", String)])
    member2 = ObjectType("Object2", [Field("field", String)])
    union1 = UnionType("Union1", [member2])
    union2 = UnionType("Union2", [member1])
    schema = Schema(
        ObjectType("Query", [Field("field1", union1), Field("field2", union2)])
    )
    assert not schema.types_overlap(union1, union2)


def test_common_unions_not_overlap():
    member1 = ObjectType("Object1", [Field("field", String)])
    member2 = ObjectType("Object2", [Field("field", String)])
    union1 = UnionType("Union1", [member2])
    union2 = UnionType("Union2", [member1, member2])
    schema = Schema(
        ObjectType("Query", [Field("field1", union1), Field("field2", union2)])
    )
    assert schema.types_overlap(union1, union2)


def test_union_and_interface_with_common_types_overlap():
    iface = InterfaceType("Iface", [Field("field", String)])
    impl = ObjectType("Object", [Field("field", String)], [iface])
    union = UnionType("Union", [impl])
    schema = Schema(
        ObjectType("Query", [Field("field1", union), Field("field2", iface)])
    )
    assert schema.types_overlap(iface, union)
