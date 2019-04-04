# -*- coding: utf-8 -*-

import pytest

from py_gql.schema import (
    ID,
    Argument,
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

    Being = InterfaceType(
        "Being", [Field("name", String, [Argument("surname", Boolean)])]
    )

    Pet = InterfaceType(
        "Pet", [Field("name", String, [Argument("surname", Boolean)])]
    )

    Canine = InterfaceType(
        "Canine", [Field("name", String, [Argument("surname", Boolean)])]
    )

    DogCommand = EnumType(
        "DogCommand",
        [EnumValue("SIT", 0), EnumValue("HEEL", 1), EnumValue("DOWN", 2)],
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
            Field("name", String, args=[Argument("surname", Boolean)]),
            Field("nickname", String),
            Field("barkVolume", Int),
            Field("barks", Boolean),
            Field(
                "doesKnowCommand", Boolean, [Argument("dogCommand", DogCommand)]
            ),
            Field(
                "isHousetrained",
                Boolean,
                [Argument("atOtherHomes", Boolean, True)],
            ),
            Field(
                "isAtLocation",
                Boolean,
                [Argument("x", Int), Argument("y", Int)],
            ),
        ],
        [Being, Pet, Canine],
    )

    Cat = ObjectType(
        "Cat",
        [
            Field("name", String, args=[Argument("surname", Boolean)]),
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
            Field("name", String, args=[Argument("surname", Boolean)]),
            Field("iq", Int),
            Field("pets", ListType(Pet)),
            Field("relatives", ListType(Human)),
        ],
        [Being, Intelligent],
    )

    Alien = ObjectType(
        "Alien",
        [
            Field("name", String, args=[Argument("surname", Boolean)]),
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
            InputField(
                "nonNullField", NonNullType(Boolean), default_value=False
            ),
            InputField("intField", Int),
            InputField("stringField", String),
            InputField("booleanField", Boolean),
            InputField("stringListField", ListType(String)),
        ],
    )

    ComplicatedArgs = ObjectType(
        "ComplicatedArgs",
        [
            Field("intArgField", String, [Argument("intArg", Int)]),
            Field(
                "nonNullIntArgField",
                String,
                [Argument("nonNullIntArg", NonNullType(Int))],
            ),
            Field("stringArgField", String, [Argument("stringArg", String)]),
            Field("booleanArgField", String, [Argument("booleanArg", Boolean)]),
            Field("enumArgField", String, [Argument("enumArg", FurColor)]),
            Field("floatArgField", String, [Argument("floatArg", Float)]),
            Field("idArgField", String, [Argument("idArg", ID)]),
            Field(
                "stringListArgField",
                String,
                [Argument("stringListArg", ListType(String))],
            ),
            Field(
                "stringListNonNullArgField",
                String,
                [
                    Argument(
                        "stringListNonNullArg", ListType(NonNullType(String))
                    )
                ],
            ),
            Field(
                "complexArgField",
                String,
                [Argument("complexArg", ComplexInput)],
            ),
            Field(
                "multipleReqs",
                String,
                [
                    Argument("req1", NonNullType(Int)),
                    Argument("req2", NonNullType(Int)),
                ],
            ),
            Field(
                "nonNullFieldWithDefault",
                String,
                [Argument("arg", NonNullType(Int), default_value=0)],
            ),
            Field(
                "multipleOpts",
                String,
                [Argument("opt1", Int, 0), Argument("opt2", Int, 0)],
            ),
            Field(
                "multipleOptAndReq",
                String,
                [
                    Argument("req1", NonNullType(Int)),
                    Argument("req2", NonNullType(Int)),
                    Argument("opt1", Int, 0),
                    Argument("opt2", Int, 0),
                ],
            ),
        ],
    )

    def _invalid(*args, **kwargs):
        raise ValueError("Invalid scalar is always invalid")

    def _stringify(value):
        return str(value)

    InvalidScalar = ScalarType("Invalid", _stringify, _invalid, _invalid)
    AnyScalar = ScalarType("Any", _stringify, lambda x: x)  # type: ScalarType

    return Schema(
        ObjectType(
            "QueryRoot",
            [
                Field("human", Human, [Argument("id", ID)]),
                Field("alien", Alien),
                Field("dog", Dog),
                Field("cat", Cat),
                Field("pet", Pet),
                Field("catOrDog", CatOrDog),
                Field("dogOrHuman", DogOrHuman),
                Field("humanOrAlien", HumanOrAlien),
                Field("humanOrAlien", HumanOrAlien),
                Field("complicatedArgs", ComplicatedArgs),
                Field("invalidArg", String, [Argument("arg", InvalidScalar)]),
                Field("anydArg", String, [Argument("arg", AnyScalar)]),
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
        "SomeBox",
        [Field("deepBox", lambda: SomeBox), Field("unrelatedField", String)],
    )  # type: InterfaceType

    StringBox = ObjectType(
        "StringBox",
        [
            Field("scalar", String),
            Field("deepBox", lambda: StringBox),
            Field("unrelatedField", String),
            Field("listStringBox", lambda: ListType(StringBox)),
            Field("stringBox", lambda: StringBox),
            Field("intBox", lambda: IntBox),  # type: ignore
        ],
        [SomeBox],
    )  # type: ObjectType

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
    )  # type: ObjectType

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
                                    "Node",
                                    [Field("id", ID), Field("name", String)],
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
            "QueryRoot",
            [Field("someBox", SomeBox), Field("connection", Connection)],
        ),
        types=[IntBox, StringBox, NonNullStringBox1Impl, NonNullStringBox2Impl],
    )
