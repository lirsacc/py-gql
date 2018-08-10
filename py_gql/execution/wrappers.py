# -*- coding: utf-8 -*-

import json
from concurrent.futures import Future

import six

from .._utils import OrderedDict
from ..exc import CoercionError, MultiCoercionError, ResolverError
from ..utilities import directive_arguments


class ExecutionContext(object):
    """ Container to be passed around **internally** during the execution.
    Unless you are implementing a custom execution function you should not need to
    refer to this class.
    """

    __slots__ = (
        "schema",
        "document",
        "variables",
        "fragments",
        "executor",
        "future_cls",
        "operation",
        "middlewares",
        "context",
        "_errors",
        "grouped_fields",
        "field_defs",
        "subselections",
        "argument_values",
    )

    def __init__(
        self,
        schema,
        document,
        variables,
        fragments,
        executor,
        operation,
        middlewares,
        context,
    ):
        self.schema = schema
        self.document = document
        self.variables = variables
        self.fragments = fragments
        self.executor = executor
        self.future_cls = getattr(executor, "Future", Future)
        self.operation = operation
        self.middlewares = middlewares
        self.context = context

        self._errors = []

        self.grouped_fields = {}
        self.field_defs = {}
        self.subselections = {}
        self.argument_values = {}

    def add_error(self, err, node=None, path=None):
        """ Register a localized execution error.

        :type err: str|Exception
        :param err: The error

        :type node: py_gql.lang.ast.Node
        :param node: The node corresponding to this error

        :type path: list
        :param path: The traversal path where this error was occuring
        """
        if isinstance(err, six.string_types):
            err = ResolverError(err, [node], path)
        elif isinstance(err, MultiCoercionError):
            for child_error in err.errors:
                self.add_error(child_error)
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

        :rtype: list[tuple[str|Exception, py_gql.lang.ast.Node, list]]
        """
        return self._errors[:]


# REVIEW: Maybe this exposes too much?
class ResolveInfo(object):
    """ ResolveInfo will be passed to resolver functions to expose
    some of the data used in the execution process as well as some common helper
    functions. You shouldn't instantiate thos yourself.

    Warning:

        Interface will surely change as the resolver definitions gets
        fined-tuned.

    Args:
        field_def (py_gql.schema.Field):
        parent_type (py_gql.schema.ObjectType):
        path (List[Union[str, int]]):
        schema (py_gql.schema.Schema):
        variables (dict):
        fragments (dict[str, py_gql.lang.ast.FragmentDefinition]):
        operation (py_gql.lang.ast.OperationDefinition):
        node (list[py_gql.lang.ast.Node]):
        executor (py_gql.execution.executors.Executor):

    Attributes:
        field_def (py_gql.schema.Field): Field being resolved

        parent_type (py_gql.schema.ObjectType):
            ObjectType definition where the field originated from

        path (List[Union[str, int]]): Current traversal path

        schema (py_gql.schema.Schema): Schema

        variables (dict): Coerced variables

        fragments (dict[str, py_gql.lang.ast.FragmentDefinition]):
            Fragments present in the document

        operation (py_gql.lang.ast.OperationDefinition): Current operation

        node (list[py_gql.lang.ast.Node]): AST nodes corresponding to the field

        executor (py_gql.execution.executors.Executor): Current executor
            Use this if you need to submit call other resover / fetcher
            functions inside a resolver.

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
            values.update(
                directive_arguments(definition, node, self.variables) or {}
            )
        self._directive_values[directive_name] = values
        return values


_unset = object()


class GraphQLResult(object):
    """ Wrapper encoding the behaviour described in the `Response
    <http://facebook.github.io/graphql/June2018/#sec-Response>`_ part of the
    specification.

    Args:
        data (Optional[Any]):
            The data part of the response
        errors (Optional[List[py_gql.exc.GraphQLResponseError]]):
            The errors part of the response
    """

    __slots__ = "data", "errors", "extensions"

    def __init__(self, data=_unset, errors=_unset):
        self.data = data
        self.errors = errors
        self.extensions = OrderedDict()

    def __bool__(self):
        return self.errors is _unset or not self.errors

    __nonzero__ = __bool__

    def __iter__(self):
        return iter((self.data, self.errors))

    def add_extension(self, ext):
        """ Add an extensions to the result.

        Args:
            ext (GraphQLExtension): Extension instance

        Raises:
            ValueError: Extension with the same name has already been added
        """
        name = ext.name()
        if name in self.extensions:
            raise ValueError('Duplicate extension "%s"' % name)
        self.extensions[name] = ext.payload()

    def response(self):
        """ Generate an ordered response dict.

        Returns:
            dict:
        """
        d = OrderedDict()
        if self.errors is not _unset and self.errors:
            d["errors"] = [error.to_dict() for error in self.errors]
        if self.data is not _unset:
            d["data"] = self.data
        if self.extensions:
            d["extensions"] = self.extensions
        return d

    def json(self, **kw):
        """ Encode response as JSON using the standard lib ``json`` module.

        Args:
            **kw (dict): Keyword args passed to to ``json.dumps``

        Returns:
            str:
        """
        return json.dumps(self.response(), **kw)


class GraphQLExtension(object):
    """ Encode a GraphQL response extension.

    Use in conjonction with :meth:`GraphQLResult.add_extension` to encode the
    response alongside an execution result.
    """

    def payload(self):
        """
        Returns:
            Any: Extension payload; **must** be JSON serialisable.
        """
        raise NotImplementedError()

    def name(self):
        """
        Returns:
            str: Name of the extension used as the key in the response.
        """
        raise NotImplementedError()
