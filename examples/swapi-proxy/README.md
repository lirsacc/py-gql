# SWAPI + Flask GraphQL proxy

```
./run
```

This example demonstrates:

-   Usage of `ThreadPoolExecutor` for parallel fetching and nested usage of the
    executor through `py_gql.execution.ResolutionInfo.executor` to nest async
    request
-   Schema generation and resolver inference from an SDL file
-   Simple [flask](http://flask.pocoo.org) integration

Data is fetched live from [https://swapi.co](https://swapi.co).

**NOTE:** This code could be optimised as it currently doesn't deduplicate in flight requests and doesn't chain requests as `Future`s which leads to longer wait time than necessary.

## Running

1.  Make sure you have `py_gql` installed
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the flask server: `FLASK_APP=server.py python -m flask run --reload`
