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
        ids = [int(u.split("/")[-2]) for u in obj[key]]
        return _concurrency.all_(
            [info.executor.submit(swapi.fetch_one, resource, id) for id in ids]
        )

    return resolve


single_fields = {"Query.person": "people", "Person.homeworld": "planets"}
list_fields = {"Planet.residents": "people"}
resources = ("films", "people", "planets")


def infer_resolver(typename, fieldname):
    path = typename + "." + fieldname
    if typename == "Query" and fieldname.startswith("all_"):
        resource = fieldname.split("_")[-1]
        if resource in resources:
            return resource_resolver(resource)
        elif path in single_fields:
            return single_resource_resolver(single_fields[path])
        elif fieldname + "s" in resources:
            return single_resource_resolver(fieldname)
    elif path in single_fields:
        return nested_single_resource_resolver(fieldname, single_fields[path])
    elif fieldname + "s" in resources:
        return nested_single_resource_resolver(fieldname, fieldname + "s")
    elif path in list_fields:
        return nested_list_resolver(fieldname, list_fields[path])
    elif fieldname in resources:
        return nested_list_resolver(fieldname, fieldname)
    return None


with open(os.path.join(os.path.dirname(__file__), "schema.graphql")) as f:
    schema = schema_from_ast(f.read(), resolvers=infer_resolver)
