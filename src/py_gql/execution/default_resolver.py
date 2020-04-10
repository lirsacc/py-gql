# -*- coding: utf-8 -*-

from collections.abc import Mapping
from typing import Any

from .wrappers import ResolveInfo


def default_resolver(
    root: Any,
    context: Any,
    info: ResolveInfo,
    *,
    __isinstance: Any = isinstance,
    __getattr: Any = getattr,
    __callable: Any = callable,
    __mapping_cls: Any = Mapping,
    **args: Any
) -> Any:
    """
    Resolve a field from dictionaries or objects.

    This is the default resolver used during query execution and looks up the
    value from the ``root`` in the following lookup order:

    - If ``root`` is a dict subclass:
        - If the field name is present return it
    - If ``root`` has an attribute corresponding to the field name:
        - If the attribute is non callable, return it
        - If the attribute is callable, treat it like a method and return the
          result of calling it passing in ``(context, info, **args)``.
    - Return ``None``.

    If the field defined a custom ``python_name`` attribute, this will be used
    instead of the field name.

    As this is can be called a lot during execution, the ``__*`` type arguments
    are there as an optimisation.

    Args:
        root: Value of the resolved parent node.
        context: User provided context value.
        info (py_gql.execution.ResolveInfo): Resolution context.
        **args: Coerced field arguments.

    Returns:
        Resolved value.

    """
    if __isinstance(root, __mapping_cls):
        return root.get(info.field_definition.python_name, None)

    field_value = __getattr(root, info.field_definition.python_name, None)

    if __callable(field_value):
        return field_value(context, info, **args)
    else:
        return field_value
