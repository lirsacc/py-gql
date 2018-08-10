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
        [Field("post", PostType, args=[Argument("id", NonNullType(ID))])],
    )
)
