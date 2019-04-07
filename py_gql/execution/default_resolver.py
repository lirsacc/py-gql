# -*- coding: utf-8 -*-

from typing import Any

from .wrappers import ResolveInfo


def default_resolver(
    root: Any, context: Any, info: ResolveInfo, **args: Any
) -> Any:
    """ Default resolver used during query execution.

    This resolver looks up the value from the ``root`` in the
    following lookup order:

    1. If ``root`` is a dict subcass:

        1. If the field name is present and non callable, return it
        2. If the field name is present and callable, return the result of
           calling it like a normal resolver (i.e. with the same arguments
           that were passed to this function)

    2. If ``root`` has an attribute corresponding to the field name:

        1.  If the attribute is non callable, return it
        2. If the attribute is callable, treat it like a method of
           ``root`` and call it passing in ``(context, info, **args)``

    3. Return ``None``

    Args:
        root: Value of the resolved parent node
        context: User provided context value
        info (py_gql.execution.ResolveInfo): Resolution context
        **args: Coerced field arguments

    Returns:
        Resolved value
    """
    field_name = info.field_definition.name
    try:
        field_value = root.get(field_name, None)
    except AttributeError:
        attr_value = getattr(root, field_name, None)
        if callable(attr_value):
            return attr_value(context, info, **args)
        return attr_value
    else:
        if callable(field_value):
            return field_value(root, context, info, **args)
        return field_value
