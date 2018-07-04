# -*- coding: utf-8 -*-
import requests


URL = "https://swapi.co/api"
LOCAL_CACHE = {}


def fetch(url, query=None, cache=LOCAL_CACHE):
    headers = {"User-Agent": "python"}
    cache_key = (url, tuple(sorted(query.items())) if query else None)

    if cache_key in cache:
        print("Fetching from cache", cache_key)
        return cache[cache_key]

    print("Fetching", cache_key)
    response = requests.get(url, headers=headers, params=query)
    response.raise_for_status()

    data = response.json()
    cache[cache_key] = data
    return data


def _url(*parts):
    return "%s/%s/" % (URL, "/".join(parts))


def fetch_one(resource, id):
    try:
        res = fetch(_url(resource, str(id)))
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            return None
        raise

    if res is None:
        return res
    return dict(res, id=id)


def fetch_many(resource, **kw):
    res = fetch(_url(resource), query=kw)["results"]
    return [dict(r, id=int(r["url"].split("/")[-2])) for r in res]
