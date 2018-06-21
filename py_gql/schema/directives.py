# -*- coding: utf-8 -*-
""" Default directives. """
from __future__ import unicode_literals

from .scalars import Boolean, String
from .types import Argument, Directive, NonNullType

IncludeDirective = Directive(
    "include",
    description=(
        "Directs the executor to include this field or fragment only when "
        "the `if` argument is true."
    ),
    locations=["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
    args=[
        Argument("if", NonNullType(Boolean), description="Included when true")
    ],
)

SkipDirective = Directive(
    "skip",
    description=(
        "Directs the executor to skip this field or fragment when the `if` "
        "argument is true."
    ),
    locations=["FIELD", "FRAGMENT_SPREAD", "INLINE_FRAGMENT"],
    args=[
        Argument("if", NonNullType(Boolean), description="Skipped when true")
    ],
)

DEFAULT_DEPRECATION = "No longer supported"

DeprecatedDirective = Directive(
    "deprecated",
    description="Marks an element of a GraphQL schema as no longer supported.",
    locations=["FIELD_DEFINITION", "ENUM_VALUE"],
    args=[
        Argument(
            "reason",
            String,
            default_value=DEFAULT_DEPRECATION,
            description=(
                "Explains why this element was deprecated, usually also "
                "including a suggestion for how to access supported "
                "similar data. Formatted in [Markdown](https://daringfireball"
                ".net/projects/markdown/)."
            ),
        )
    ],
)


# These are the types which are part of the spec and will always be available
# in any spec compliant GraphQL server.
SPECIFIED_DIRECTIVES = (IncludeDirective, SkipDirective, DeprecatedDirective)
