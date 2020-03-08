# -*- coding: utf-8 -*-
import aiohttp


URL = "https://swapi.co/api"


async def fetch(url, query=None, cache={}):
    headers = {"User-Agent": "python"}
    cache_key = (url, tuple(sorted(query.items())) if query else None)

    if cache_key in cache:
        print("Fetching from cache", cache_key)
        return cache[cache_key]

    print("Fetching", cache_key)
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, headers=headers, params=query)
        response.raise_for_status()
        data = await response.json()
        cache[cache_key] = data
        return data


def _url(*parts):
    return "%s/%s/" % (URL, "/".join(parts))


async def fetch_one(resource, id):
    try:
        res = await fetch(_url(resource, str(id)))
    except aiohttp.client_exceptions.ClientResponseError as err:
        if err.status == 404:
            return None
        raise

    if res is None:
        return res
    return dict(res, id=id)


async def fetch_many(resource, **kw):
    resp = await fetch(
        _url(resource), query={k: v for k, v in kw.items() if v is not None}
    )
    res = resp["results"]
    return [dict(r, id=int(r["url"].split("/")[-2])) for r in res]
