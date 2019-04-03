# -*- coding: utf-8 -*-

from typing import List, Mapping, Optional, Sequence, TypeVar

from .._utils import DefaultOrderedDict, OrderedDict, deduplicate
from ..exc import ValidationError
from ..lang import ast as _ast
from ..lang.visitor import DispatchingVisitor
from ..schema import Schema
from ..utilities import TypeInfoVisitor

T = TypeVar("T")
MMap = Mapping[str, Mapping[str, T]]
LMap = Mapping[str, List[T]]


class ValidationVisitor(DispatchingVisitor):
    """ Visitor class used for validating GraphQL documents.

    Subclass this to implement custom validators. Use :meth:`add_error` to
    register errors and :class:`py_gql.lang.visitor.SkipNode` to prevent
    validating child nodes when parent node is invalid.

    Args:
        schema: Schema to validate against (for known types, directives, etc.).
        type_info: Type information collector provided by
            :func:`~py_gql.validation.validate`.

    Attributes:
        schema (py_gql.schema.Schema): Schema to validate against
            (for known types, directives, etc.).
        type_info (TypeInfoVisitor): Type information collector provided by
            :func:`~py_gql.validation.validate`.
        errors (List[ValidationError]): Collected errors.
    """

    def __init__(self, schema: Schema, type_info: TypeInfoVisitor):
        super(ValidationVisitor, self).__init__()
        self.schema = schema
        self.type_info = type_info
        self.errors = []  # type: List[ValidationError]

    def add_error(
        self, message: str, nodes: Optional[Sequence[_ast.Node]] = None
    ) -> None:
        """ Register an error

        Args:
            message (str): Error description
            nodes (Optional[List[py_gql.lang.ast.Node]]):
                Nodes where the error comes from
        """
        self.errors.append(ValidationError(message, nodes))


class VariablesCollector(ValidationVisitor):
    """
    Custom validation visitor which tracks all variable definitions and
    usage across the document.
    """

    def __init__(self, schema, type_info):
        super(VariablesCollector, self).__init__(schema, type_info)

        self._op = None
        self._op_variables = DefaultOrderedDict(
            OrderedDict
        )  # type: MMap[_ast.Variable]
        self._op_defined_variables = DefaultOrderedDict(
            OrderedDict
        )  # type: MMap[_ast.VariableDefinition]
        self._op_fragments = DefaultOrderedDict(
            list
        )  # type: LMap[_ast.FragmentSpread]
        self._fragment = None
        self._fragment_variables = DefaultOrderedDict(
            OrderedDict
        )  # type: MMap[_ast.Variable]
        self._fragment_fragments = DefaultOrderedDict(
            list
        )  # type: LMap[_ast.FragmentSpread]
        self._in_var_def = False

    def enter_operation_definition(self, node):
        self._op = node.name.value if node.name else ""

    def leave_operation_definition(self, _node):
        self._op = None

    def enter_fragment_definition(self, node):
        self._fragment = node.name.value

    def leave_fragment_definition(self, _node):
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

    def leave_variable_definition(self, _node):
        self._in_var_def = False

    def enter_variable(self, node):
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
