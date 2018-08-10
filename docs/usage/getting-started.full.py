
import json

from flask import Flask, Response, request

from py_gql import graphql
from py_gql.schema import (
    ID,
    Argument,
    Field,
    Int,
    ListType,
    NonNullType,
    ObjectType,
    Schema,
    String,
)

DATA = """
[
  {
    "id": 1,
    "title": "adipisicing exercitation veniam",
    "comments": []
  },
  {
    "id": 2,
    "title": "exercitation dolor ipsum",
    "comments": [
      {
        "id": 21,
        "body": "excepteur consectetur id ea eu proident et elit exercitation eiusmod"
      },
      {
        "id": 21,
        "body": "do commodo aliquip ipsum anim consectetur ea aute ea nulla"
      }
    ]
  },
  {
    "id": 3,
    "title": "sint est ex",
    "comments": [
      {
        "id": 31,
        "body": "commodo sunt laborum reprehenderit aliquip ex amet est mollit magna"
      },
      {
        "id": 32,
        "body": "deserunt qui id aliqua in tempor aliqua nostrud ullamco officia"
      },
      {
        "id": 33,
        "body": "veniam consequat fugiat commodo nostrud labore do dolore duis nisi"
      }
    ]
  }
]
"""

DB = {str(row["id"]): row for row in json.loads(DATA)}


def resolve_post(_, args, context, info):
    # Extract post from DB object
    return context["DB"].get(args["id"])


def resolve_comments(post, args, context, info):
    # Paginate + add parent post to comment objects to support nesting
    page = post["comments"][args["offset"] : args["offset"] + args["count"]]
    return [dict(c, post=post) for c in page]


PostType = ObjectType(
    "Post",
    [
        Field("id", NonNullType(ID)),
        Field("title", NonNullType(String)),
        Field(
            "comments",
            # The lambda allows to us to avoid issues with circular types
            lambda: ListType(CommentType),
            args=[
                Argument("count", NonNullType(Int)),
                Argument("offset", NonNullType(Int), default_value=0),
            ],
            resolve=resolve_comments,
        ),
    ],
)

CommentType = ObjectType(
    "Comment",
    [
        Field("id", NonNullType(ID)),
        Field("post", NonNullType(PostType)),
        Field("body", String),
    ],
)

# The root Query type is special as it defines the top-level fields available
# to clients for querying. Otherwise it is a standard ObjectType similar to
# the ones defined above.
schema = Schema(
    ObjectType(
        "Query",
        [
            Field(
                "post",
                PostType,
                args=[Argument("id", NonNullType(ID))],
                resolve=resolve_post,
            )
        ],
    )
)


app = Flask(__name__)


@app.route("/graphql", methods=("POST",))
def graphql_route():
    data = request.json

    result = graphql(
        schema,
        data["query"],
        data.get("variables", {}),
        data.get("operation_name"),
        context=dict(DB=DB),
    )

    return Response(result.json(), mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True)
