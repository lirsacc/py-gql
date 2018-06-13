# -*- coding: utf-8 -*-
""" Define the GraphQL schema
"""

import functools as ft
import os

import requests

import swapi
from py_gql.exc import ResolverError
from py_gql.execution import _concurrency
from py_gql.schema import schema_from_ast


def swapi_caller(func):
    @ft.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as err:
            raise ResolverError(
                "Cannot reach SWAPI",
                extensions=[
                    ("msg", str(err)),
                    ("code", err.response.status_code),
                    ("url", err.request.url),
                ],
            )

    return wrapper


def single_resource_resolver(resource):
    @swapi_caller
    def resolve(obj, args, ctx, info):
        return swapi.fetch_one(resource, args["id"])

    return resolve


def nested_single_resource_resolver(key, resource):
    @swapi_caller
    def resolve(obj, args, ctx, info):
        if obj is None:
            return None
        id = int(obj[key].split("/")[-2])
        return info.executor.submit(swapi.fetch_one, resource, id)

    return resolve


def resource_resolver(resource):
    @swapi_caller
    def resolve(obj, args, ctx, info):
        return swapi.fetch_many(resource, search=args.get("search"))

    return resolve


def nested_list_resolver(key, resource):
    @swapi_caller
    def resolve(obj, args, ctx, info):
        if obj is None:
            return None
        ids = [int(u.split("/")[-2]) for u in obj[key]]
        return _concurrency.all_(
            [info.executor.submit(swapi.fetch_one, resource, id) for id in ids]
        )

    return resolve


RESOLVERS = {
    "Query": {
        "film": single_resource_resolver("films"),
        "all_films": resource_resolver("films"),
        "planet": single_resource_resolver("planets"),
        "all_planets": resource_resolver("planets"),
        "person": single_resource_resolver("people"),
        "all_people": resource_resolver("people"),
    },
    "Film": {"planets": nested_list_resolver("planets", "planets")},
    "Planet": {
        "residents": nested_list_resolver("residents", "people"),
        "films": nested_list_resolver("films", "films"),
    },
    "Person": {
        "homeworld": nested_single_resource_resolver("homeworld", "planets"),
        "films": nested_list_resolver("films", "films"),
    },
}

with open(os.path.join(os.path.dirname(__file__), "schema.graphql")) as f:
    schema = schema_from_ast(f.read(), resolvers=RESOLVERS)
