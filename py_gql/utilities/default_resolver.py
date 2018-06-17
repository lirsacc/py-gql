# -*- coding: utf-8 -*-
""" Default resolver behaviour """


def default_resolver(parent_value, args, context, info):
    """ Default resolver used during execution.

    This resolver looks up the value from the ``parent_value`` in the
    following lookup order:

    1. If ``parent_value`` is a ``dict`` subcass:
        1. If the field name is present and non callable, return it
        2. If the field name is present and callable, return result of
            calling it like a normal resolver (i.e. with the arguments passed to
            this function)
    2. If ``parent_value`` has an attribute corresponding to the field name:
        1.  If the attribute is non callable, return it
        2. If the attribute is callable, treat it like a method of ``parent_value``
            and call it passing in ``(args, context, info)``
    3. Return ``None``

    :type parent_value: any
    :param parant_value: Value of the resolved parent node

    :type args: dict
    :param args: Coerced arguments

    :type context: any
    :param context: User provided context value

    :type info: :class:`py_gql.execution.ResolveInfo`
    :param info: Resolution context

    :rype: any
    :returns: Resolved value
    """
    field_name = info.field_def.name
    if isinstance(parent_value, dict):
        field_value = parent_value.get(field_name, None)
        if callable(field_value):
            return field_value(parent_value, args, context, info)
        return field_value

    attr_value = getattr(parent_value, field_name, None)
    if callable(attr_value):
        return attr_value(args, context, info)
    return attr_value
