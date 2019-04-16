# SWAPI + Flask GraphQL proxy

This example demonstrates:

- Usage of `ThreadPoolExecutor` for parallel synchronous IO and `process_graphql_request` to inject executor class.
- Schema generation from an SDL file
- Tracer and extension usage
- Simple [flask](http://flask.pocoo.org) integration with GraphiQL

Data is fetched live from <https://swapi.co>.

**NOTE:** This code could be optimised as it currently doesn't deduplicate in flight requests and doesn't chain requests as `Future`s which leads to longer wait time than necessary.

## Running

```.bash
pip install -r requirements.txt
FLASK_APP=server.py python -m flask run --reload
```

You can then open <http://localhost:5000/graphiql> to run queries interactively.
