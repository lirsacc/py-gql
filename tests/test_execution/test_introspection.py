# -*- coding: utf-8 -*-
# flake8: noqa
""" tests related to introspection queries """

import json

from py_gql.schema import (
    Argument,
    EnumType,
    EnumValue,
    Field,
    InputField,
    InputObjectType,
    ListType,
    ObjectType,
    Schema,
    String,
)
from py_gql.utilities import introspection_query

from ._test_utils import assert_sync_execution

# Star Wars schema related tests. These are simpler than other tests down
# this file and should be easier to debug if something breaks while
# the others are supposed to cover more ground.


def test_allows_querying_the_schema_for_types(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionTypeQuery {
        __schema {
            types { name }
        }
    }
    """,
        {
            "__schema": {
                "types": [
                    {"name": "Boolean"},
                    {"name": "Character"},
                    {"name": "Droid"},
                    {"name": "Episode"},
                    {"name": "Float"},
                    {"name": "Human"},
                    {"name": "ID"},
                    {"name": "Int"},
                    {"name": "Query"},
                    {"name": "String"},
                    {"name": "__Directive"},
                    {"name": "__DirectiveLocation"},
                    {"name": "__EnumValue"},
                    {"name": "__Field"},
                    {"name": "__InputValue"},
                    {"name": "__Schema"},
                    {"name": "__Type"},
                    {"name": "__TypeKind"},
                ]
            }
        },
        [],
    )


def test_allows_querying_the_schema_for_query_type(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionQueryTypeQuery {
        __schema {
            queryType {
                name
            }
        }
    }
    """,
        {"__schema": {"queryType": {"name": "Query"}}},
        [],
    )


def test_allows_querying_the_schema_for_a_specific_type(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionDroidTypeQuery {
        __type(name: "Droid") {
           name
        }
    }
    """,
        {"__type": {"name": "Droid"}},
        [],
    )


def test_allows_querying_the_schema_for_an_object_kind(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionDroidKindQuery {
        __type(name: "Droid") {
            name
            kind
        }
    }
    """,
        {"__type": {"name": "Droid", "kind": "OBJECT"}},
        [],
    )


def test_allows_querying_the_schema_for_an_interface_kind(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionCharacterKindQuery {
        __type(name: "Character") {
            name
           kind
        }
    }
    """,
        {"__type": {"name": "Character", "kind": "INTERFACE"}},
        [],
    )


def test_allows_querying_the_schema_for_object_fields(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
     query IntrospectionDroidFieldsQuery {
        __type(name: "Droid") {
            name
            fields {
                name
                type {
                    name
                   kind
                }
            }
        }
    }
    """,
        {
            "__type": {
                "name": "Droid",
                "fields": [
                    {"name": "id", "type": {"name": None, "kind": "NON_NULL"}},
                    {
                        "name": "name",
                        "type": {"name": "String", "kind": "SCALAR"},
                    },
                    {"name": "friends", "type": {"name": None, "kind": "LIST"}},
                    {
                        "name": "appearsIn",
                        "type": {"name": None, "kind": "LIST"},
                    },
                    {
                        "name": "secretBackstory",
                        "type": {"name": "String", "kind": "SCALAR"},
                    },
                    {
                        "name": "primaryFunction",
                        "type": {"name": "String", "kind": "SCALAR"},
                    },
                ],
            }
        },
        [],
    )


