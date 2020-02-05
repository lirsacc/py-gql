# -*- coding: utf-8 -*-
""" Define the GraphQL schema
"""

import functools as ft
import os
import re

import requests

from py_gql import build_schema
from py_gql.exc import ResolverError

from . import swapi


def swapi_caller(func):
    @ft.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as err:
            raise ResolverError(
                "Cannot reach SWAPI",
                extensions={
                    "msg": str(err),
                    "code": err.response.status_code,
                    "url": err.request.url,
                },
            )

    return wrapper


def single_resource_resolver(resource):
    @swapi_caller
    def resolve(*, id):
        return swapi.fetch_one(resource, id)

    return resolve


def nested_single_resource_resolver(key, resource):
    @swapi_caller
    def resolve(obj, ctx, info, **args):
        if obj is None:
            return None
        return swapi.fetch_one(resource, int(obj[key].split("/")[-2]))

    return resolve


def resource_resolver(resource):
    @swapi_caller
    def resolve(obj, ctx, info, **args):
        return swapi.fetch_many(resource, search=args.get("search"))

    return resolve


def nested_list_resolver(key, resource):
    @swapi_caller
    def resolve(obj, ctx, info, **args):
        if obj is None:
            return None
        ids = [int(u.split("/")[-2]) for u in obj[key]]
        return info.runtime.gather_values(
            [info.runtime.submit(swapi.fetch_one, resource, id) for id in ids]
        )

    return resolve


# This on is pretty dumb...
def string_numeric_resolver(key):
    def resolver(obj, *_, **__):
        value = obj.get(key)
        if value is None or value.lower() in ("n/a", "unknown"):
            return None
        return float(re.sub(r"[A-Za-z]", "", value))

    return resolver


TRANSPORT_RESOLVERS = {
    "films": nested_list_resolver("films", "films"),
    "pilots": nested_list_resolver("pilots", "people"),
    "max_atmosphering_speed": string_numeric_resolver("max_atmosphering_speed"),
    "cost_in_credits": string_numeric_resolver("cost_in_credits"),
    "length": string_numeric_resolver("length"),
    "crew": string_numeric_resolver("crew"),
    "passengers": string_numeric_resolver("passengers"),
    "cargo_capacity": string_numeric_resolver("cargo_capacity"),
}

RESOLVERS = {
    "Query": {
        "film": single_resource_resolver("films"),
        "all_films": resource_resolver("films"),
        "planet": single_resource_resolver("planets"),
        "all_planets": resource_resolver("planets"),
        "person": single_resource_resolver("people"),
        "all_people": resource_resolver("people"),
        "starship": single_resource_resolver("starships"),
        "all_starships": resource_resolver("starships"),
        "vehicle": single_resource_resolver("vehicles"),
        "all_vehicles": resource_resolver("vehicles"),
        "species": single_resource_resolver("species"),
        "all_species": resource_resolver("species"),
    },
    "Film": {"planets": nested_list_resolver("planets", "planets")},
    "Planet": {
        "residents": nested_list_resolver("residents", "people"),
        "films": nested_list_resolver("films", "films"),
        "population": string_numeric_resolver("population"),
        "surface_water": string_numeric_resolver("surface_water"),
    },
    "Person": {
        "homeworld": nested_single_resource_resolver("homeworld", "planets"),
        "films": nested_list_resolver("films", "films"),
        "vehicles": nested_list_resolver("vehicles", "vehicles"),
        "starships": nested_list_resolver("starships", "starships"),
        "height": string_numeric_resolver("height"),
        "mass": string_numeric_resolver("mass"),
        "species": nested_list_resolver("species", "species"),
    },
    "Starship": TRANSPORT_RESOLVERS,
    "Vehicle": TRANSPORT_RESOLVERS,
    "Species": {
        "homeworld": nested_single_resource_resolver("homeworld", "planets"),
        "people": nested_list_resolver("people", "people"),
        "films": nested_list_resolver("films", "films"),
        "average_lifespan": string_numeric_resolver("average_lifespan"),
    },
}


with open(os.path.join(os.path.dirname(__file__), "schema.graphql")) as f:
    SCHEMA = build_schema(f.read())


for typename, field_resolvers in RESOLVERS.items():
    for fieldname, resolver in field_resolvers.items():
        SCHEMA.register_resolver(typename, fieldname, resolver)
