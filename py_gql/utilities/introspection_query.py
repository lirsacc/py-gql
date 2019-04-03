# -*- coding: utf-8 -*-


def introspection_query(description: bool = True) -> str:
    """
    Return a generic introspection query to be used by GraphQL clients.

    Args:
        description:
            If ``True`` the query will require descriptions to be included.

    Returns:
        Canonical intropsection query
    """
    return """
    query IntrospectionQuery {
        __schema {
            queryType { name }
            mutationType { name }
            subscriptionType { name }

            types {
                ...FullType
            }

            directives {
                name
                %(description_field)s
                locations
                args {
                    ...InputValue
                }
            }
        }
    }

    fragment FullType on __Type {
        kind
        name
        %(description_field)s

        fields(includeDeprecated: true) {
            name
            %(description_field)s
            args {
                ...InputValue
            }
            type {
                ...TypeRef
            }
            isDeprecated
            deprecationReason
        }

        inputFields {
            ...InputValue
        }

        interfaces {
            ...TypeRef
        }

        enumValues(includeDeprecated: true) {
            name
            %(description_field)s
            isDeprecated
            deprecationReason
        }

        possibleTypes {
            ...TypeRef
        }
    }

    fragment InputValue on __InputValue {
        name
        %(description_field)s
        type { ...TypeRef }
        defaultValue
    }

    fragment TypeRef on __Type {
        kind
        name
        ofType {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """ % {
        "description_field": "" if not description else "description"
    }