def test_allows_querying_the_schema_for_nested_object_fields(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionDroidNestedFieldsQuery {
        __type(name: "Droid") {
            name
            fields {
                name
                type {
                    name
                    kind
                    ofType {
                        name
                        kind
                    }
                }
            }
        }
    }
    """,
        {
            "__type": {
                "fields": [
                    {
                        "name": "id",
                        "type": {
                            "kind": "NON_NULL",
                            "name": None,
                            "ofType": {"kind": "SCALAR", "name": "String"},
                        },
                    },
                    {
                        "name": "name",
                        "type": {
                            "kind": "SCALAR",
                            "name": "String",
                            "ofType": None,
                        },
                    },
                    {
                        "name": "friends",
                        "type": {
                            "kind": "LIST",
                            "name": None,
                            "ofType": {
                                "kind": "INTERFACE",
                                "name": "Character",
                            },
                        },
                    },
                    {
                        "name": "appearsIn",
                        "type": {
                            "kind": "LIST",
                            "name": None,
                            "ofType": {"kind": "ENUM", "name": "Episode"},
                        },
                    },
                    {
                        "name": "secretBackstory",
                        "type": {
                            "kind": "SCALAR",
                            "name": "String",
                            "ofType": None,
                        },
                    },
                    {
                        "name": "primaryFunction",
                        "type": {
                            "kind": "SCALAR",
                            "name": "String",
                            "ofType": None,
                        },
                    },
                ],
                "name": "Droid",
            }
        },
        [],
    )


def test_allows_querying_the_schema_for_field_args(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionQueryTypeQuery {
        __schema {
            queryType {
                fields {
                   name
                    args {
                        name
                        description
                        type {
                            name
                            kind
                            ofType {
                                name
                                kind
                            }
                        }
                        defaultValue
                    }
                }
            }
        }
    }
    """,
        {
            "__schema": {
                "queryType": {
                    "fields": [
                        {
                            "args": [
                                {
                                    "defaultValue": None,
                                    "description": "If omitted, returns the hero of the whole saga. "  # noqa: B950
                                    "If provided, returns the hero of that particular "
                                    "episode.",
                                    "name": "episode",
                                    "type": {
                                        "kind": "ENUM",
                                        "name": "Episode",
                                        "ofType": None,
                                    },
                                }
                            ],
                            "name": "hero",
                        },
                        {
                            "args": [
                                {
                                    "defaultValue": None,
                                    "description": "Id of the human",
                                    "name": "id",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "SCALAR",
                                            "name": "String",
                                        },
                                    },
                                }
                            ],
                            "name": "human",
                        },
                        {
                            "args": [
                                {
                                    "defaultValue": None,
                                    "description": "Id of the droid",
                                    "name": "id",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "SCALAR",
                                            "name": "String",
                                        },
                                    },
                                }
                            ],
                            "name": "droid",
                        },
                    ]
                }
            }
        },
        [],
    )


def test_allows_querying_the_schema_for_documentation(starwars_schema):
    assert_sync_execution(
        starwars_schema,
        """
    query IntrospectionDroidDescriptionQuery {
        __type(name: "Droid") {
            name
           description
        }
    }
    """,
        {
            "__type": {
                "name": "Droid",
                "description": "A mechanical creature in the Star Wars universe.",
            }
        },
        [],
    )


