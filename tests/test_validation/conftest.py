# -*- coding: utf-8 -*-

import pytest

from py_gql.schema import (
    ID,
    Arg,
    Boolean,
    Directive,
    EnumType,
    EnumValue,
    Field,
    Float,
    InputField,
    InputObjectType,
    Int,
    InterfaceType,
    ListType,
    NonNullType,
    ObjectType,
    ScalarType,
    Schema,
    String,
    UnionType,
)


@pytest.fixture
def schema():

    Being = InterfaceType("Being", [Field("name", String, [Arg("surname", Boolean)])])

    Pet = InterfaceType("Pet", [Field("name", String, [Arg("surname", Boolean)])])

    Canine = InterfaceType("Canine", [Field("name", String, [Arg("surname", Boolean)])])

    DogCommand = EnumType(
        "DogCommand", [EnumValue("SIT", 0), EnumValue("HEEL", 1), EnumValue("DOWN", 2)]
    )

    FurColor = EnumType(
        "FurColor",
        [
            EnumValue("BROWN", 0),
            EnumValue("BLACK", 1),
            EnumValue("TAN", 2),
            EnumValue("SPOTTED", 3),
            EnumValue("NO_FUR", None),
            EnumValue("UNKNOWN", -1),
        ],
    )

    Dog = ObjectType(
        "Dog",
        [
            Field("name", String, args=[Arg("surname", Boolean)]),
            Field("nickname", String),
            Field("barkVolume", Int),
            Field("barks", Boolean),
            Field("doesKnowCommand", Boolean, [Arg("dogCommand", DogCommand)]),
            Field("isHousetrained", Boolean, [Arg("atOtherHomes", Boolean, True)]),
            Field("isAtLocation", Boolean, [Arg("x", Int), Arg("y", Int)]),
        ],
        [Being, Pet, Canine],
    )

    Cat = ObjectType(
        "Cat",
        [
            Field("name", String, args=[Arg("surname", Boolean)]),
            Field("nickname", String),
            Field("meowVolume", Int),
            Field("meows", Boolean),
            Field("furColor", FurColor),
        ],
        [Being, Pet],
    )

    CatOrDog = UnionType("CatOrDog", [Dog, Cat])

    Intelligent = InterfaceType("Intelligent", [Field("iq", Int)])

    Human = ObjectType(
        "Human",
        lambda: [
            Field("name", String, args=[Arg("surname", Boolean)]),
            Field("iq", Int),
            Field("pets", ListType(Pet)),
            Field("relatives", ListType(Human)),
        ],
        [Being, Intelligent],
    )

    Alien = ObjectType(
        "Alien",
        [
            Field("name", String, args=[Arg("surname", Boolean)]),
            Field("iq", Int),
            Field("numEyes", Int),
        ],
        [Being, Intelligent],
    )

    DogOrHuman = UnionType("DogOrHuman", [Dog, Human])

    HumanOrAlien = UnionType("HumanOrAlien", [Human, Alien])

    ComplexInput = InputObjectType(
        "ComplexInput",
        [
            InputField("requiredField", NonNullType(Boolean)),
            InputField("intField", Int),
            InputField("stringField", String),
            InputField("booleanField", Boolean),
            InputField("stringListField", ListType(String)),
        ],
    )

    ComplicatedArgs = ObjectType(
        "ComplicatedArgs",
        [
            Field("intArgField", String, [Arg("intArg", Int)]),
            Field(
                "nonNullIntArgField", String, [Arg("nonNullIntArg", NonNullType(Int))]
            ),
            Field("stringArgField", String, [Arg("stringArg", String)]),
            Field("booleanArgField", String, [Arg("booleanArg", Boolean)]),
            Field("enumArgField", String, [Arg("enumArg", FurColor)]),
            Field("floatArgField", String, [Arg("floatArg", Float)]),
            Field("idArgField", String, [Arg("idArg", ID)]),
            Field(
                "stringListArgField", String, [Arg("stringListArg", ListType(String))]
            ),
            Field(
                "stringListNonNullArgField",
                String,
                [Arg("stringListNonNullArg", ListType(NonNullType(String)))],
            ),
            Field("complexArgField", String, [Arg("complexArg", ComplexInput)]),
            Field(
                "multipleReqs",
                String,
                [Arg("req1", NonNullType(Int)), Arg("req2", NonNullType(Int))],
            ),
            Field("multipleOpts", String, [Arg("opt1", Int, 0), Arg("opt2", Int, 0)]),
            Field(
                "multipleOptAndReq",
                String,
                [
                    Arg("req1", NonNullType(Int)),
                    Arg("req2", NonNullType(Int)),
                    Arg("opt1", Int, 0),
                    Arg("opt2", Int, 0),
                ],
            ),
        ],
    )

    def _invalid(*args, **kwargs):
        raise ValueError("Invalid scalar is always invalid")

    InvalidScalar = ScalarType("Invalid", lambda x: x, _invalid, _invalid)
    AnyScalar = ScalarType("Any", lambda x: x, lambda x: x, lambda x: x)

    return Schema(
        ObjectType(
            "QueryRoot",
            [
                Field("human", Human, [Arg("id", ID)]),
                Field("alien", Alien),
                Field("dog", Dog),
                Field("cat", Cat),
                Field("pet", Pet),
                Field("catOrDog", CatOrDog),
                Field("dogOrHuman", DogOrHuman),
                Field("humanOrAlien", HumanOrAlien),
                Field("humanOrAlien", HumanOrAlien),
                Field("complicatedArgs", ComplicatedArgs),
                Field("invalidArg", String, [Arg("arg", InvalidScalar)]),
                Field("anydArg", String, [Arg("arg", AnyScalar)]),
            ],
        ),
        types=[Cat, Dog, Human, Alien],
        directives=[
            Directive("onQuery", ["QUERY"]),
            Directive("onMutation", ["MUTATION"]),
            Directive("onSubscription", ["SUBSCRIPTION"]),
            Directive("onField", ["FIELD"]),
            Directive("onFragmentDefinition", ["FRAGMENT_DEFINITION"]),
            Directive("onFragmentSpread", ["FRAGMENT_SPREAD"]),
            Directive("onInlineFragment", ["INLINE_FRAGMENT"]),
            Directive("onSchema", ["SCHEMA"]),
            Directive("onScalar", ["SCALAR"]),
            Directive("onObject", ["OBJECT"]),
            Directive("onFieldDefinition", ["FIELD_DEFINITION"]),
            Directive("onArgumentDefinition", ["ARGUMENT_DEFINITION"]),
            Directive("onInterface", ["INTERFACE"]),
            Directive("onUnion", ["UNION"]),
            Directive("onEnum", ["ENUM"]),
            Directive("onEnumValue", ["ENUM_VALUE"]),
            Directive("onInputObject", ["INPUT_OBJECT"]),
            Directive("onInputFieldDefinition", ["INPUT_FIELD_DEFINITION"]),
        ],
    )


