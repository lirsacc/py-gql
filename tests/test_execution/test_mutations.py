# -*- coding: utf-8 -*-
""" generic mutations handling tests """

import pytest

from py_gql.exc import ResolverError
from py_gql.schema import Argument, Field, Int, ObjectType, Schema

from ._test_utils import TESTED_EXECUTORS, check_execution


class NumberHolder(object):
    __slots__ = "theNumber"

    def __init__(self, original):
        self.theNumber = original


class Root(object):
    def __init__(self, original):
        self.numberHolder = NumberHolder(original)

    def incrementTheNumber(self, steps):
        self.numberHolder.theNumber = self.numberHolder.theNumber + steps
        return self.numberHolder

    def immediatelyChangeTheNumber(self, newNumber):
        self.numberHolder.theNumber = newNumber
        return self.numberHolder

    def failToChangeTheNumber(self, _new_number):
        raise ResolverError("Cannot change the number")


number_holder = ObjectType("NumberHolder", [Field("theNumber", Int)])

schema = Schema(
    ObjectType("Query", [Field("numberHolder", number_holder)]),
    ObjectType(
        "Mutation",
        [
            Field(
                "incrementTheNumber",
                number_holder,
                args=[Argument("steps", Int)],
                resolve=lambda obj, args, *_: obj.incrementTheNumber(
                    args["steps"]
                ),
            ),
            Field(
                "immediatelyChangeTheNumber",
                number_holder,
                args=[Argument("newNumber", Int)],
                resolve=lambda obj, args, *_: (
                    obj.immediatelyChangeTheNumber(args["newNumber"])
                ),
            ),
            Field(
                "failToChangeTheNumber",
                number_holder,
                args=[Argument("newNumber", Int)],
                resolve=lambda obj, args, *_: (
                    obj.failToChangeTheNumber(args["newNumber"])
                ),
            ),
        ],
    ),
)


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_it_evaluates_mutations_serially(exe_cls, exe_kwargs):
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            schema,
            """
            mutation M {
                first: immediatelyChangeTheNumber(newNumber: 1) {
                    theNumber
                },
                second: incrementTheNumber(steps: 1) {
                    theNumber
                },
                third: immediatelyChangeTheNumber(newNumber: 3) {
                    theNumber
                }
                fourth: incrementTheNumber(steps: -3) {
                    theNumber
                }
                fifth: immediatelyChangeTheNumber(newNumber: 5) {
                    theNumber
                }
            }
            """,
            initial_value=Root(6),
            expected_data={
                "first": {"theNumber": 1},
                "second": {"theNumber": 2},
                "third": {"theNumber": 3},
                "fourth": {"theNumber": 0},
                "fifth": {"theNumber": 5},
            },
            expected_errors=[],
            executor=executor,
        )


@pytest.mark.parametrize("exe_cls, exe_kwargs", TESTED_EXECUTORS)
def test_it_evaluates_mutations_correctly_even_when_some_mutation_fails(
    exe_cls, exe_kwargs
):

    doc = """
        mutation M {
            first: immediatelyChangeTheNumber(newNumber: 1) {
                theNumber
            },
            second: failToChangeTheNumber(newNumber: 3) {
                theNumber
            }
            third: incrementTheNumber(newNumber: 1, steps: 1) {
                theNumber
            }
            fourth: failToChangeTheNumber(newNumber: 6) {
                theNumber
            }
        }
    """
    with exe_cls(**exe_kwargs) as executor:
        check_execution(
            schema,
            doc,
            initial_value=Root(6),
            executor=executor,
            expected_data={
                "first": {"theNumber": 1},
                "second": None,
                "third": {"theNumber": 2},
                "fourth": None,
            },
            expected_errors=[
                ("Cannot change the number", (137, 222), "second"),
                ("Cannot change the number", (339, 424), "fourth"),
            ],
        )