def test_intropsection_query():
    empty_schema = Schema(ObjectType("QueryRoot", [Field("onlyField", String)]))

    assert_sync_execution(
        empty_schema,
        introspection_query(False),
        expected_data={
            "__schema": {
                "mutationType": None,
                "subscriptionType": None,
                "queryType": {"name": "QueryRoot"},
                "types": [
                    {
                        "enumValues": None,
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "SCALAR",
                        "name": "Boolean",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "SCALAR",
                        "name": "Float",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "SCALAR",
                        "name": "ID",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "SCALAR",
                        "name": "Int",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "onlyField",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            }
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "QueryRoot",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "SCALAR",
                        "name": "String",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "name",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "String",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "description",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "locations",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "LIST",
                                        "name": None,
                                        "ofType": {
                                            "kind": "NON_NULL",
                                            "name": None,
                                            "ofType": {
                                                "kind": "ENUM",
                                                "name": "__DirectiveLocation",
                                                "ofType": None,
                                            },
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "args",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "LIST",
                                        "name": None,
                                        "ofType": {
                                            "kind": "NON_NULL",
                                            "name": None,
                                            "ofType": {
                                                "kind": "OBJECT",
                                                "name": "__InputValue",
                                                "ofType": None,
                                            },
                                        },
                                    },
                                },
                            },
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "__Directive",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": [
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "QUERY",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "MUTATION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "SUBSCRIPTION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "FIELD",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "FRAGMENT_DEFINITION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "FRAGMENT_SPREAD",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "INLINE_FRAGMENT",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "SCHEMA",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "SCALAR",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "OBJECT",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "FIELD_DEFINITION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "ARGUMENT_DEFINITION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "INTERFACE",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "UNION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "ENUM",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "ENUM_VALUE",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "INPUT_OBJECT",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "INPUT_FIELD_DEFINITION",
                            },
                        ],
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "ENUM",
                        "name": "__DirectiveLocation",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "name",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "String",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "description",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "isDeprecated",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "Boolean",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "deprecationReason",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "__EnumValue",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "name",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "String",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "description",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "args",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "LIST",
                                        "name": None,
                                        "ofType": {
                                            "kind": "NON_NULL",
                                            "name": None,
                                            "ofType": {
                                                "kind": "OBJECT",
                                                "name": "__InputValue",
                                                "ofType": None,
                                            },
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "type",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "OBJECT",
                                        "name": "__Type",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "isDeprecated",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "Boolean",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "deprecationReason",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "__Field",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "name",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "String",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "description",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "type",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "OBJECT",
                                        "name": "__Type",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "defaultValue",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "__InputValue",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "types",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "LIST",
                                        "name": None,
                                        "ofType": {
                                            "kind": "NON_NULL",
                                            "name": None,
                                            "ofType": {
                                                "kind": "OBJECT",
                                                "name": "__Type",
                                                "ofType": None,
                                            },
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "queryType",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "OBJECT",
                                        "name": "__Type",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "mutationType",
                                "type": {
                                    "kind": "OBJECT",
                                    "name": "__Type",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "subscriptionType",
                                "type": {
                                    "kind": "OBJECT",
                                    "name": "__Type",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "directives",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "LIST",
                                        "name": None,
                                        "ofType": {
                                            "kind": "NON_NULL",
                                            "name": None,
                                            "ofType": {
                                                "kind": "OBJECT",
                                                "name": "__Directive",
                                                "ofType": None,
                                            },
                                        },
                                    },
                                },
                            },
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "__Schema",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": None,
                        "fields": [
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "kind",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "ENUM",
                                        "name": "__TypeKind",
                                        "ofType": None,
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "name",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "description",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            },
                            {
                                "args": [
                                    {
                                        "defaultValue": "false",
                                        "name": "includeDeprecated",
                                        "type": {
                                            "kind": "SCALAR",
                                            "name": "Boolean",
                                            "ofType": None,
                                        },
                                    }
                                ],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "fields",
                                "type": {
                                    "kind": "LIST",
                                    "name": None,
                                    "ofType": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "OBJECT",
                                            "name": "__Field",
                                            "ofType": None,
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "interfaces",
                                "type": {
                                    "kind": "LIST",
                                    "name": None,
                                    "ofType": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "OBJECT",
                                            "name": "__Type",
                                            "ofType": None,
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "possibleTypes",
                                "type": {
                                    "kind": "LIST",
                                    "name": None,
                                    "ofType": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "OBJECT",
                                            "name": "__Type",
                                            "ofType": None,
                                        },
                                    },
                                },
                            },
                            {
                                "args": [
                                    {
                                        "defaultValue": "false",
                                        "name": "includeDeprecated",
                                        "type": {
                                            "kind": "SCALAR",
                                            "name": "Boolean",
                                            "ofType": None,
                                        },
                                    }
                                ],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "enumValues",
                                "type": {
                                    "kind": "LIST",
                                    "name": None,
                                    "ofType": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "OBJECT",
                                            "name": "__EnumValue",
                                            "ofType": None,
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "inputFields",
                                "type": {
                                    "kind": "LIST",
                                    "name": None,
                                    "ofType": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {
                                            "kind": "OBJECT",
                                            "name": "__InputValue",
                                            "ofType": None,
                                        },
                                    },
                                },
                            },
                            {
                                "args": [],
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "ofType",
                                "type": {
                                    "kind": "OBJECT",
                                    "name": "__Type",
                                    "ofType": None,
                                },
                            },
                        ],
                        "inputFields": None,
                        "interfaces": [],
                        "kind": "OBJECT",
                        "name": "__Type",
                        "possibleTypes": None,
                    },
                    {
                        "enumValues": [
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "SCALAR",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "OBJECT",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "INTERFACE",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "UNION",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "ENUM",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "INPUT_OBJECT",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "LIST",
                            },
                            {
                                "deprecationReason": None,
                                "isDeprecated": False,
                                "name": "NON_NULL",
                            },
                        ],
                        "fields": None,
                        "inputFields": None,
                        "interfaces": None,
                        "kind": "ENUM",
                        "name": "__TypeKind",
                        "possibleTypes": None,
                    },
                ],
                "directives": [
                    {
                        "name": "deprecated",
                        "locations": ["FIELD_DEFINITION", "ENUM_VALUE"],
                        "args": [
                            {
                                "defaultValue": '"No longer supported"',
                                "name": "reason",
                                "type": {
                                    "kind": "SCALAR",
                                    "name": "String",
                                    "ofType": None,
                                },
                            }
                        ],
                    },
                    {
                        "name": "include",
                        "locations": [
                            "FIELD",
                            "FRAGMENT_SPREAD",
                            "INLINE_FRAGMENT",
                        ],
                        "args": [
                            {
                                "defaultValue": None,
                                "name": "if",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "Boolean",
                                        "ofType": None,
                                    },
                                },
                            }
                        ],
                    },
                    {
                        "name": "skip",
                        "locations": [
                            "FIELD",
                            "FRAGMENT_SPREAD",
                            "INLINE_FRAGMENT",
                        ],
                        "args": [
                            {
                                "defaultValue": None,
                                "name": "if",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {
                                        "kind": "SCALAR",
                                        "name": "Boolean",
                                        "ofType": None,
                                    },
                                },
                            }
                        ],
                    },
                ],
            }
        },
        expected_errors=[],
    )


