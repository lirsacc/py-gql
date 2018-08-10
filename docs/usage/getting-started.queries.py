# Valid query
graphql(
    schema,
    """
    {
        post(id: 1) {
            id
            title
            comments(count: 10) {
                id
                body
                post {
                    id
                }
            }
        }
    }
    """,
    context={"DB": DB},
)
# {
#     "data": {
#         "post": {
#             "id": "1",
#             "title": "adipisicing exercitation veniam",
#             "comments": []
#         }
#     }
# }

# Valid query (nested result)
graphql(
    schema,
    """
    {
        post(id: 3) {
            id
            title
            comments(count: 10, offset: 1) {
                id
                body
                post {
                    id
                }
            }
        }
    }
    """,
    context={"DB": DB},
)
# {
#     "data": {
#         "post": {
#             "id": "3",
#             "title": "sint est ex",
#             "comments": [
#                 {
#                     "id": "32",
#                     "body": "deserunt qui id aliqua in tempor aliqua nostrud ullamco officia",
#                     "post": {
#                         "id": "3"
#                     }
#                 },
#                 {
#                     "id": "33",
#                     "body": "veniam consequat fugiat commodo nostrud labore do dolore duis nisi",
#                     "post": {
#                         "id": "3"
#                     }
#                 }
#             ]
#         }
#     }
# }


# Invalid query
graphql(
    schema,
    """
    {
        post(id: 1) {
            id
            titl
            comments
        }
    }
    """,
    context={"DB": DB},
)
# {
#     "errors": [
#         {
#             "message": "Field \"comments\" of type \"[Comment]\" must have a subselection",
#             "locations": [
#                 {
#                     "line": 6,
#                     "column": 13
#                 }
#             ]
#         },
#         {
#             "message": "Cannot query field \"titl\" on type \"Post\", did you mean \"title\"?",
#             "locations": [
#                 {
#                     "line": 5,
#                     "column": 13
#                 }
#             ]
#         },
#         {
#             "message": "Field \"comments\" argument \"count\" of type Int! is required but not provided",
#             "locations": [
#                 {
#                     "line": 6,
#                     "column": 13
#                 }
#             ]
#         }
#     ]
# }

# Using aliases
graphql(
    schema,
    """
    {
        post1: post(id: 1) { id title }
        post2: post(id: 2) { id title }
    }
    """,
    context={"DB": DB},
)
# {
#     "data": {
#         "post1": {
#             "id": "1",
#             "title": "adipisicing exercitation veniam"
#         },
#         "post2": {
#             "id": "2",
#             "title": "exercitation dolor ipsum"
#         }
#     }
# }

# Missing post
graphql(
    schema,
    """
    {
        post(id: 8) { title }
    }
    """,
    context={"DB": DB},
)
# {
#     "data": {
#         "post": null
#     }
# }

graphql(
    schema,
    """
    {
        post(id: true){
            id
            title
        }
    }
    """,
    context={"DB": DB},
)
# Bad argument
# {
#     "errors": [
#         {
#             "message": "Expected type ID!, found true",
#             "locations": [
#                 {
#                     "line": 3,
#                     "column": 18
#                 }
#             ]
#         }
#     ]
# }
