# -*- coding: utf-8 -*-
""" generic mutations handling tests """

import pytest

from py_gql.exc import ResolverError
from py_gql.schema import Argument, Field, Int, ObjectType, Schema

from ._test_utils import assert_execution

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class NumberHolder:
    __slots__ = "theNumber"

    def __init__(self, original):
        self.theNumber = original


class Root:
    def __init__(self, original):
        self.numberHolder = NumberHolder(original)

    def incrementTheNumber(self, steps):
        self.numberHolder.theNumber = self.numberHolder.theNumber + steps
        return self.numberHolder

    def changeTheNumber(self, newNumber):
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
                resolver=lambda obj, *_, **args: obj.incrementTheNumber(
                    args["steps"]
                ),
            ),
            Field(
                "changeTheNumber",
                number_holder,
                args=[Argument("newNumber", Int)],
                resolver=lambda obj, *_, **args: (
                    obj.changeTheNumber(args["newNumber"])
                ),
            ),
            Field(
                "failToChangeTheNumber",
                number_holder,
                args=[Argument("newNumber", Int)],
                resolver=lambda obj, *_, **args: (
                    obj.failToChangeTheNumber(args["newNumber"])
                ),
            ),
        ],
    ),
)


async def test_it_evaluates_mutations_serially(executor_cls):
    await assert_execution(
        schema,
        """
        mutation M {
            first: changeTheNumber(newNumber: 1) { theNumber }
            second: incrementTheNumber(steps: 1) { theNumber }
            third: changeTheNumber(newNumber: 3) { theNumber }
            fourth: incrementTheNumber(steps: -3) { theNumber }
            fifth: changeTheNumber(newNumber: 5) { theNumber }
        }
        """,
        initial_value=Root(6),
        executor_cls=executor_cls,
        expected_data={
            "first": {"theNumber": 1},
            "second": {"theNumber": 2},
            "third": {"theNumber": 3},
            "fourth": {"theNumber": 0},
            "fifth": {"theNumber": 5},
        },
        expected_errors=[],
    )


async def test_it_evaluates_mutations_correctly_even_when_some_mutation_fails(
    executor_cls
):
    doc = """
        mutation M {
            first: changeTheNumber(newNumber: 1) { theNumber }
            second: failToChangeTheNumber(newNumber: 3) { theNumber }
            third: incrementTheNumber(newNumber: 1, steps: 1) { theNumber }
            fourth: failToChangeTheNumber(newNumber: 6) { theNumber }
        }
    """
    await assert_execution(
        schema,
        doc,
        initial_value=Root(6),
        executor_cls=executor_cls,
        expected_data={
            "first": {"theNumber": 1},
            "second": None,
            "third": {"theNumber": 2},
            "fourth": None,
        },
        expected_errors=[
            ("Cannot change the number", (72, 129), "second"),
            ("Cannot change the number", (202, 259), "fourth"),
        ],
    )
