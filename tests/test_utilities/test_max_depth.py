# -*- coding: utf-8 -*-

import pytest

from py_gql.lang import ast, parse
from py_gql.utilities import MaxDepthValidationRule

MULTIPLE_OPERATIONS = """
query ShallowQuery {
    hero {
        friends {
            name
        }
    }
}

query DeepQuery {
    hero {
        friends {
            friends {
                friends {
                    friends {
                        friends {
                            friends {
                                name
                            }
                        }
                    }
                }
            }
        }
    }
}

query ShallowFragmentQuery { hero { ... getShallowFriends } }

query DeepFragmentQuery { hero { ... getDeepFriends } }

fragment getShallowFriends on Character {
    friends {
        name
    }
}

fragment getDeepFriends on Character {
    friends {
        friends {
            friends {
                friends {
                    friends {
                        friends {
                            name
                        }
                    }
                }
            }
        }
    }
}
"""

SHALLOW_QUERY = """
{
    hero {
        name
        friends {
            name
        }
    }
}
"""

DEEP_QUERY = """
{
    hero {
        name
        friends {
            name {
                friends {
                    friends {
                        friends {
                            name
                        }
                    }
                }
            }
        }
    }
}
"""


def case(id, *args):
    return pytest.param(*args, id=id)


@pytest.mark.parametrize(
    "doc, kwargs, expected_errors",
    [
        case(
            "Shallow single query doesn't have errors",
            SHALLOW_QUERY,
            {"max_depth": 5},
            [],
        ),
        case(
            "Deep single query has errors",
            DEEP_QUERY,
            {"max_depth": 5},
            ['Operation "<ANONYMOUS>" depth (6) exceeds maximum depth (5)'],
        ),
        case(
            "Multiple operation without operation name has multiple errors",
            MULTIPLE_OPERATIONS,
            {"max_depth": 5},
            [
                'Operation "DeepQuery" depth (7) exceeds maximum depth (5)',
                'Operation "DeepFragmentQuery" depth (7) exceeds maximum depth (5)',
            ],
        ),
        case(
            "Multiple operation with matching operation name (deep) has 1 error",
            MULTIPLE_OPERATIONS,
            {"max_depth": 5, "operation_name": "DeepQuery"},
            ['Operation "DeepQuery" depth (7) exceeds maximum depth (5)'],
        ),
        case(
            "Multiple operation with matching operation name (shallow) has 0 error",
            MULTIPLE_OPERATIONS,
            {"max_depth": 5, "operation_name": "ShallowQuery"},
            [],
        ),
        case(
            "Multiple operation with missing operation name has 0 error",
            MULTIPLE_OPERATIONS,
            {"max_depth": 5, "operation_name": "Foo"},
            [],
        ),
    ],
)
def test(starwars_schema, doc, kwargs, expected_errors):
    rule = MaxDepthValidationRule(**kwargs)
    errors = rule(starwars_schema, parse(doc))
    assert [e.message for e in errors] == expected_errors


def test_errors_point_to_the_correct_operation_node(starwars_schema):
    rule = MaxDepthValidationRule(5)
    doc = parse(MULTIPLE_OPERATIONS)
    errors = rule(starwars_schema, doc)

    ops = [o for o in doc.definitions if isinstance(o, ast.OperationDefinition)]

    assert errors[0].nodes == [ops[1]]
    assert errors[1].nodes == [ops[3]]
