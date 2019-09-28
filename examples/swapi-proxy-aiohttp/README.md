# SWAPI + Aiohttp GraphQL proxy

This example demonstrates:

- Usage of `AsyncIOExecutor` for parallel fetching using `async/await` and regular synchronous functions.
- Schema generation from an SDL file
- Tracer and extension usage
- Simple [aiohttp](https://aiohttp.readthedocs.io/) integration with GraphiQL

Data is fetched live from <https://swapi.co>.

**NOTE:** This code could be optimised as it currently doesn't deduplicate in flight requests and doesn't chain requests which leads to longer wait time than necessary.

## Running

```.bash
pip install -r requirements.txt
adev runserver -p 5000 --app-factory init app.server
```

You can then open <http://localhost:5000/graphiql> to run queries interactively.
