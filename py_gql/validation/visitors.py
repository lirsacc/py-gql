# -*- coding: utf-8 -*-
"""
"""

from .._utils import DefaultOrderedDict, OrderedDict, deduplicate
from ..exc import ValidationError
from ..lang.visitor import DispatchingVisitor


class ValidationVisitor(DispatchingVisitor):
    """ Visitor class used for validating GraphQL documents.

    Subclass this to implement custom validators. Use :meth:`add_error` to
    register errors and :class:`py_gql.lang.visitor.SkipNode` to prevent
    validating child nodes when parent node is invalid.

    Args:
        schema (py_gql.schema.Schema):
            Schema to validate against (for known types, directives, etc.).
        type_info (py_gql.utilities.TypeInfoVisitor):

    Attributes:
        schema (py_gql.schema.Schema):
            Schema to validate against (for known types, directives, etc.).
        type_info (py_gql.utilities.TypeInfoVisitor):
        errors (List[py_gql.exc.ValidationError]):
    """

    def __init__(self, schema, type_info):
        super(ValidationVisitor, self).__init__()
        self.schema = schema
        self.type_info = type_info
        self.errors = []

    def add_error(self, message, nodes=None):
        """ Register an error

        Args:
            message (str): Error description
            nodes (Optional[List[py_gql.lang.ast.Node]]):
                Nodes where the error comes from
        """
        self.errors.append(ValidationError(message, nodes))


class VariablesCollector(ValidationVisitor):
    """ Custom validation visitor which tracks all variable definitions and
    usage across the document.

    This replaces ``getRecursiveVariableUsages`` and ``getVariableUsages``
    from the ref implementation and allows to work with variables without
    eagerly visitng subtrees.

    Most validation must happen in :meth:`leave_document` though.
    """

    def __init__(self, schema, type_info):
        super(VariablesCollector, self).__init__(schema, type_info)

        self._op = None
        self._op_variables = DefaultOrderedDict(OrderedDict)
        self._op_defined_variables = DefaultOrderedDict(OrderedDict)
        self._op_fragments = DefaultOrderedDict(list)
        self._fragment = None
        self._fragment_variables = DefaultOrderedDict(OrderedDict)
        self._fragment_fragments = DefaultOrderedDict(list)
        self._in_var_def = False

    def enter_operation_definition(self, node):
        self._op = node.name.value if node.name else ""

    def leave_operation_definition(self, node):
        self._op = None

    def enter_fragment_definition(self, node):
        self._fragment = node.name.value

    def leave_fragment_definition(self, node):
        self._fragment = None

    def enter_fragment_spread(self, node):
        name = node.name.value
        if self._op is not None:
            self._op_fragments[self._op].append(name)
        elif self._fragment is not None and name != self._fragment:
            self._fragment_fragments[self._fragment].append(name)

    def enter_variable_definition(self, node):
        self._in_var_def = True
        name = node.variable.name.value
        if self._op is not None:
            self._op_defined_variables[self._op][name] = node

    def leave_variable_definition(self, node):
        self._in_var_def = False

    def enter_variable_value(self, node):
        var = node.name.value
        input_type = self.type_info.input_type
        input_value_def = self.type_info.input_value_def
        if self._in_var_def:
            pass
        elif self._op is not None:
            self._op_variables[self._op][var] = (
                node,
                input_type,
                input_value_def,
            )
        elif self._fragment is not None:
            self._fragment_variables[self._fragment][var] = (
                node,
                input_type,
                input_value_def,
            )

    def _flatten_fragments(self):
        for parent, children in self._fragment_fragments.items():
            for child in deduplicate(children):
                for op in self._op_fragments.keys():
                    if parent in self._op_fragments[op]:
                        self._op_fragments[op].append(child)

    def leave_document(self, _):
        self._flatten_fragments()