def test_intropsection_on_input_object():
    test_input = InputObjectType(
        "TestInputObject",
        [
            InputField("a", String, default_value="tes\t de\fault"),
            InputField("b", ListType(String)),
            InputField("c", String, default_value=None),
        ],
    )

    test_type = ObjectType(
        "TestType",
        [
            Field(
                "field",
                String,
                [Argument("complex", test_input)],
                resolver=lambda _, args, *__: json.dumps(args.get("complex")),
            )
        ],
    )

    schema = Schema(test_type)

    assert_sync_execution(
        schema,
        """
    {
        __type(name: "TestInputObject") {
            kind
            name
            inputFields {
                name
                type { ...TypeRef }
                defaultValue
            }
        }
    }

    fragment TypeRef on __Type {
        kind
        name
        ofType {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                }
            }
        }
    }
    """,
        expected_data={
            "__type": {
                "inputFields": [
                    {
                        "defaultValue": '"tes\t de\x0cault"',
                        "name": "a",
                        "type": {
                            "kind": "SCALAR",
                            "name": "String",
                            "ofType": None,
                        },
                    },
                    {
                        "defaultValue": None,
                        "name": "b",
                        "type": {
                            "kind": "LIST",
                            "name": None,
                            "ofType": {
                                "kind": "SCALAR",
                                "name": "String",
                                "ofType": None,
                            },
                        },
                    },
                    {
                        "defaultValue": "null",
                        "name": "c",
                        "type": {
                            "kind": "SCALAR",
                            "name": "String",
                            "ofType": None,
                        },
                    },
                ],
                "kind": "INPUT_OBJECT",
                "name": "TestInputObject",
            }
        },
        expected_errors=[],
    )


