# -*- coding: utf-8 -*-

import six

from ..exc import ResolverError, CoercionError
from ..utilities import directive_arguments


class ExecutionContext(object):
    """ Container to be passed around **internally** during the execution.
    Unless you are implementing a custom execution function you should not need to
    refer tot his class.
    """

    __slots__ = (
        "schema",
        "document",
        "variables",
        "fragments",
        "executor",
        "operation",
        "_errors",
        "context",
    )

    def __init__(
        self, schema, document, variables, fragments, executor, operation, context
    ):
        """
        :type schema: py_gql.schema.Schema
        :param schema:

        :type document: py_gql.lang.ast.Document
        :param document:

        :type variables: dict
        :param variables: Coerced variables

        :type fragments: dict[str, py_gql.lang.ast.FragmentDefinition]
        :param fragments:

        :type operation: py_gql.lang.ast.OperationDefinition
        :param operation:

        :type context: any
        :param context:
        """
        self.schema = schema
        self.document = document
        self.variables = variables
        self.fragments = fragments
        self.executor = executor
        self.operation = operation
        self.context = context
        self._errors = []

    def add_error(self, err, node=None, path=None):
        """ Register a localized execution error.

        :type err: str|Exception
        :param err: The error

        :type node: py_gql.lang.ast.Node
        :param node: The node corresponding to this error

        :type path: py_gql._utils.Path
        :param path: The traversal path where this error was occuring
        """
        if isinstance(err, six.string_types):
            err = ResolverError(err, node, path)
        elif isinstance(err, (ResolverError, CoercionError)):
            if node:
                if err.nodes and node not in err.nodes:
                    err.nodes.append(node)
                elif not err.nodes:
                    err.nodes = [node]
            err.path = path if path is not None else err.path
        self._errors.append((err, node, path))

    @property
    def errors(self):
        """ Get a copy of the errors without the risk of modifying the internal
        structure.

        :rtype: list[tuple[str|Exception, py_gql.lang.ast.Node, py_gql._utils.Path]]
        """
        return self._errors[:]


# REVIEW: Maybe this exposes too much?
class ResolveInfo(object):
    """ ResolveInfo will be passed to custom resolver function to expose
    some of the data used in the execution process as well as some common helper
    functions.

    WARN: Interface will surely change as the resolver definitions get fined-tuned.
    """

    __slots__ = (
        "field_def",
        "parent_type",
        "path",
        "schema",
        "variables",
        "fragments",
        "operation",
        "nodes",
        "_directive_values",
        "executor",
    )

    def __init__(
        self,
        field_def,
        parent_type,
        path,
        schema,
        variables,
        fragments,
        operation,
        nodes,
        executor,
    ):
        """
        :type field_def: py_gql.schema.Field
        :param field_def: Type definition for the field being resolved

        :type parent_type: py_gql.schema.ObjectType
        :param parent_type: ObjectType definition where the field originated from

        :type path: py_gql._utils.Path
        :param path: Current traversal path

        :type schema: py_gql.schema.Schema
        :param schema:

        :type variables: dict
        :param variables: Coerced variables

        :type fragments: dict[str, py_gql.lang.ast.FragmentDefinition]
        :param fragments:

        :type operation: py_gql.lang.ast.OperationDefinition
        :param operation:

        :type node: list[py_gql.lang.ast.Node]
        :param node: The nodes corresponding to the field

        :type executor: py_gql.execution.executors.Executor
        :param executor: The current executor
            Use this if you need to submit call other resover / fetcher functions
            inside an exsiting resolver.
        """
        self.field_def = field_def
        self.parent_type = parent_type
        self.path = path
        self.schema = schema
        self.variables = variables
        self.fragments = fragments
        self.operation = operation
        self.nodes = nodes
        self.executor = executor

        self._directive_values = {}

    def directive_values(self, directive_name):
        """ Extract directive argument values for given directive name.

        :type directive_name: str
        :param directive_name: Directive name.
            This assumes validation has run and the directive exists in the schema
            as well as in a valid position.

        :rtype: dict
        :returns: The arguments to the directive
        """
        if directive_name in self._directive_values:
            return self._directive_values[directive_name]

        definition = self.schema.directives[directive_name]
        values = {}
        for node in self.nodes:
            values.update(directive_arguments(definition, node, self.variables) or {})
        self._directive_values[directive_name] = values
        return values
