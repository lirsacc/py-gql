# -*- coding: utf-8 -*-
""" generic mutations handling tests """


from py_gql.exc import ResolverError
from py_gql.schema import Schema, ObjectType, Field, Int, Arg
from ._test_utils import check_execution


class NumberHolder(object):
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

    def lazilyChangeTheNumber(self, newNumber):
        def _mutate():
            self.numberHolder.theNumber = newNumber
            return self.numberHolder
        return _mutate

    def failToChangeTheNumber(self, newNumber):
        raise ResolverError('Cannot change the number')

    def lazilyFailToChangeTheNumber(self, newNumber):
        def _mutate():
            raise ResolverError('Cannot change the number')
        return _mutate


number_holder = ObjectType('NumberHolder', [Field('theNumber', Int)])

schema = Schema(
    ObjectType('Query', [
        Field('numberHolder', number_holder)
    ]),
    ObjectType('Mutation', [
        Field(
            'incrementTheNumber',
            number_holder,
            args=[
                Arg('steps', Int),
            ],
            resolve=lambda obj, args, *_: obj.incrementTheNumber(args['steps'])
        ),
        Field(
            'immediatelyChangeTheNumber',
            number_holder,
            args=[
                Arg('newNumber', Int),
            ],
            resolve=lambda obj, args, *_: (
                obj.immediatelyChangeTheNumber(args['newNumber'])
            )
        ),
        Field(
            'lazilyChangeTheNumber',
            number_holder,
            args=[
                Arg('newNumber', Int),
            ],
            resolve=lambda obj, args, *_: (
                obj.lazilyChangeTheNumber(args['newNumber'])
            )
        ),
        Field(
            'failToChangeTheNumber',
            number_holder,
            args=[
                Arg('newNumber', Int),
            ],
            resolve=lambda obj, args, *_: (
                obj.failToChangeTheNumber(args['newNumber'])
            )
        ),
        Field(
            'lazilyFailToChangeTheNumber',
            number_holder,
            args=[
                Arg('newNumber', Int),
            ],
            resolve=lambda obj, args, *_: (
                obj.lazilyFailToChangeTheNumber(args['newNumber'])
            )
        )
    ])
)


def test_it_evaluates_mutations_serially():
    check_execution(
        schema,
        '''
        mutation M {
            first: immediatelyChangeTheNumber(newNumber: 1) {
                theNumber
            },
            second: lazilyChangeTheNumber(newNumber: 2) {
                theNumber
            },
            third: immediatelyChangeTheNumber(newNumber: 3) {
                theNumber
            }
            fourth: lazilyChangeTheNumber(newNumber: 4) {
                theNumber
            },
            fifth: immediatelyChangeTheNumber(newNumber: 5) {
                theNumber
            }
        }
        ''',
        initial_value=Root(6),
        expected_data={
            'first': {'theNumber': 1},
            'second': {'theNumber': 2},
            'third': {'theNumber': 3},
            'fourth': {'theNumber': 4},
            'fifth': {'theNumber': 5},
        },
        expected_errors=[]
    )


def test_it_evaluates_mutations_serially_2():
    check_execution(
        schema,
        '''
        mutation M {
            first: incrementTheNumber(steps: 1) {
                theNumber
            },
            second: incrementTheNumber(steps: -3) {
                theNumber
            }
        }
        ''',
        initial_value=Root(6),
        expected_data={
            'first': {'theNumber': 7},
            'second': {'theNumber': 4},
        },
        expected_errors=[]
    )


def test_it_evaluates_mutations_correctly_even_when_some_mutation_fails():
    check_execution(
        schema,
        '''
        mutation M {
            first: immediatelyChangeTheNumber(newNumber: 1) {
                theNumber
            },
            second: lazilyChangeTheNumber(newNumber: 2) {
                theNumber
            },
            third: failToChangeTheNumber(newNumber: 3) {
                theNumber
            }
            fourth: lazilyChangeTheNumber(newNumber: 4) {
                theNumber
            },
            fifth: immediatelyChangeTheNumber(newNumber: 5) {
                theNumber
            }
            sixth: lazilyFailToChangeTheNumber(newNumber: 6) {
                theNumber
            }
        }
        ''',
        initial_value=Root(6),
        expected_data={
            'first': {'theNumber': 1},
            'second': {'theNumber': 2},
            'third': None,
            'fourth': {'theNumber': 4},
            'fifth': {'theNumber': 5},
            'sixth': None,
        },
        expected_errors=[
            ('Cannot change the number', (236, 320), 'third'),
            ('Cannot change the number', (534, 624), 'sixth')
        ]
    )