def test_it_supports_the_type_root_field():
    test_type = ObjectType("TestType", [Field("testField", String)])
    schema = Schema(test_type)
    assert_sync_execution(
        schema,
        """
    {
        __type(name: "TestType") {
            name
        }
    }
    """,
        expected_data={"__type": {"name": "TestType"}},
        expected_errors=[],
    )


def test_it_identifies_deprecated_fields():
    test_type = ObjectType(
        "TestType",
        [
            Field("nonDeprecated", String),
            Field("deprecated", String, deprecation_reason="Removed in 1.0"),
        ],
    )
    schema = Schema(test_type)

    assert_sync_execution(
        schema,
        """
    {
        __type(name: "TestType") {
            name
            fields(includeDeprecated: true) {
                name
                isDeprecated,
               deprecationReason
            }
        }
    }
    """,
        expected_data={
            "__type": {
                "name": "TestType",
                "fields": [
                    {
                        "name": "nonDeprecated",
                        "isDeprecated": False,
                        "deprecationReason": None,
                    },
                    {
                        "name": "deprecated",
                        "isDeprecated": True,
                        "deprecationReason": "Removed in 1.0",
                    },
                ],
            }
        },
        expected_errors=[],
    )


def test_it_respects_the_include_deprecated_parameter_for_fields():
    test_type = ObjectType(
        "TestType",
        [
            Field("nonDeprecated", String),
            Field("deprecated", String, deprecation_reason="Removed in 1.0"),
        ],
    )
    schema = Schema(test_type)

    assert_sync_execution(
        schema,
        """
    {
        __type(name: "TestType") {
            name
            fields {
                name
                isDeprecated,
               deprecationReason
            }
        }
    }
    """,
        expected_data={
            "__type": {
                "name": "TestType",
                "fields": [
                    {
                        "name": "nonDeprecated",
                        "isDeprecated": False,
                        "deprecationReason": None,
                    }
                ],
            }
        },
        expected_errors=[],
    )


def test_it_identifies_deprecated_enum_values():
    test_enum = EnumType(
        "TestEnum",
        [
            EnumValue("NONDEPRECATED", 0),
            EnumValue("DEPRECATED", 1, "Removed in 1.0"),
            EnumValue("ALSONONDEPRECATED", 2),
        ],
    )
    test_type = ObjectType("TestType", [Field("testEnum", test_enum)])
    schema = Schema(test_type)

    assert_sync_execution(
        schema,
        """
    {
        __type(name: "TestEnum") {
            name
            enumValues(includeDeprecated: true) {
                name
                isDeprecated,
                deprecationReason
            }
        }
    }
    """,
        {
            "__type": {
                "enumValues": [
                    {
                        "deprecationReason": None,
                        "isDeprecated": False,
                        "name": "NONDEPRECATED",
                    },
                    {
                        "deprecationReason": "Removed in 1.0",
                        "isDeprecated": True,
                        "name": "DEPRECATED",
                    },
                    {
                        "deprecationReason": None,
                        "isDeprecated": False,
                        "name": "ALSONONDEPRECATED",
                    },
                ],
                "name": "TestEnum",
            }
        },
        [],
    )


