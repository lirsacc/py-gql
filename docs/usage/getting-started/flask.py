app = flask.Flask(__name__)


@app.route("/graphql", methods=("POST",))
def graphql_route():
    data = flask.request.json

    result = graphql_blocking(
        schema,
        data["query"],
        variables=data.get("variables", {}),
        operation_name=data.get("operation_name"),
        context=dict(db=database),
    )

    return flask.jsonify(result.response())
