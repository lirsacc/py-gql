# -*- coding: utf-8 -*-

from py_gql import graphql
from py_gql.utilities.tracers import ApolloTracer


def test_it_does_not_crash(starwars_schema):
    # REVIEW: This doesn't test anything more than the code not crashing
    tracer = ApolloTracer()
    graphql(
        starwars_schema,
        """
        query NestedQuery {
            hero {
                name
                friends {
                    name
                    appearsIn
                    friends {
                    name
                    }
                }
            }
        }
        """,
        tracer=tracer,
    )

    tracer.payload()
    assert tracer.name() == "tracing"