@pytest.fixture
def schema_2():
    SomeBox = InterfaceType(
        "SomeBox", [Field("deepBox", lambda: SomeBox), Field("unrelatedField", String)]
    )

    StringBox = ObjectType(
        "StringBox",
        [
            Field("scalar", String),
            Field("deepBox", lambda: StringBox),
            Field("unrelatedField", String),
            Field("listStringBox", lambda: ListType(StringBox)),
            Field("stringBox", lambda: StringBox),
            Field("intBox", lambda: IntBox),
        ],
        [SomeBox],
    )

    IntBox = ObjectType(
        "IntBox",
        [
            Field("scalar", Int),
            Field("deepBox", lambda: IntBox),
            Field("unrelatedField", String),
            Field("listStringBox", lambda: ListType(StringBox)),
            Field("stringBox", lambda: StringBox),
            Field("intBox", lambda: IntBox),
        ],
        [SomeBox],
    )

    NonNullStringBox1 = InterfaceType(
        "NonNullStringBox1", [Field("scalar", NonNullType(String))]
    )

    NonNullStringBox1Impl = ObjectType(
        "NonNullStringBox1Impl",
        [
            Field("scalar", NonNullType(String)),
            Field("unrelatedField", String),
            Field("deepBox", SomeBox),
        ],
        [SomeBox, NonNullStringBox1],
    )

    NonNullStringBox2 = InterfaceType(
        "NonNullStringBox2", [Field("scalar", NonNullType(String))]
    )

    NonNullStringBox2Impl = ObjectType(
        "NonNullStringBox2Impl",
        [
            Field("scalar", NonNullType(String)),
            Field("unrelatedField", String),
            Field("deepBox", SomeBox),
        ],
        [SomeBox, NonNullStringBox2],
    )

    Connection = ObjectType(
        "Connection",
        [
            Field(
                "edges",
                ListType(
                    ObjectType(
                        "Edge",
                        [
                            Field(
                                "node",
                                ObjectType(
                                    "Node", [Field("id", ID), Field("name", String)]
                                ),
                            )
                        ],
                    )
                ),
            )
        ],
    )

    yield Schema(
        ObjectType(
            "QueryRoot", [Field("someBox", SomeBox), Field("connection", Connection)]
        ),
        types=[IntBox, StringBox, NonNullStringBox1Impl, NonNullStringBox2Impl],
    )