def test_it_respects_the_include_deprecated_parameter_for_enum_values():
    test_enum = EnumType(
        "TestEnum",
        [
            EnumValue("NONDEPRECATED", 0),
            EnumValue("DEPRECATED", 1, "Removed in 1.0"),
            EnumValue("ALSONONDEPRECATED", 2),
        ],
    )
    test_type = ObjectType("TestType", [Field("testEnum", test_enum)])
    schema = Schema(test_type)

    assert_sync_execution(
        schema,
        """
    {
        __type(name: "TestEnum") {
            name
            enumValues(includeDeprecated: false) {
                name
                isDeprecated,
                deprecationReason
            }
        }
    }
    """,
        {
            "__type": {
                "enumValues": [
                    {
                        "deprecationReason": None,
                        "isDeprecated": False,
                        "name": "NONDEPRECATED",
                    },
                    {
                        "deprecationReason": None,
                        "isDeprecated": False,
                        "name": "ALSONONDEPRECATED",
                    },
                ],
                "name": "TestEnum",
            }
        },
        [],
    )


def test_it_fails_as_expected_on_the_type_root_field_without_an_arg():
    test_type = ObjectType("TestType", [Field("testField", String)])
    schema = Schema(test_type)
    assert_sync_execution(
        schema,
        "{ __type { name } }",
        expected_data={"__type": None},
        expected_errors=[
            (
                'Argument "name" of required type "String!" was not provided',
                (2, 17),
                "__type",
            )
        ],
    )


def test_it_exposes_descriptions_on_types_and_fields():
    schema = Schema(ObjectType("QueryRoot", [Field("onlyField", String)]))
    assert_sync_execution(
        schema,
        """
    {
        schemaType: __type(name: "__Schema") {
            name,
            description,
            fields { name, description }
        }
    }
    """,
        {
            "schemaType": {
                "name": "__Schema",
                "description": "A GraphQL Schema defines the capabilities of a "
                "GraphQL server. It exposes all available types and "
                "directives on the server, as well as the entry "
                "points for query, mutation, "
                "and subscription operations.",
                "fields": [
                    {
                        "name": "types",
                        "description": "A list of all types supported by this server.",
                    },
                    {
                        "name": "queryType",
                        "description": "The type that query operations will be rooted at.",
                    },
                    {
                        "name": "mutationType",
                        "description": "If this server supports mutation, the type that "
                        "mutation operations will be rooted at.",
                    },
                    {
                        "name": "subscriptionType",
                        "description": "If this server supports subscription, the type "
                        "that subscription operations will be rooted at.",
                    },
                    {
                        "name": "directives",
                        "description": "A list of all directives supported by this server.",
                    },
                ],
            }
        },
        [],
    )


def test_it_exposes_descriptions_on_enums():
    schema = Schema(ObjectType("QueryRoot", [Field("onlyField", String)]))
    assert_sync_execution(
        schema,
        """
    {
        typeKindType: __type(name: "__TypeKind") {
            name,
            description,
            enumValues {
                name,
                description
            }
        }
    }
    """,
        {
            "typeKindType": {
                "description": "An enum describing what kind of type a given `__Type` is.",
                "enumValues": [
                    {
                        "description": "Indicates this type is a scalar.",
                        "name": "SCALAR",
                    },
                    {
                        "description": "Indicates this type is an object. `fields` and "
                        "`interfaces` are valid fields.",
                        "name": "OBJECT",
                    },
                    {
                        "description": "Indicates this type is an interface. `fields` and "
                        "`possibleTypes` are valid fields.",
                        "name": "INTERFACE",
                    },
                    {
                        "description": "Indicates this type is a union. `possibleTypes` is a "
                        "valid field.",
                        "name": "UNION",
                    },
                    {
                        "description": "Indicates this type is an enum. `enumValues` is a "
                        "valid field.",
                        "name": "ENUM",
                    },
                    {
                        "description": "Indicates this type is an input object. `inputFields` "
                        "is a valid field.",
                        "name": "INPUT_OBJECT",
                    },
                    {
                        "description": "Indicates this type is a list. `ofType` is a valid field.",
                        "name": "LIST",
                    },
                    {
                        "description": "Indicates this type is a non-null. `ofType` is a "
                        "valid field.",
                        "name": "NON_NULL",
                    },
                ],
                "name": "__TypeKind",
            }
        },
        [],
    )
