# -*- coding: utf-8 -*-
""" Validation of GraphQL (query) documents.

- Use `validate_ast` to confirm that a GraphQL document is correct.
- This only validates query documents not IDL / type system definitions.
- Each validator is a custom vistor which checks one semantic rule defined by
  the spec. They do not cross reference each other and assume that the others
  validators are passing though they should not break and just silently ignore
  unexpected input (if that's not the case, that's a bug).
- There is no suggestion list implementation like the ref implementation
  provides.
"""

from itertools import chain

from ..lang.visitor import ParrallelVisitor, visit
from ..utilities import TypeInfoVisitor
from .visitors import ValidationVisitor  # noqa: F401
from .rules import (  # noqa: F401
    ExecutableDefinitionsChecker,
    UniqueOperationNameChecker,
    LoneAnonymousOperationChecker,
    SingleFieldSubscriptionsChecker,
    KnownTypeNamesChecker,
    FragmentsOnCompositeTypesChecker,
    VariablesAreInputTypesChecker,
    ScalarLeafsChecker,
    FieldsOnCorrectTypeChecker,
    UniqueFragmentNamesChecker,
    KnownFragmentNamesChecker,
    NoUnusedFragmentsChecker,
    PossibleFragmentSpreadsChecker,
    NoFragmentCyclesChecker,
    UniqueVariableNamesChecker,
    NoUndefinedVariablesChecker,
    NoUnusedVariablesChecker,
    KnownDirectivesChecker,
    UniqueDirectivesPerLocationChecker,
    KnownArgumentNamesChecker,
    UniqueArgumentNamesChecker,
    ValuesOfCorrectTypeChecker,
    ProvidedNonNullArgumentsChecker,
    VariablesDefaultValueAllowedChecker,
    VariablesInAllowedPositionChecker,
    OverlappingFieldsCanBeMergedChecker,
    UniqueInputFieldNamesChecker,
)

SPECIFIED_CHECKERS = (
    ExecutableDefinitionsChecker,
    UniqueOperationNameChecker,
    LoneAnonymousOperationChecker,
    SingleFieldSubscriptionsChecker,
    KnownTypeNamesChecker,
    FragmentsOnCompositeTypesChecker,
    VariablesAreInputTypesChecker,
    ScalarLeafsChecker,
    FieldsOnCorrectTypeChecker,
    UniqueFragmentNamesChecker,
    KnownFragmentNamesChecker,
    NoUnusedFragmentsChecker,
    PossibleFragmentSpreadsChecker,
    NoFragmentCyclesChecker,
    UniqueVariableNamesChecker,
    NoUndefinedVariablesChecker,
    NoUnusedVariablesChecker,
    KnownDirectivesChecker,
    UniqueDirectivesPerLocationChecker,
    KnownArgumentNamesChecker,
    UniqueArgumentNamesChecker,
    ValuesOfCorrectTypeChecker,
    ProvidedNonNullArgumentsChecker,
    VariablesDefaultValueAllowedChecker,
    VariablesInAllowedPositionChecker,
    OverlappingFieldsCanBeMergedChecker,
    UniqueInputFieldNamesChecker,
)


class ValidationResult(object):
    """ """
    def __init__(self, errors):
        self.errors = errors or []

    def __bool__(self):
        return not self.errors

    def __iter__(self):
        return self.errors

    def __str__(self):
        return '<%s (%s)>' % (type(self).__name__, bool(self))


def validate_ast(schema, ast_root, validators=None):
    """ Check that an ast is a valid GraphQL query docuemnt.

    Runs a parse tree through a list of validation visitors given a schema.

    [WARN] This assumes the ast is a valid document generated by
    `py_gql.lang.parser.parse` and will most likely break unexpectedly
    if that's not the case.

    :type schema: py_gql.schema.Schema
    :param schema:
        Schema to validate against (for known types, directives, etc.).

    :type ast_root: py_gql.lang.ast.Document
    :param ast_root:
        The parse tree root, should be a Document.

    :type validators: Iterable[type|Tuple[type, dict]]
    :param validators:
        List of validators to use. Defaults to ``SPECIFIED_CHECKERS``.

    :rtype: List[ValidationError]
    :returns:
        List of ValidationErrors.
    """
    type_info = TypeInfoVisitor(schema)
    if validators is None:
        validators = SPECIFIED_CHECKERS

    def instantiate_validator(cls_or_tuple, schema, type_info):
        if isinstance(cls_or_tuple, tuple):
            cls, kw = cls_or_tuple
        else:
            cls, kw = cls_or_tuple, {}
        assert issubclass(cls, ValidationVisitor)
        return cls(schema, type_info, **kw)

    # Type info NEEDS to be first to be accurately used inside other validators
    # so when a validator enters node the type stack has already been updated.
    validator = ParrallelVisitor(type_info, *[
        instantiate_validator(validator_, schema, type_info)
        for validator_ in validators
    ])

    visit(validator, ast_root)

    return ValidationResult(
        list(chain(*[v.errors for v in validator.visitors[1:]]))
    )