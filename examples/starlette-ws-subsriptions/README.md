# Subscription example

- **This example requires Python >= 3.7**

This example demonstrates:

- Usage with AsyncIO for queries, mutations and subscriptions.
- Subscriptions using async iterators.
- Integration over websockets using the [Startlette](https://github.com/encode/starlette) ASGI library and the [Websocket Transport Protocol](https://github.com/apollographql/subscriptions-transport-ws/blob/master/PROTOCOL.md) from Apollo GraphQL.
- Usage of MyPy and TypedDict when creating resolvers.

## Running

```.bash
pip install -r requirements.txt
uvicorn --debug --port 5000 app:app
```

You can then open <http://localhost:5000/playground> to run queries interactively.
