# -*- coding: utf-8 -*-

from .._utils import find_one
from ..utilities import coerce_argument_values


class ExecutionContext(object):
    """
    """

    __slots__ = ('schema', 'document', 'variables', 'fragments',
                 'operation', '_errors', 'context')

    def __init__(self, schema, document, variables, fragments,
                 operation, context):
        """
        """
        self.schema = schema
        self.document = document
        self.variables = variables
        self.fragments = fragments
        self.operation = operation
        self.context = context
        self._errors = []

    def add_error(self, msg, node, path):
        self._errors.append((msg, node, path))

    @property
    def errors(self):
        return self._errors[:]


class ResolutionContext(object):
    """ ResolutionContext will be passed to custom resolver function to expose
    some of the data used in the execution process. """

    __slots__ = ('field_def', 'parent_type', 'path', 'schema', 'variables',
                 'fragments', 'operation', 'nodes', '_directive_values')

    def __init__(self, field_def, parent_type, path, schema, variables,
                 fragments, operation, nodes):
        self.field_def = field_def
        self.parent_type = parent_type
        self.path = path
        self.schema = schema
        self.variables = variables
        self.fragments = fragments
        self.operation = operation
        self.nodes = nodes

        self._directive_values = {}

    def directive_values(self, directive_name):
        """ Extract directive argument values for given directive name.

        :type directive_name: str
        :param directive_name:
            Directive name. This assumes validation has run and the directive
            exists in the schema as well as in a valid position.

        :rtype: dict
        :returns:
            The arguments to the directive
        """
        if directive_name in self._directive_values:
            return self._directive_values[directive_name]

        definition = self.schema.directives[directive_name]
        values = {}
        for node in self.nodes:
            values.update(
                directive_arguments(definition, node, self.variables) or {}
            )
        self._directive_values[directive_name] = values
        return values


def directive_arguments(definition, node, variables=None):
    """ Extract directive argument given a field node and a directive
    definition.

    :type definition: py_gql.schema.Directive
    :param definition:
        Field or Directive definition from which to extract argument
        definitions.

    :type node: py_gql.lang.ast.Field
    :param node:
        Ast node

    :type variables: Optional[dict]
    :param variables:
        Coerced variable values

    :rtype: dict
    """
    directive = find_one(
        node.directives,
        lambda d: d.name.value == definition.name
    )

    return (coerce_argument_values(definition, directive, variables)
            if directive is not None else None)
