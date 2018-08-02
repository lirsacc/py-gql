# SWAPI + Aiohttp GraphQL proxy

```
./run
```

This example demonstrates:

-   Usage of `AsyncIOExecutor` for parallel fetching using `async/await` and
    regular synchronous functions.
-   Schema generation and resolver inference from an SDL file
-   Simple [aiohttp](https://aiohttp.readthedocs.io/) integration

Data is fetched live from [https://swapi.co](https://swapi.co).

**NOTE:** This code could be optimised as it currently doesn't deduplicate in flight requests and doesn't chain requests which leads to longer wait time than necessary.

## Running

1.  Make sure you have `py_gql` installed
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the flask server: `adev runserver -p 5000 --app-factory init server.py`
